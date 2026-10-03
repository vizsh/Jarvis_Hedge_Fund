"""The chat assistant's brain: routes a question to the right tool and writes a structured,
verifiable answer.

Design rules (the point is to be right, not to sound clever):
  * Intents are decided by precise rules first, then a small trained nearest-neighbour model
    for paraphrases the rules miss, and if neither is confident the assistant ASKS rather
    than guessing. The old behaviour -- falling back to a portfolio summary for anything
    unrecognised -- answered the wrong question confidently.
  * Every figure comes from the same calculators the Practice page uses (analysis/tools.py,
    backend/practice.py, analysis/panic.py, analysis/goal.py), never from a language model.
  * Text is written in the requested language directly from templates, so numbers cannot be
    changed by a translator.
  * Tool-backed answers carry structure (facts, a table, an "open the visual" action) so the
    UI can show them well, and say plainly what is assumed or illustrative.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any, Callable

from analysis import goal as goal_mod
from analysis import panic as panic_mod
from analysis import tools
from backend import digest as digest_mod
from backend import explain, ledger as ledger_mod, practice
from backend.explain import Answer
from core import universe


@dataclass
class Ctx:
    pit: Any
    portfolio: Any
    prices: dict
    policy: Any
    conn: sqlite3.Connection
    convo: Any = None
    lang: str = "en"
    level: str = "normal"


# =================================================================== saved funds
def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS my_funds (fund_id TEXT PRIMARY KEY, added TEXT)")
    conn.commit()


def my_funds(conn: sqlite3.Connection) -> list[str]:
    _ensure(conn)
    return [r[0] for r in conn.execute("SELECT fund_id FROM my_funds ORDER BY added, fund_id")]


def set_my_fund(conn: sqlite3.Connection, fund_id: str, on: bool) -> list[str]:
    _ensure(conn)
    if on:
        conn.execute("INSERT OR IGNORE INTO my_funds VALUES (?, datetime('now'))", (fund_id,))
    else:
        conn.execute("DELETE FROM my_funds WHERE fund_id = ?", (fund_id,))
    conn.commit()
    return my_funds(conn)


# =================================================================== fund name matching
# (alias, strong). A weak alias ("tech", "banking") is only a fund when the sentence also says
# "fund"/"mutual"/"mf", so "is TCS a tech stock" never becomes a fund question.
_A = {
    "nifty_index": [("nifty 50 index fund", 1), ("nifty index fund", 1), ("nifty 50 index", 1), ("nifty index", 1),
                    ("index fund", 1), ("nifty 50", 0), ("nifty", 0)],
    "largecap_a": [("sample large cap fund a", 1), ("large cap fund a", 1), ("largecap fund a", 1), ("large cap a", 1),
                   ("large cap fund", 1), ("largecap fund", 1), ("large cap", 0), ("largecap", 0)],
    "bluechip_b": [("sample bluechip fund b", 1), ("bluechip fund b", 1), ("blue chip fund b", 1), ("bluechip fund", 1),
                   ("blue chip fund", 1), ("bluechip", 1), ("blue chip", 1), ("blue-chip", 1)],
    "flexicap_c": [("sample flexi cap fund c", 1), ("flexi cap fund c", 1), ("flexicap fund", 1), ("flexi cap fund", 1),
                   ("flexi-cap", 1), ("flexicap", 1), ("flexi cap", 1), ("flexi", 1)],
    "it_fund": [("technology fund", 1), ("tech fund", 1), ("it sector fund", 1), ("it fund", 1),
                ("technology", 0), ("tech", 0)],
    "bank_fund": [("banking fund", 1), ("bank fund", 1), ("banking sector fund", 1), ("banking", 0), ("bank", 0)],
    "pharma_fund": [("healthcare fund", 1), ("pharma fund", 1), ("health fund", 1), ("healthcare", 0), ("pharma", 0)],
    "consumption": [("consumption fund", 1), ("consumer fund", 1), ("consumption", 0)],
}
_ALIAS_LIST = sorted(((a, fid, strong) for fid, items in _A.items() for a, strong in items),
                     key=lambda x: -len(x[0]))
_FUND_WORD = re.compile(r"\b(funds?|mutual|mfs?|schemes?)\b", re.I)
_LETTER = re.compile(r"\bfund\s+([abc])\b", re.I)


def find_funds(text: str) -> list[str]:
    low = " " + re.sub(r"[^a-z0-9 \-]", " ", text.lower()) + " "
    has_word = bool(_FUND_WORD.search(text))
    hits: list[tuple[int, str]] = []
    for alias, fid, strong in _ALIAS_LIST:
        if not strong and not has_word:
            continue
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", low):
            if all(not (s <= m.start() < e) for s, e, _ in [(h[0], h[0] + 1, 0) for h in hits]):
                hits.append((m.start(), fid))
                low = low[:m.start()] + " " * len(alias) + low[m.end():]
    for m in _LETTER.finditer(text):                       # "fund A and fund B"
        fid = {"a": "largecap_a", "b": "bluechip_b", "c": "flexicap_c"}[m.group(1).lower()]
        hits.append((m.start() + 10_000, fid))
    out: list[str] = []
    for _, fid in sorted(hits):
        if fid not in out:
            out.append(fid)
    return out


# =================================================================== intent rules
def _r(p: str) -> re.Pattern:
    return re.compile(p, re.I | re.S)


_FUNDISH = _r(r"\b(funds?|mutual|mfs?|schemes?|sips?)\b")
_RULES: list[tuple[str, re.Pattern]] = [
    ("digest", _r(r"\bone[- ]minute (update|brief\w*|summary|catch-?up)\b|\b(over|in|during) the (past|last) week\b|\b(past|last) (week|7 days|seven days)\b|\b(summary|summari[sz]e|update|brief\w*|roundup|recap)\b.{0,40}\b(this|the|last|past) week\b|\bfor (this|the) week\b|\b(weekly|week'?s|this week'?s?)\b.{0,25}\b(digest|summary|update|report|recap|brief|roundup)\b|\bdigest\b|"
                  r"\b(brief|update|summari[sz]e|catch) me\b.{0,45}\bweek\b|\bhow (was|did|is) my week\b|\bmy week\b|"
                  r"\bsunday (summary|update|brief)\b")),
    ("ledger", _r(r"\b(change|alter|edit|modify|rewrite|tamper|fake|backdate)\w*\b.{0,30}\b(past|old|previous|earlier|my)\b.{0,15}\b(trades?|entries|records?|ledger|history)\b|\b(ledger|audit (trail|log)|tamper\w*|hash[- ]?chain|trade history|trade log|trail of (my )?trades|"
                  r"record of (my )?(trades|decisions)|records? (been )?(changed|altered|edited))\b")),
    ("my_funds_remove", _r(r"\b(remove|delete|drop|forget|clear)\b.{0,40}\b(funds?|mutual)\b|\bno longer (own|hold)\b.{0,40}\bfund|"
                           r"\b(sold|exited|redeemed)\b.{0,30}\b(my )?\w*\s?fund\b")),
    ("my_funds_add", _r(r"\b(i|we)\s+(?:\w+\s+){0,2}?(own|hold|have|invest(ed)? in|bought|am invested in|put money in|started)\b.{0,100}\b(funds?|mutual|index|bluechip|flexi|large cap)|"
                        r"\badd\b.{0,60}\bto my (funds|mutual funds|list)\b|\bmy (mutual )?funds? (are|is)\b|\bsave (these|those|my) funds\b")),
    ("my_funds_show", _r(r"\b(what|which)\s+(mutual )?funds\s+(do|have)\s+i\b|\bshow (me )?my (saved )?(mutual )?funds\b|"
                         r"^\s*(what are |list |display )?my (saved )?(mutual )?funds\s*\??\s*$|\bwhich funds have i (saved|added)\b")),
    ("fund_vs_direct", _r(r"\bdirectly\b|\bmy own (stocks|shares)\b|\bmy direct (stocks|shares|holdings)\b|\b(my|the)\s+(direct\s+)?(stocks|shares|holdings)\b.{0,70}\b(in|inside|through|via|within)\b.{0,25}\b(funds?|mutual)\b|"
                          r"\balready own\b.{0,40}\bfunds?\b|\b(funds?|mutual)\b.{0,50}\b(my|the)\s+(direct\s+)?(stocks|shares|holdings)\b|"
                          r"\bdo my (stocks|shares|holdings)\b.{0,30}\b(appear|show up|repeat)\b.{0,30}\bfunds?\b")),
    ("fund_overlap", _r(r"\b(overlap\w*|same stocks?|same shares|common (stocks|holdings|shares)|duplicat\w*|similar funds?|"
                        r"hold the same|holding the same|paying twice|pay twice|twice for the same|redundant|same thing|same as|clash(es)?|conflict|doubling up|double up|alike|most similar|how similar|crossover|cross-over|same job|twins?|clones?|copies|carbon cop(y|ies))\b")),
    ("fund_list", _r(r"\bwhat (mutual )?funds do you (cover|have|support|know|offer)\b|\b(name|list) the funds\b|\b(what|which|list|show|name|available)\b.{0,25}\b(mutual )?funds?\b.{0,30}\b(have|available|compare|cover|support|know|there|list|offer)\b|"
                      r"\blist (of )?(all )?(the )?(mutual )?funds\b|\bshow me (all )?(the )?(mutual )?funds\b|\bwhich funds (can|do) (i|you)\b")),
    ("fund_info", _r(r"\bstocks?\b.{0,40}\bfund\b.{0,15}\b(invested in|holds?|owns?)\b|\bfund\b.{0,12}\binvested in\b|\bwhat (stocks|shares|companies)\b.{0,30}\b(does|do|are|is)\b.{0,40}\bfund\b|\b(top )?holdings? (of|in)\b|\bwhat('?s| is| does)\b.{0,25}\b(inside|in|hold|holds|own)\b.{0,30}\bfund\b|"
                      r"\bwhat does\b.{0,40}\bhold\b|\bwhat stocks (are )?(in|inside)\b|\bwhat('?s| is) in (the )?\w+\s?\w*\s?fund\b")),
    ("fee_drag", _r(r"\bexpense ratios?\b|\b(management fees?|manager fees?|fund manager|fees?|expense ratio|ter|brokerage|commission|charges?|direct plans?|regular plans?|expense)\b")),
    ("emergency", _r(r"\b(cushion|income stopped|lose my job|lost my job|how many months do i get)\b|\b(savings?|cash|money)\b.{0,30}\b(cover|last|carry)\b.{0,30}\b(without|if|no)\b.{0,20}\b(income|salary|job|work)\b|\bwithout (any )?(income|salary|a job)\b|\bhow long (can|will|could|would) (i|my|it|that|we)\b.{0,40}\b(live|last|survive|manage|cope|get by)\b|\b(emergency fund|emergency savings|emergency money|rainy day|runway|safety net|"
                      r"(how long|how many months).{0,45}\b(last|survive|manage|cover|go on|stay afloat|get by)\b|"
                      r"(lose|lost|losing|quit|laid off|layoffs?|job loss|no job|without (a )?(job|salary|income))\b.{0,30}\b(job|income|salary|work)?\b.{0,30}\b(months?|how long|last|survive|savings)\b|"
                      r"if my (salary|income|job) (stops|ends|goes|disappears)|months? of (expenses|living costs|savings)|"
                      r"enough (cash|savings|money) (for|to cover)|cash cushion)\b")),
    ("goal", _r(r"\b(likelihood|odds|chances?|probabilit\w+)\b.{0,40}\b(crore|lakh|million|target|goal)\b|\bmy (target|goal) is\b.{0,60}\b(years?|yrs?)\b|\bcan i make it\b|\bwhat do i need to invest\b|\bcrorepati\b|\b(sip|investment|portfolio|savings?)\b.{0,30}\b(build|reach|become|make|create)s?\b.{0,20}\b(a |an )?(crore|lakh|million)\b|\b(saving|investing|putting away) enough\b|\b(reach|hit|get to|achieve|make|build|plan|path to|odds)\b.{0,35}\b\d[\d.,]*\s?(lakh|lakhs|crore|crores|cr|lac|lacs)\b.{0,40}\b(years?|yrs?|retire|sip|monthly)\b|\bhow much (would|will|could|can) i (have|get|end up with|accumulate)\b.{0,40}\b(in|after|over|by)\b|\b(sip|invest\w*|portfolio)\b.{0,40}\b(turn into|become|grow to|be worth|worth|end up)\b|\b(retire\w*|financial goal|my goal|corpus|target amount|nest egg|"
                 r"(will|can|could|should) i (reach|get to|have|hit|accumulate|build|make|become)\b.{0,50}\b(lakh|crore|lac|\d+\s?(k|cr|l)\b)|"
                 r"how (long|many years) (will|would|does|to|until)\b.{0,30}\b(take|reach|get|build|hit)|"
                 r"(reach|build|save|accumulate|become|get)\b.{0,30}\d.{0,12}\b(lakh|crore|lac|cr|k)\b.{0,40}\b(years?|yrs?|sip|monthly)|"
                 r"(sip|invest\w*)\b.{0,40}\b(for|over|in)\b.{0,10}\d+\s?(years?|yrs?)\b.{0,50}\b(grow|become|worth|reach|get me|end up|amount to)|"
                 r"will my (sip|investment|portfolio)\b.{0,30}\b(reach|be enough|grow|get me))\b")),
    ("panic", _r(r"\b(wanting|want|tempted|urge|itching|feel like) to sell\b|\bsell when (the )?markets? (drops?|falls?|crash\w*)\b|\b(sold|sell\w*|panic\w*|exit\w*|bail\w*|dump\w*|got out)\b.{0,45}\b(covid|crash|2020|2022|2023|bottom|sell-?off|adani|rate shock|fall)\b|"
                  r"\b(covid|crash|2020|2022|2023|bottom|sell-?off|adani)\b.{0,35}\b(sold|sell|panic\w*|dump\w*|bail\w*)\b|"
                  r"\bpanic[- ]?sell\w*|\bif i (had )?(sold|exited|panicked)\b|\bwhat (if|would have happened).{0,25}\b(i )?(sold|exit)\b")),
    ("tip_scan", _r(r"\b(telegram|whatsapp|instagram|youtube|facebook) (channel|group|page|account)\b.{0,60}\b(tip|tips|guarantee\w*|trust|signal|sure)\b|\b(tip|tips|signal)\b.{0,40}\b(for|costs?) \d+\b.{0,60}\b(guarantee\w*|trust)\b|\b(is|are)\s+(this|that|these)\b.{0,25}\b(tip|tips|message|post|forward\w*|group|channel|advice|signal)\b.{0,25}\b(legit|real|fake|scam|safe|genuine|true|trustworthy|reliable)\b|"
                     r"\b(check|scan|verify|analy[sz]e|screen|vet)\b.{0,15}\b(this|that|the)\b.{0,10}\b(tip|message|post|forward\w*|text)\b|"
                     r"\b(tip|tips|message|group|advice|signal)\b.{0,40}\b(on|from|in)\b.{0,12}\b(telegram|whatsapp|instagram|youtube|facebook|twitter)\b.{0,40}\b(legit|real|fake|scam|safe|true|trust\w*|check)\b|"
                     r"\b(sure[- ]?shot|100% (return|profit|guaranteed)|guaranteed (returns?|profit|(\d+x)|doubl\w+)|double your money|multibagger tip)\b")),
    ("scam_help", _r(r"\bincome tax (department|officer)\b|\bsim (card )?(will be |is )?(blocked|deactivated|disconnected)\b|\b(claim|won) (a |your )?(prize|lottery|reward|gift)\b|\bclick (on )?(a|the|this) link\b|\bpolice\b.{0,25}\barrest\b.{0,20}\b(video|phone|call|online)\b|\bpenalty\b.{0,30}\bupi\b|\bshare the (code|otp)\b|\b(parcel|courier|customs)\b.{0,40}\b(illegal|drugs|contraband|seized|held|in my name|arrest)\b|\bcaller says\b|\b(transfer|send|move|pay)\b.{0,25}\bmoney\b.{0,40}\b(police|officer|rbi|bank|account|unblock|safe account|verification)\b|\b(screen[- ]?shar\w*|download|install)\b.{0,40}\bapps?\b.{0,40}\b(account|unblock|bank|kyc|fix)\b|\b(call|caller|sms|email|link|officer|message)\b.{0,30}\b(real|genuine|fake|legit|safe|authentic)\b|\blink\b.{0,40}\bkyc\b|\bkyc\b.{0,40}\blink\b|\b(otp|cvv|kyc (call|expired|update|pending)|digital arrest|scam\w*|fraud\w*|cheated|phishing|fake (call|caller|link|app|website|officer)|"
                      r"suspicious (call|message|link|sms|email)|someone (called|rang|messaged)|(got|received|had) (a|an) (call|message|sms|email)|anydesk|quicksupport|teamviewer|"
                      r"remote (access|control|app)|upi (fraud|scam|request)|collect request|1930|cyber ?crime|asked (me )?for my (pin|otp|password)|"
                      r"lost money (to|in) (a )?(scam|fraud)|blackmail\w*|loan app|parcel (with|has|held)|customs (officer|call))\b")),
    ("predict", _r(r"\bwhich (small|mid|large)[- ]?cap\b|\bmake me rich\b|\bwill (bitcoin|btc|crypto|gold|silver|nifty|sensex|the market|[a-z]+)\b.{0,15}\b(cross|hit|touch|reach|breach)\b|\b(target price|price target)\b|\b(will|going to)\b.{0,25}\b(give|make|return|get)\b.{0,15}\b\d+ ?x\b|\b\d+ ?x\b.{0,12}\b(return|returns|in a year|in a month)\b|\b(will|going to|gonna)\b.{0,25}\b(double|triple|go up|rise|moon|crash|fall|rally|jump|shoot up|touch)\b|"
                    r"\b(price target|multibagger|which stocks? (to buy|will|should i buy|is best)|best stocks? to buy|stocks? to buy (now|today|tomorrow)|"
                    r"hot stocks?|next (big )?winner|will .{0,20} (be|hit) (₹|rs)?\s?\d)\b|\bpredict\w*\b|\bforecast\b|\btomorrow'?s? (price|market)\b|\bwhere will (the )?(market|nifty|sensex)\b")),
    ("help", _r(r"\bwhat should i ask\b|\bwhat (are )?(the )?(things|stuff|questions|topics) (i|we) can (ask|do|say)\b|^\s*(help|what can you do|what do you do|what can i (ask|do)|how (do|can) i use (this|you)|who are you|what are you|features|capabilities|show (me )?what you can do|menu)\b")),
    ("stress", _r(r"\b(tanks?|plunges?|collapses?|crashes|slumps?|tumbles?)\b.{0,20}\b\d+\s?(%|percent)\b")),
    ("diversification", _r(r"@@b(too heavily|overexposed|over-exposed|eggs in one basket|too tilted|too much (of my money )?(is )?(riding )?in)@@b.{0,30}@@b(one|single|same|a)@@b|@@btoo heavily invested@@b".replace("@@", chr(92)))),
    ("correlation", _r(r"\b(fall|rise|move|go up|go down|drop) together\b|\btend to (fall|rise|move|drop)\b|@@b(behave|act|move|trade)@@w*@@b.{0,15}@@b(the same|alike|similarly|in sync|together)@@b|@@bany of my (shares|stocks|holdings)@@b.{0,30}@@b(same|alike|together)@@b".replace("@@", chr(92)))),
    ("should_buy", _r(r"@@b(good|great|wise|smart|sensible)@@s+(addition|buy|pick|idea to buy)@@b|@@bshould i (get(?! rid)|pick up|add|buy)@@b".replace("@@", chr(92)))),
    ("fix", _r(r"\bwhich of my (stocks|shares|holdings)\b.{0,25}\b(sell|drop|exit|get rid of|dump|cut|trim|reduce)\b|\bget rid of\b|@@bwhat should i (cut|drop|reduce|lower|offload|get rid of|trim)@@b|@@bto be safer@@b|@@bhow (can|do) i (de-?risk|reduce my risk|make it safer)@@b".replace("@@", chr(92)))),
    ("why", _r(r"\b(weakest|weak) (part|spot|point|link)\b|@@b(main|biggest|top|key|major|worst)@@s+(risks?|problems?|weak(ness)?es)@@b|@@brisks? in my@@b".replace("@@", chr(92)))),
    ("xray", _r(r"\b(big picture|bird.s eye|how my (investments|money|portfolio) (are|is) doing)\b|\b(check-?up|health ?check|overview|status)\b.{0,25}\b(my|of my)\b.{0,15}\b(investments?|portfolio|money|holdings)\b|@@b(in good shape|doing well|state of my (money|portfolio|investments)|my overall (position|picture)|how (am|are) (i|you) doing with)@@b".replace("@@", chr(92)))),
    ("chitchat", _r(r"^\s*(hi|hello|hey|namaste|namaskar|good (morning|afternoon|evening)|thanks?( you)?|thank you|ok(ay)?|cool|great|nice|bye|goodbye|see you)\W*$")),
]

LEGACY = {"define", "stress", "fix", "why", "xray", "correlation", "diversification", "should_buy", "simplify"}
NEW_KINDS = {"digest", "ledger", "my_funds_add", "my_funds_remove", "my_funds_show", "fund_vs_direct", "fund_overlap",
             "fund_list", "fund_info", "fee_drag", "emergency", "goal", "panic", "tip_scan", "scam_help", "predict",
             "help", "chitchat", "clarify", "out_of_scope"}


_OWNERSHIP = _r(r"\b(i|we)\s+(?:\w+\s+){0,2}?(own|hold|have|invest(ed)?|bought|put|started|am invested)\b|\badd\b.{0,60}\bto my\b|\bmy funds? (are|is)\b")
_NOT_OVERLAP = _r(r"\b(remove|delete|drop|forget|clear|sold|redeemed|fees?|expense|cost|charges?|top holdings|holdings of|"
                  r"what (is|does|are)\b.{0,25}\b(in|inside|hold)|inside the)\b")
_OFFTOPIC = _r(r"\b(how (tall|far|old|big|deep|long ago)|everest|bedtime|who (invented|discovered|wrote)|when was (the )?\w+ (born|built)|weather|rain|temperature|joke|funny|cricket|ipl|football|soccer|movie|film|song|music|poem|story|recipe|cook|bake|"
               r"cake|biryani|pizza|restaurant|coffee|hotel|flight|nearby|holiday|vacation|travel|usa|capital of|prime minister|president|who won|world cup|translate|homework|girlfriend|boyfriend|dating|"
               r"politic\w*|election|celebrity|what time is it|riddle|sing|game)\b")
_ONTOPIC = _r(r"\b(fund|funds|stock|stocks|share|shares|portfolio|invest\w*|sip|savings?|loan|tax|fee|fees|bank|nifty|sensex|market|"
              r"holdings?|crore|lakh|rupees?|emi|insurance|scam|otp|digest|ledger|mutual)\b|₹")
_DEF_Q = _r(r"^\s*(what('?s| is| are| does| do)|whats|explain|define|meaning of|tell me about|what do you mean by)\b")
_PERSONAL = _r(r"\b(my|mine|i|we|our)\b|\d")


def rule_intent(text: str) -> str | None:
    low = text.strip()
    # A plain "what is X?" about a term we have a definition for is a definition, even when X
    # is also a trigger word for a tool ("expense ratio", "overlap", "otp").
    if _DEF_Q.search(low) and not _PERSONAL.search(low) and explain.define(low):
        return "define"
    funds = find_funds(low)
    # A named fund plus a comparison word is an overlap question even without the word
    # "overlap": "compare large cap fund A and bluechip fund B".
    if (_OFFTOPIC.search(low) and not _ONTOPIC.search(low)):
        return "out_of_scope"
    if len(funds) >= 2 and not _OWNERSHIP.search(low) and not _NOT_OVERLAP.search(low):
        return "fund_overlap"
    for kind, rx in _RULES:
        if rx.search(low):
            if kind == "fee_drag" and not _fee_context_ok(low):
                continue
            if kind == "fund_overlap" and not (funds or _FUNDISH.search(low)):
                continue       # "do my stocks overlap" is the older correlation question
            if kind in ("my_funds_add",) and not funds:
                continue
            if kind == "my_funds_remove" and not (funds or re.search(r"\b(all|everything|my funds)\b", low, re.I)):
                continue
            if kind == "fund_vs_direct" and not (funds or _FUNDISH.search(low)):
                continue
            if kind == "fund_info" and not funds:
                continue
            return kind
    return None


def _fee_context_ok(low: str) -> bool:
    """'fee' alone is a weak signal ("tax fee on selling"?). It needs a fund/investing context, a
    figure, or cost words, so only real fee-drag questions land here."""
    if re.search(r"\b(tax|stt|capital gains?|ltcg|stcg)\b", low, re.I) and not _FUNDISH.search(low):
        return False
    if re.search(r"\bexpense ratios?\b", low):
        return True
    return bool(_FUNDISH.search(low) or re.search(r"\d|\b(direct|regular) plans?\b", low) or
                re.search(r"\b(cost|costs|eat|eats|drag|impact|compound|affect|matter|worth|hurt|pay|paying|high|low|cheap|expensive)\b", low, re.I))


# =================================================================== trained fallback
_KNN = None


def _knn():
    global _KNN
    if _KNN is None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from scipy.sparse import hstack
        from backend.intent_data import EXAMPLES
        texts, labels = [], []
        for label, items in EXAMPLES.items():
            for it in items:
                texts.append(_mask(it))
                labels.append(label)
        v1 = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
        v2 = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)
        X = hstack([v1.fit_transform(texts), v2.fit_transform(texts)]).tocsr()
        _KNN = (v1, v2, X, labels, texts)
    return _KNN


_NAME_RX = None
_ALIAS_RX = None


def _mask(t: str) -> str:
    """Hide the entities (fund names, company names, numbers) so the model learns the shape of
    the request, not which fund or figure happened to be in the examples."""
    global _NAME_RX, _ALIAS_RX
    if _NAME_RX is None:
        names = sorted({universe.name(x).lower() for x in universe.tickers()} |
                       {x.split(".")[0].lower() for x in universe.tickers()}, key=len, reverse=True)
        _NAME_RX = re.compile("(?<![a-z])(" + "|".join(re.escape(n) for n in names) + ")(?![a-z])")
        _ALIAS_RX = re.compile("(?<![a-z0-9])(" + "|".join(re.escape(a) for a, _, _ in _ALIAS_LIST) + ")(?![a-z0-9])")
    t = t.lower()
    t = _ALIAS_RX.sub(" fundname ", t)
    t = _NAME_RX.sub(" companyname ", t)
    t = re.sub(r"\d[\d,]*(\.\d+)?", " num ", t)
    t = re.sub(r"\bfund\s+[abc]\b", " fundname ", t)
    return re.sub(r"\s+", " ", t).strip()


def knn_rank(text: str, exclude: str | None = None) -> list[tuple[str, float]]:
    """Intents ranked by the similarity of their closest training example."""
    from scipy.sparse import hstack
    from sklearn.preprocessing import normalize
    v1, v2, X, labels, texts = _knn()
    q = hstack([v1.transform([_mask(text)]), v2.transform([_mask(text)])]).tocsr()
    sims = (normalize(X) @ normalize(q).T).toarray().ravel()
    if exclude is not None:                                    # leave-one-out for evaluation
        for i, tx in enumerate(texts):
            if tx == _mask(exclude):
                sims[i] = -1
    best: dict[str, float] = {}
    for sim, lab in zip(sims, labels):
        if lab == "chitchat":          # greetings are matched by rule only: too short to trust a similarity score
            continue
        best[lab] = max(best.get(lab, 0.0), float(sim))
    return sorted(best.items(), key=lambda kv: -kv[1])


def knn_intent(text: str, exclude: str | None = None) -> tuple[str | None, float, float]:
    """(intent, best similarity, margin over the runner-up intent)."""
    ranked = knn_rank(text, exclude)
    if not ranked:
        return None, 0.0, 0.0
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    return ranked[0][0], ranked[0][1], ranked[0][1] - second


def detect(text: str) -> tuple[str, str]:
    """(intent, how). Precise rules, then the original explainer's rules, otherwise "clarify".
    The similarity model is not allowed to decide: measured leave-one-out it was right about
    half the time, and a confident wrong answer is worse than a question. It suggests instead
    (see h_clarify), and an optional local-LLM classifier (aanswer) handles odd phrasings."""
    k = rule_intent(text)
    if k:
        return k, "rule"
    legacy = explain.classify_strict(text)
    if legacy:
        return legacy, "legacy"
    return "clarify", "none"


# =================================================================== answer helpers
def _t(lang: str):
    return (lambda en, hi: hi if lang == "hi" else en)


def _fact(label: str, value: str, tone: str = "") -> dict[str, str]:
    return {"label": label, "value": value, "tone": tone}


def _done(a: Answer, ctx: Ctx, chips: list[tuple[str, str]], kind: str) -> Answer:
    """Attach follow-ups (English question, Hindi label), apply the explain-back level."""
    a.kind = kind
    a.lang = ctx.lang
    a.follow_ups = [q for q, _ in chips]
    if ctx.lang == "hi":
        a.follow_ups_hi = [h for _, h in chips]
    if ctx.lang == "hi":                       # keep the Indian number words in the language of the text
        def hi(x: str) -> str:
            return x.replace(" crore", " करोड़").replace(" lakh", " लाख")
        for f in a.facts:
            f["value"] = hi(f["value"])
        if a.table:
            a.table["rows"] = [[hi(c) for c in row] for row in a.table["rows"]]
    if ctx.level == "simple":
        a.bullets = a.bullets[:1]
        a.table = None
        a.detail = None
    elif ctx.level == "maths" and a.detail:
        a.bullets = [*a.bullets, a.detail]
    if ctx.convo is not None:
        ctx.convo.remember(a)
    return a


_FU = {
    "overlap": ("Which funds overlap the most?", "कौन से फ़ंड सबसे ज़्यादा मिलते-जुलते हैं?"),
    "fee": ("What does a 2% fee cost over 20 years?", "2% फ़ीस बीस साल में कितनी पड़ती है?"),
    "emerg": ("How long will 3 lakh last if I spend 40000 a month?", "3 लाख रुपये 40000 महीने के ख़र्च पर कितना चलेंगे?"),
    "goal": ("Will 10000 a month reach 50 lakh in 15 years?", "10000 महीने की SIP से 15 साल में 50 लाख बनेंगे?"),
    "panic": ("What if I had sold during the Covid crash?", "कोविड गिरावट में बेच देता तो क्या होता?"),
    "digest": ("Give me my weekly digest", "मेरा साप्ताहिक सार सुनाइए"),
    "scam": ("Someone asked for my OTP on a call", "किसी ने फ़ोन पर मेरा OTP माँगा"),
    "list": ("Which mutual funds do you have?", "आपके पास कौन से म्यूचुअल फ़ंड हैं?"),
    "help": ("What can you do?", "आप क्या-क्या कर सकते हैं?"),
    "xray": ("How am I doing?", "मेरा पोर्टफ़ोलियो कैसा चल रहा है?"),
    "ledger": ("Is my ledger intact?", "क्या मेरा रिकॉर्ड सुरक्षित है?"),
    "why": ("Why is my risk high?", "मेरा जोखिम ज़्यादा क्यों है?"),
    "fix": ("What should I sell?", "मुझे क्या बेचना चाहिए?"),
    "stress": ("What if the market drops 20%?", "बाज़ार 20% गिरे तो क्या होगा?"),
    "div": ("Am I diversified?", "क्या मेरा पैसा अलग-अलग जगह बँटा है?"),
}


def _chips(*keys: str) -> list[tuple[str, str]]:
    return [_FU[k] for k in keys]


def _pc(x: float) -> str:
    """Round half up, so 88.5% reads 89% here exactly as it does on the overlap ring."""
    return str(int(x + 0.5))


def _mo(n: int, hi: bool) -> str:
    return f"{n} महीने" if hi else f"{n} month{'' if n == 1 else 's'}"


def _fname(fid: str) -> str:
    return practice.FUNDS[fid]["name"].replace("Sample ", "")


# =================================================================== handlers
def h_help(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    a = Answer(headline=t("I help you protect your money, understand it and keep it honest.",
                          "मैं आपके पैसे को सुरक्षित रखने, समझने और ईमानदार रखने में मदद करता हूँ।"),
               bullets=[t("Protect: check a stock tip, a suspicious call or a scam message.",
                          "सुरक्षा: स्टॉक टिप, संदिग्ध कॉल या ठगी के संदेश की जाँच।"),
                        t("Understand: fund overlap, what fees cost, emergency cash, whether a goal is reachable, what a crash would do.",
                          "समझ: फ़ंड ओवरलैप, फ़ीस की असली क़ीमत, इमरजेंसी पैसा, लक्ष्य पूरा होगा या नहीं, गिरावट का असर।"),
                        t("Keep honest: your trade record is tamper-evident, and every figure comes from a calculator, not a guess.",
                          "ईमानदारी: आपका लेन-देन रिकॉर्ड छेड़छाड़ पकड़ने वाला है, और हर आँकड़ा कैलकुलेटर से आता है, अंदाज़े से नहीं।")],
               action=t("Try one of the questions below. I will tell you plainly when I do not know.",
                        "नीचे का कोई सवाल आज़माइए। जो मुझे नहीं पता, वह मैं साफ़ बता दूँगा।"))
    return _done(a, ctx, _chips("overlap", "fee", "emerg", "goal", "panic", "digest"), "help")


def h_chitchat(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    thanks = re.search(r"thank|bye|cool|great|nice|ok", text, re.I)
    a = Answer(headline=t("Happy to help. Ask me anything about your money." if thanks else "Hello! What would you like to know about your money?",
                          "ख़ुशी हुई। अपने पैसे के बारे में कुछ भी पूछिए।" if thanks else "नमस्कार! अपने पैसे के बारे में क्या जानना चाहेंगे?"))
    return _done(a, ctx, _chips("xray", "overlap", "fee", "help"), "chitchat")


def h_out_of_scope(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    a = Answer(headline=t("That is outside what I can help with. I only handle money questions.",
                          "यह मेरे दायरे से बाहर है। मैं सिर्फ़ पैसे से जुड़े सवालों में मदद कर सकता हूँ।"),
               action=t("Ask about your portfolio, funds, fees, emergency cash, goals or scams.",
                        "अपने पोर्टफ़ोलियो, फ़ंड, फ़ीस, इमरजेंसी पैसे, लक्ष्य या ठगी के बारे में पूछिए।"))
    return _done(a, ctx, _chips("xray", "overlap", "scam", "help"), "out_of_scope")


_INTENT_CHIP = {"fund_overlap": "overlap", "fund_list": "list", "fund_info": "list", "fund_vs_direct": "overlap",
                "my_funds_add": "overlap", "my_funds_show": "overlap", "my_funds_remove": "overlap",
                "fee_drag": "fee", "emergency": "emerg", "goal": "goal", "panic": "panic", "digest": "digest",
                "scam_help": "scam", "tip_scan": "scam", "predict": "scam", "ledger": "ledger", "help": "help",
                "xray": "xray", "why": "why", "fix": "fix", "stress": "stress", "diversification": "div",
                "correlation": "xray", "should_buy": "xray", "define": "help", "simplify": "xray"}


def suggestions(text: str, n: int = 3) -> list[tuple[str, str]]:
    """The nearest few things I know how to do, as tappable questions."""
    chips: list[tuple[str, str]] = []
    try:
        ranked = knn_rank(text)
    except Exception:  # noqa: BLE001
        ranked = []
    for intent, sim in ranked:
        key = _INTENT_CHIP.get(intent)
        if key and sim > 0.15 and _FU[key] not in chips:
            chips.append(_FU[key])
        if len(chips) >= n:
            break
    for key in ("xray", "overlap", "fee"):
        if len(chips) >= n:
            break
        if _FU[key] not in chips:
            chips.append(_FU[key])
    return chips


def h_clarify(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    a = Answer(headline=t("I am not sure what you are asking, and I would rather ask than guess.",
                          "मुझे पक्का समझ नहीं आया कि आप क्या पूछ रहे हैं, और मैं अंदाज़ा लगाने से बेहतर पूछना समझता हूँ।"),
               bullets=[t("Try naming the thing: a fund, a fee, your emergency cash, a goal, a call or message, or a company.",
                          "किसी चीज़ का नाम लीजिए: फ़ंड, फ़ीस, इमरजेंसी पैसा, लक्ष्य, कोई कॉल या संदेश, या कोई कंपनी।")],
               action=t("Or pick one of these.", "या इनमें से कोई चुनिए।"))
    return _done(a, ctx, suggestions(text), "clarify")


def h_predict(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    a = Answer(headline=t("Nobody can reliably predict where a price will go, and I will not pretend to.",
                          "कोई भी भरोसे से नहीं बता सकता कि भाव कहाँ जाएगा, और मैं दिखावा नहीं करूँगा।"),
               bullets=[t("Anyone promising a sure winner or a doubling is selling something. That is the most common scam line.",
                          "जो भी पक्का मुनाफ़ा या पैसा दुगना होने का वादा करे, वह कुछ बेच रहा है। यह सबसे आम ठगी की बात है।"),
                        t("What I can do is show what a fall would do to your own holdings, and check a tip for scam tactics.",
                          "मैं यह दिखा सकता हूँ कि गिरावट आने पर आपके अपने शेयरों का क्या होगा, और किसी टिप में ठगी की चालें जाँच सकता हूँ।")],
               action=t("Ask what a fall would do to you, or paste a tip to check.",
                        "पूछिए कि गिरावट का आप पर क्या असर होगा, या जाँचने के लिए कोई टिप चिपकाइए।"))
    return _done(a, ctx, _chips("panic", "scam", "xray"), "predict")


# ---- funds -----------------------------------------------------------------------------
def _own(ctx: Ctx) -> dict[str, float]:
    return {tk: sh * ctx.prices.get(tk, 0.0) for tk, sh in ctx.portfolio.positions.items()}


def _ranked_pairs(ids: list[str]) -> list[dict[str, Any]]:
    out = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            o = practice.overlap(a, b, universe.name)
            out.append({"a": a, "b": b, "pct": o["overlap_pct"], "n": o["shared_stocks"], "verdict": o["verdict"], "o": o})
    out.sort(key=lambda r: -r["pct"])
    return out


def _verdict_words(v: str, t) -> str:
    return {"red": t("almost the same portfolio", "लगभग एक ही पोर्टफ़ोलियो"),
            "amber": t("a noticeable overlap", "ध्यान देने लायक़ ओवरलैप"),
            "green": t("genuinely different", "सचमुच अलग-अलग")}[v]


_DISC = ("Holdings are illustrative samples typical of each fund type, not live factsheets.",
         "होल्डिंग्स हर तरह के फ़ंड के नमूने हैं, असली फ़ैक्टशीट नहीं।")


def _pair_answer(a_id: str, b_id: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    o = practice.overlap(a_id, b_id, universe.name, _own(ctx))
    A, B = o["a"], o["b"]
    pct, v = o["overlap_pct"], o["verdict"]
    top = o["shared"][:3]
    head = t(f"{_fname(a_id)} and {_fname(b_id)} hold {_pc(pct)}% of the same stocks: {_verdict_words(v, t)}.",
             f"{_fname(a_id)} और {_fname(b_id)} में {_pc(pct)}% शेयर एक जैसे हैं: {_verdict_words(v, t)}।")
    bullets = []
    if top:
        bullets.append(t("Biggest shared holdings: " + ", ".join(f"{r['name']} ({r['wa']}% and {r['wb']}%)" for r in top) + ".",
                         "सबसे बड़े साझा शेयर: " + ", ".join(f"{r['name']} ({r['wa']}% और {r['wb']}%)" for r in top) + "।"))
    else:
        bullets.append(t("They share no stocks, so holding both does spread your money.", "इनमें कोई शेयर साझा नहीं है, इसलिए दोनों रखने से पैसा सचमुच बँटता है।"))
    if v != "green":
        bullets.append(t(f"Fees: {A['er']}% and {B['er']}% a year. On every ₹1 lakh, about {tools.inr(o['wasted_fee_per_lakh'])} a year pays for stocks you already hold through the other fund.",
                         f"फ़ीस: सालाना {A['er']}% और {B['er']}%। हर 1 लाख रुपये पर लगभग {tools.inr_hi(o['wasted_fee_per_lakh'])} साल में उन शेयरों के लिए जाते हैं जो दूसरे फ़ंड से पहले ही आपके पास हैं।"))
    if o.get("own_in_a", 0) or o.get("own_in_b", 0):
        bullets.append(t(f"Of what you hold directly, {o['own_in_a']}% is already inside {_fname(a_id)} and {o['own_in_b']}% inside {_fname(b_id)}.",
                         f"आपके सीधे शेयरों का {o['own_in_a']}% पहले से {_fname(a_id)} में और {o['own_in_b']}% {_fname(b_id)} में है।"))
    action = {"red": t("Ask whether you need both. Keeping one, ideally the cheaper, usually gives the same spread for one fee.",
                       "सोचिए कि क्या दोनों चाहिए। एक रखना, ख़ासकर सस्ता वाला, एक ही फ़ीस में लगभग वही बँटवारा देता है।"),
              "amber": t("Some duplication is normal. Check whether the second fund adds anything the first does not.",
                         "कुछ दोहराव सामान्य है। देखिए कि दूसरा फ़ंड कुछ नया जोड़ता है या नहीं।"),
              "green": t("These two complement each other.", "ये दोनों एक-दूसरे के पूरक हैं।")}[v]
    a = Answer(headline=head, bullets=bullets, action=action,
               detail=t("Overlap = sum over shared stocks of the smaller weight, as a share of the smaller fund. " + _DISC[0],
                        "ओवरलैप = साझा शेयरों के छोटे वज़न का जोड़, छोटे फ़ंड के हिस्से के रूप में। " + _DISC[1]),
               facts=[_fact(t("Overlap", "ओवरलैप"), f"{_pc(pct)}%", {"red": "bad", "amber": "warn", "green": "good"}[v]),
                      _fact(t("Shared stocks", "साझा शेयर"), str(o["shared_stocks"])),
                      _fact(t("Fees", "फ़ीस"), f"{A['er']}% / {B['er']}%")],
               table={"columns": [t("Stock", "शेयर"), _fname(a_id), _fname(b_id)],
                      "rows": [[r["name"], f"{r['wa']}%", f"{r['wb']}%"] for r in o["shared"][:8]]} if o["shared"] else None,
               visual={"page": "practice", "label": t("Open the overlap visual", "ओवरलैप का चित्र खोलें"), "params": {"a": a_id, "b": b_id}})
    a.data = {"overlap_pct": pct, "a": a_id, "b": b_id}
    return _done(a, ctx, _chips("fee", "overlap", "list"), "fund_overlap")


def _ranking_answer(ids: list[str], ctx: Ctx, title_en: str, title_hi: str) -> Answer:
    t = _t(ctx.lang)
    pairs = _ranked_pairs(ids)
    top = pairs[0]
    head = t(f"{title_en}: {_fname(top['a'])} and {_fname(top['b'])} overlap the most, at {_pc(top['pct'])}%.",
             f"{title_hi}: {_fname(top['a'])} और {_fname(top['b'])} सबसे ज़्यादा मिलते हैं, {_pc(top['pct'])}%।")
    a = Answer(headline=head,
               bullets=[t(f"{sum(1 for p in pairs if p['verdict'] == 'red')} pairs are mostly the same portfolio; "
                          f"{sum(1 for p in pairs if p['verdict'] == 'green')} pairs are genuinely different.",
                          f"{sum(1 for p in pairs if p['verdict'] == 'red')} जोड़ियाँ लगभग एक ही पोर्टफ़ोलियो हैं; "
                          f"{sum(1 for p in pairs if p['verdict'] == 'green')} जोड़ियाँ सचमुच अलग हैं।")],
               action=t("Ask about a specific pair for the shared stocks and the fee cost.", "किसी एक जोड़ी के बारे में पूछिए, साझा शेयर और फ़ीस का असर दिखाऊँगा।"),
               detail=_DISC[1] if ctx.lang == "hi" else _DISC[0],
               table={"columns": [t("Pair", "जोड़ी"), t("Overlap", "ओवरलैप"), t("Shared", "साझा")],
                      "rows": [[f"{_fname(p['a'])} + {_fname(p['b'])}", f"{_pc(p['pct'])}%", str(p["n"])] for p in pairs[:6]]},
               facts=[_fact(t("Highest overlap", "सबसे ज़्यादा"), f"{_pc(top['pct'])}%", "bad" if top["verdict"] == "red" else "warn")],
               visual={"page": "practice", "label": t("Open the overlap visual", "ओवरलैप का चित्र खोलें"), "params": {"a": top["a"], "b": top["b"]}})
    return _done(a, ctx, _chips("fee", "list", "overlap"), "fund_overlap")


def h_fund_overlap(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    named = find_funds(text)
    mine = my_funds(ctx.conn)
    wants_mine = bool(re.search(r"\bmy\b|\bi (own|hold|have)\b|\bmine\b|\bi'?m invested\b", text, re.I))
    if len(named) >= 3:
        return _ranking_answer(named, ctx, t("Among the funds you named", "आपके बताए फ़ंडों में"), "आपके बताए फ़ंडों में")
    if len(named) == 2:
        return _pair_answer(named[0], named[1], ctx)
    if wants_mine:
        if len(mine) >= 3:
            return _ranking_answer(mine, ctx, t("Among your funds", "आपके फ़ंडों में"), "आपके फ़ंडों में")
        if len(mine) == 2:
            return _pair_answer(mine[0], mine[1], ctx)
        have = ", ".join(_fname(f) for f in mine) or t("none yet", "अभी कोई नहीं")
        a = Answer(headline=t("I need at least two of your funds to compare. Tell me which ones you own.",
                              "तुलना के लिए मुझे आपके कम से कम दो फ़ंड चाहिए। बताइए कौन से आपके पास हैं।"),
                   bullets=[t(f"Saved so far: {have}.", f"अब तक सहेजे: {have}।"),
                            t("Say, for example: I own Large Cap Fund A and Bluechip Fund B.", "जैसे कहिए: मेरे पास Large Cap Fund A और Bluechip Fund B है।"),
                            t("I can only see the sample funds below, not real fund factsheets.", "मैं सिर्फ़ नीचे के नमूना फ़ंड देख सकता हूँ, असली फ़ैक्टशीट नहीं।")],
                   table={"columns": [t("Fund", "फ़ंड"), t("Type", "प्रकार"), t("Fee", "फ़ीस")],
                          "rows": [[f["name"].replace("Sample ", ""), f["kind"], f"{f['er']}%"] for f in practice.fund_list()]})
        return _done(a, ctx, _chips("list", "overlap"), "fund_overlap")
    if len(named) == 1:
        others = [f for f in practice.FUNDS if f != named[0]]
        pairs = sorted(({"b": b, "o": practice.overlap(named[0], b, universe.name)} for b in others), key=lambda r: -r["o"]["overlap_pct"])
        top = pairs[0]
        a = Answer(headline=t(f"{_fname(named[0])} overlaps most with {_fname(top['b'])}, at {_pc(top['o']['overlap_pct'])}%.",
                              f"{_fname(named[0])} सबसे ज़्यादा {_fname(top['b'])} से मिलता है, {_pc(top['o']['overlap_pct'])}%।"),
                   bullets=[t(f"It overlaps least with {_fname(pairs[-1]['b'])}, at {_pc(pairs[-1]['o']['overlap_pct'])}%.",
                              f"सबसे कम मेल {_fname(pairs[-1]['b'])} से है, {_pc(pairs[-1]['o']['overlap_pct'])}%।")],
                   detail=_DISC[1] if ctx.lang == "hi" else _DISC[0],
                   table={"columns": [t("Other fund", "दूसरा फ़ंड"), t("Overlap", "ओवरलैप")],
                          "rows": [[_fname(p["b"]), f"{_pc(p['o']['overlap_pct'])}%"] for p in pairs[:5]]},
                   facts=[_fact(t("Highest", "सबसे ज़्यादा"), f"{_pc(top['o']['overlap_pct'])}%")],
                   visual={"page": "practice", "label": t("Open the overlap visual", "ओवरलैप का चित्र खोलें"),
                           "params": {"a": named[0], "b": top["b"]}})
        return _done(a, ctx, _chips("fee", "list"), "fund_overlap")
    return _ranking_answer(list(practice.FUNDS), ctx, t("Across all the sample funds", "सभी नमूना फ़ंडों में"), "सभी नमूना फ़ंडों में")


def h_fund_list(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    fl = practice.fund_list()
    a = Answer(headline=t(f"I can compare {len(fl)} sample funds: index, active and sector.", f"मैं {len(fl)} नमूना फ़ंडों की तुलना कर सकता हूँ: इंडेक्स, एक्टिव और सेक्टर।"),
               bullets=[t("These are illustrative samples typical of each fund type. I cannot see real fund factsheets offline.",
                          "ये हर तरह के फ़ंड के नमूने हैं। मैं ऑफ़लाइन असली फ़ंड की फ़ैक्टशीट नहीं देख सकता।")],
               table={"columns": [t("Fund", "फ़ंड"), t("Type", "प्रकार"), t("Fee a year", "सालाना फ़ीस")],
                      "rows": [[f["name"].replace("Sample ", ""), f["kind"], f"{f['er']}%"] for f in fl]},
               visual={"page": "practice", "label": t("Open the overlap visual", "ओवरलैप का चित्र खोलें"), "params": {}})
    return _done(a, ctx, _chips("overlap", "fee"), "fund_list")


def h_fund_info(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    fid = find_funds(text)[0]
    f = practice.FUNDS[fid]
    rows = sorted(f["h"].items(), key=lambda kv: -kv[1])
    a = Answer(headline=t(f"{_fname(fid)} ({f['kind']}, fee {f['er']}% a year) puts most weight on {universe.name(rows[0][0])}, {rows[0][1]}%.",
                          f"{_fname(fid)} ({f['kind']}, सालाना फ़ीस {f['er']}%) सबसे ज़्यादा वज़न {universe.name(rows[0][0])} को देता है, {rows[0][1]}%।"),
               bullets=[t(f"Top three: " + ", ".join(f"{universe.name(k)} {v}%" for k, v in rows[:3]) + ".",
                          "शीर्ष तीन: " + ", ".join(f"{universe.name(k)} {v}%" for k, v in rows[:3]) + "।")],
               detail=_DISC[1] if ctx.lang == "hi" else _DISC[0],
               table={"columns": [t("Stock", "शेयर"), t("Weight", "वज़न")], "rows": [[universe.name(k), f"{v}%"] for k, v in rows[:8]]},
               facts=[_fact(t("Fee a year", "सालाना फ़ीस"), f"{f['er']}%"), _fact(t("Holdings shown", "दिखाए गए शेयर"), str(len(rows)))])
    return _done(a, ctx, _chips("overlap", "fee", "list"), "fund_info")


def h_my_funds_add(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    ids = find_funds(text)
    for fid in ids:
        set_my_fund(ctx.conn, fid, True)
    mine = my_funds(ctx.conn)
    a = Answer(headline=t("Saved: " + ", ".join(_fname(f) for f in ids) + ".", "सहेज लिया: " + ", ".join(_fname(f) for f in ids) + "।"),
               bullets=[t("Your funds: " + ", ".join(_fname(f) for f in mine) + ".", "आपके फ़ंड: " + ", ".join(_fname(f) for f in mine) + "।")],
               action=t("Ask which of your funds overlap." if len(mine) >= 2 else "Add another fund and I can compare them.",
                        "पूछिए कि आपके कौन से फ़ंड मिलते हैं।" if len(mine) >= 2 else "एक और फ़ंड जोड़िए, मैं तुलना कर दूँगा।"))
    return _done(a, ctx, [("Which of my mutual funds overlap?", "मेरे कौन से म्यूचुअल फ़ंड आपस में मिलते हैं?"), _FU["fee"]], "my_funds")


def h_my_funds_remove(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    ids = find_funds(text)
    if not ids or re.search(r"\b(all|everything|clear)\b", text, re.I):
        ids = my_funds(ctx.conn)
    for fid in ids:
        set_my_fund(ctx.conn, fid, False)
    mine = my_funds(ctx.conn)
    a = Answer(headline=t("Removed: " + (", ".join(_fname(f) for f in ids) or "nothing") + ".", "हटा दिया: " + (", ".join(_fname(f) for f in ids) or "कुछ नहीं") + "।"),
               bullets=[t("Your funds now: " + (", ".join(_fname(f) for f in mine) or "none") + ".", "अब आपके फ़ंड: " + (", ".join(_fname(f) for f in mine) or "कोई नहीं") + "।")])
    return _done(a, ctx, _chips("list", "overlap"), "my_funds")


def h_my_funds_show(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    mine = my_funds(ctx.conn)
    if not mine:
        a = Answer(headline=t("You have not told me about any funds yet.", "आपने अभी तक कोई फ़ंड नहीं बताया है।"),
                   action=t("Say, for example: I own Large Cap Fund A and Bluechip Fund B.", "जैसे कहिए: मेरे पास Large Cap Fund A और Bluechip Fund B है।"))
        return _done(a, ctx, _chips("list"), "my_funds")
    a = Answer(headline=t(f"You have told me about {len(mine)} fund{'s' if len(mine) != 1 else ''}.", f"आपने मुझे {len(mine)} फ़ंड बताए हैं।"),
               table={"columns": [t("Fund", "फ़ंड"), t("Fee", "फ़ीस")], "rows": [[_fname(f), f"{practice.FUNDS[f]['er']}%"] for f in mine]})
    return _done(a, ctx, [("Which of my mutual funds overlap?", "मेरे कौन से म्यूचुअल फ़ंड आपस में मिलते हैं?"), _FU["fee"]], "my_funds")


def h_fund_vs_direct(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    ids = find_funds(text) or my_funds(ctx.conn)
    if not ids:
        a = Answer(headline=t("Tell me which fund to check your direct holdings against.", "बताइए किस फ़ंड से आपके सीधे शेयरों की तुलना करूँ।"),
                   action=t("For example: which of my stocks are already inside Nifty 50 Index Fund?", "जैसे: मेरे कौन से शेयर पहले से Nifty 50 Index Fund में हैं?"))
        return _done(a, ctx, _chips("list"), "fund_vs_direct")
    own = _own(ctx)
    tot = sum(own.values()) or 1.0
    rows, best = [], None
    for fid in ids:
        h = practice.FUNDS[fid]["h"]
        inside = [(tk, v) for tk, v in own.items() if tk in h]
        share = sum(v for _, v in inside) / tot * 100
        rows.append([_fname(fid), f"{share:.0f}%", ", ".join(universe.name(tk) for tk, _ in sorted(inside, key=lambda x: -x[1])[:4]) or "-"])
        best = best or (fid, share)
    fid, share = best
    a = Answer(headline=t(f"{share:.0f}% of what you hold directly is already inside {_fname(fid)}.", f"आपके सीधे शेयरों का {share:.0f}% पहले से {_fname(fid)} में है।"),
               bullets=[t("Buying that fund on top means paying its fee to own more of the same companies.", "उस फ़ंड को ऊपर से ख़रीदना यानी उन्हीं कंपनियों को और ख़रीदने के लिए उसकी फ़ीस देना।")],
               detail=_DISC[1] if ctx.lang == "hi" else _DISC[0],
               table={"columns": [t("Fund", "फ़ंड"), t("Your direct stocks inside", "आपके शेयर जो अंदर हैं"), t("Which", "कौन से")], "rows": rows},
               facts=[_fact(t("Already inside", "पहले से अंदर"), f"{share:.0f}%", "warn" if share > 40 else "")])
    return _done(a, ctx, _chips("overlap", "fee"), "fund_vs_direct")


# ---- fees ------------------------------------------------------------------------------
_RET_CUE = re.compile(r"(return|growth|grow|earn|cagr|xirr|gain|appreciat|yield)", re.I)


def _parse_fee(text: str) -> dict[str, Any]:
    q = tools.quantities(text)
    pcts = q["pct"]
    fee_vals, gross = [], None
    for p in pcts:
        around = text[max(0, int(p["at"]) - 30):int(p["at"]) + 40]
        if re.search(r"(fee|expense|ter\b|charge|commission|plan|brokerage|cost)", around, re.I) and not re.search(r"(return|growth|earn)\w*\s*(of|at|is|=)?\s*$", text[max(0, int(p["at"]) - 20):int(p["at"])], re.I):
            fee_vals.append(p["v"])
        elif _RET_CUE.search(text[max(0, int(p["at"]) - 28):int(p["at"])]) or _RET_CUE.search(text[int(p["at"]):int(p["at"]) + 30]):
            gross = p["v"]
        else:
            fee_vals.append(p["v"])
    roles = tools.money_roles(text)
    years = int(q["years"][0]["v"]) if q["years"] else None
    return {"fees": fee_vals, "gross": gross, "lump": roles["lump"], "monthly": roles["monthly"], "years": years}


def h_fee_drag(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    p = _parse_fee(text)
    fees = sorted(p["fees"], reverse=True)
    hi_fee = fees[0] if fees else 2.0
    lo_fee = fees[1] if len(fees) > 1 else (0.2 if hi_fee > 0.2 else 0.0)
    years = p["years"] or 20
    lump, monthly = p["lump"], p["monthly"]
    assumed = []
    if lump is None and monthly is None:
        lump = 100000.0
        assumed.append(t("₹1 lakh invested once", "एक बार 1 लाख रुपये का निवेश"))
    gross = p["gross"] if p["gross"] is not None else 12.0
    if p["gross"] is None:
        assumed.append(t("12% a year before fees", "फ़ीस से पहले सालाना 12%"))
    if not fees:
        assumed.append(t("a 2% fee against a 0.2% index fund", "2% फ़ीस की तुलना 0.2% के इंडेक्स फ़ंड से"))
    elif len(fees) == 1:
        assumed.append(t(f"compared with a {lo_fee:g}% fund", f"{lo_fee:g}% वाले फ़ंड से तुलना"))
    r = tools.fee_drag(lump or 0.0, monthly or 0.0, years, gross, hi_fee, lo_fee)
    money = tools.inr_hi if ctx.lang == "hi" else tools.inr
    inv_txt = ((t(f"{tools.inr(lump)} once", f"{tools.inr_hi(lump)} एक बार") if lump else "") +
               (" + " if lump and monthly else "") +
               (t(f"{tools.inr(monthly)} a month", f"{tools.inr_hi(monthly)} हर महीने") if monthly else ""))
    a = Answer(headline=t(f"A {hi_fee:g}% fee costs you about {money(r['lost_vs_low'])} over {years} years, compared with a {lo_fee:g}% fund.",
                          f"{hi_fee:g}% की फ़ीस {years} साल में {lo_fee:g}% वाले फ़ंड की तुलना में आपको लगभग {money(r['lost_vs_low'])} का नुक़सान कराती है।"),
               bullets=[t(f"Investing {inv_txt}: you would end with {money(r['final_high'])} at the higher fee and {money(r['final_low'])} at the lower one.",
                          f"निवेश {inv_txt}: ज़्यादा फ़ीस पर अंत में {money(r['final_high'])} और कम फ़ीस पर {money(r['final_low'])} मिलेंगे।"),
                        t(f"The fee quietly takes {r['share_of_gain_lost'] * 100:.0f}% of the growth you would otherwise have had.",
                          f"फ़ीस चुपचाप उस बढ़ोतरी का {r['share_of_gain_lost'] * 100:.0f}% खा जाती है जो वरना आपको मिलती।")],
               action=t("Check the yearly fee (expense ratio) of every fund you hold; direct and index funds are usually the cheapest.",
                        "हर फ़ंड की सालाना फ़ीस (एक्सपेंस रेशियो) देखिए; डायरेक्ट और इंडेक्स फ़ंड आम तौर पर सबसे सस्ते होते हैं।"),
               detail=t("Assumes " + "; ".join(assumed) + ". Net return = gross - fee, compounded monthly, contributions at month end. A projection, not a promise.",
                        "मान्यताएँ: " + "; ".join(assumed) + "। शुद्ध रिटर्न = सकल - फ़ीस, मासिक चक्रवृद्धि। यह अनुमान है, वादा नहीं।") if assumed else
                      t("Net return = gross - fee, compounded monthly. A projection, not a promise.", "शुद्ध रिटर्न = सकल - फ़ीस। यह अनुमान है, वादा नहीं।"),
               facts=[_fact(t(f"At {hi_fee:g}%", f"{hi_fee:g}% पर"), tools.inr(r["final_high"]), "bad"),
                      _fact(t(f"At {lo_fee:g}%", f"{lo_fee:g}% पर"), tools.inr(r["final_low"]), "good"),
                      _fact(t("Lost to the fee", "फ़ीस में गया"), tools.inr(r["lost_vs_low"]), "bad")],
               table={"columns": [t("Year", "साल"), t("Invested", "लगाया"), t(f"At {hi_fee:g}%", f"{hi_fee:g}% पर"), t(f"At {lo_fee:g}%", f"{lo_fee:g}% पर"), t("Difference", "अंतर")],
                      "rows": [[str(pt["year"]), tools.inr(r["principal"] + r["monthly"] * pt["year"] * 12), tools.inr(pt["high"]), tools.inr(pt["low"]), tools.inr(pt["low"] - pt["high"])]
                               for pt in r["points"] if pt["year"] in sorted({max(1, years // 4), max(1, years // 2), max(1, 3 * years // 4), years})]},
               visual={"page": "practice", "label": t("Open the fee slider", "फ़ीस स्लाइडर खोलें"),
                       "params": {"fee": hi_fee, "low": lo_fee, "years": years, "lump": lump or 0, "monthly": monthly or 0, "gross": gross}})
    a.data = {"fee_drag": r}
    return _done(a, ctx, _chips("overlap", "emerg", "goal"), "fee_drag")


# ---- emergency -------------------------------------------------------------------------
def h_emergency(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    q = tools.quantities(text)
    money = [m["v"] for m in q["money"]]
    low = text.lower()
    expenses = cash = invest = income = None
    for m in q["money"]:
        ctx_before = m["ctx"]
        after = low[int(m["at"]):int(m["at"]) + 40]
        if re.search(r"(spend|expense|cost|burn|need|bills|rent|living|outgo)", ctx_before) or re.search(r"^[^.,;]{0,18}(a month|per month|monthly|/month|every month)", after):
            if expenses is None:
                expenses = m["v"]
                continue
        if re.search(r"(income|earn|rent from|salary of|partner)", ctx_before) and income is None and expenses is not None:
            income = m["v"]
            continue
        if re.search(r"(invest|stocks?|shares?|mutual|mf|portfolio)", ctx_before) and invest is None:
            invest = m["v"]
            continue
        if cash is None:
            cash = m["v"]
    if expenses is None and len(money) >= 2:
        # "I have 3 lakh and spend 40k": the smaller figure is the monthly one
        expenses = min(money)
        cash = max(money)
    own_cash = float(getattr(ctx.portfolio, "cash", 0.0) or 0.0)
    used_portfolio_cash = False
    if cash is None and own_cash > 0 and expenses:
        cash, used_portfolio_cash = own_cash, True
    if expenses is None or cash is None:
        a = Answer(headline=t("Tell me your monthly spending and the cash you have, and I will show how long it lasts.",
                              "अपना मासिक ख़र्च और नक़द रक़म बताइए, मैं दिखाऊँगा कि वह कितने महीने चलेगी।"),
                   bullets=[t("For example: I have 3 lakh saved and spend 40000 a month.", "जैसे: मेरे पास 3 लाख रुपये हैं और मैं 40000 हर महीने ख़र्च करता हूँ।")],
                   visual={"page": "practice", "label": t("Open the emergency meter", "इमरजेंसी मीटर खोलें"), "params": {}})
        return _done(a, ctx, [_FU["emerg"]], "emergency")
    r = tools.emergency(cash, expenses, invest or 0.0, 20.0, income or 0.0)
    runway = r["runway_cash"]
    band = r["band"]
    money_f = tools.inr_hi if ctx.lang == "hi" else tools.inr
    if runway is None:
        head = t("Your other income covers your spending, so your savings are not being drawn down.", "आपकी दूसरी आमदनी आपके ख़र्च को पूरा करती है, इसलिए बचत घट नहीं रही।")
    else:
        head = t(f"{money_f(cash)} lasts about {runway:.1f} months at {money_f(r['burn'])} a month.",
                 f"{money_f(cash)} लगभग {runway:.1f} महीने चलेंगे, अगर हर महीने {money_f(r['burn'])} ख़र्च हो।")
    bullets = []
    if runway is not None:
        bullets.append({"red": t("That is under three months: a real risk if your income stopped.", "यह तीन महीने से कम है: आमदनी रुकने पर यह सचमुच जोखिम है।"),
                        "amber": t("That is a reasonable start, but the usual target is six months.", "यह एक ठीक शुरुआत है, पर आम लक्ष्य छह महीने का है।"),
                        "green": t("That meets the usual six-month target.", "यह छह महीने के आम लक्ष्य को पूरा करता है।")}[band])
    if r["shortfall"] > 0:
        bullets.append(t(f"Six months of spending is {money_f(r['target_amount'])}. You are {money_f(r['shortfall'])} short; saving {money_f(r['save_per_month_12'])} a month closes that in a year.",
                         f"छह महीने का ख़र्च {money_f(r['target_amount'])} है। आपके पास {money_f(r['shortfall'])} कम है; हर महीने {money_f(r['save_per_month_12'])} बचाने से साल भर में पूरा हो जाएगा।"))
    if invest:
        bullets.append(t(f"Counting {tools.inr(invest)} of investments after a 20% fall, it would stretch to about {r['runway_all']:.1f} months, but selling into a crash locks in losses.",
                         f"{tools.inr_hi(invest)} के निवेश को 20% गिरावट के बाद जोड़ें तो यह लगभग {r['runway_all']:.1f} महीने चलेगा, पर गिरावट में बेचने से नुक़सान पक्का हो जाता है।"))
    if used_portfolio_cash:
        bullets.append(t("I used the cash in your portfolio as your savings.", "मैंने आपके पोर्टफ़ोलियो के नक़द को आपकी बचत माना है।"))
    a = Answer(headline=head, bullets=bullets,
               action=t("Keep this money somewhere easy to reach, not in shares.", "यह पैसा आसानी से मिलने वाली जगह रखिए, शेयरों में नहीं।"),
               detail=t("Months of cover = cash / (monthly spending - other income). Target: 6 months.", "कवर के महीने = नक़द / (मासिक ख़र्च - दूसरी आमदनी)। लक्ष्य: 6 महीने।"),
               facts=[_fact(t("Lasts", "चलेगा"), "∞" if runway is None else t(f"{runway:.1f} months", f"{runway:.1f} महीने"), {"green": "good", "amber": "warn", "red": "bad"}[band]),
                      _fact(t("Target (6 months)", "लक्ष्य (6 महीने)"), tools.inr(r["target_amount"])),
                      _fact(t("Shortfall", "कमी"), tools.inr(r["shortfall"]), "bad" if r["shortfall"] else "good")],
               table={"columns": [t("After", "बाद में"), t("Cash left", "बचा नक़द")],
                      "rows": [[_mo(pt['month'], ctx.lang == "hi"), tools.inr(pt["cash"])] for pt in r["points"] if pt["month"] in (0, 1, 3, 6, 9, 12)][:6]},
               visual={"page": "practice", "label": t("Open the emergency meter", "इमरजेंसी मीटर खोलें"),
                       "params": {"cash": cash, "exp": expenses, "inc": income or 0, "inv": invest or 0}})
    a.data = {"emergency": r}
    return _done(a, ctx, _chips("fee", "goal", "xray"), "emergency")


# ---- goal ------------------------------------------------------------------------------
def h_goal(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    q = tools.quantities(text)
    roles = tools.money_roles(text)
    years = int(q["years"][0]["v"]) if q["years"] else None
    monthly = roles["monthly"]
    target = None
    for m in q["money"]:
        if monthly is not None and abs(m["v"] - monthly) < 1e-6:
            continue
        if re.search(r"(reach|goal|target|want|need|get to|become|build|accumulate|hit|corpus|worth)", m["ctx"]) or target is None:
            target = m["v"]
    if target is None or not ctx.portfolio.positions:
        a = Answer(headline=t("Tell me the goal amount and how many years you have, and I will show the range of outcomes.",
                              "लक्ष्य की रक़म और कितने साल हैं, यह बताइए। मैं नतीजों की रेंज दिखाऊँगा।") if ctx.portfolio.positions else
                   t("Add your holdings first so I can use how your portfolio has actually behaved.", "पहले अपने शेयर जोड़िए, ताकि मैं देख सकूँ कि आपका पोर्टफ़ोलियो असल में कैसे चला है।"),
                   bullets=[t("For example: will 10000 a month reach 50 lakh in 15 years?", "जैसे: क्या 10000 महीने से 15 साल में 50 लाख बनेंगे?")])
        return _done(a, ctx, [_FU["goal"]], "goal")
    years = years or 10
    monthly = monthly if monthly is not None else 10000.0
    res = goal_mod.fan(ctx.pit, ctx.portfolio, ctx.prices, monthly, years, target)
    if not res.get("ok"):
        a = Answer(headline=t("I do not have enough price history for this portfolio to project a range.", "इस पोर्टफ़ोलियो के लिए अनुमान लगाने लायक़ दामों का इतिहास नहीं है।"))
        return _done(a, ctx, _chips("xray"), "goal")
    last = res["points"][-1]
    pt = res["prob_target"] * 100
    band = "good" if pt >= 70 else "warn" if pt >= 40 else "bad"
    mf = tools.inr_hi if ctx.lang == "hi" else tools.inr
    a = Answer(headline=t(f"In {pt:.0f}% of simulated futures you reach {mf(target)} in {years} years.", f"{years} साल में {mf(target)} तक पहुँचने की संभावना {pt:.0f}% सिमुलेशनों में है।"),
               bullets=[t(f"Typical result: {mf(last['p50'])}. Bad case (1 in 10): {mf(last['p10'])}. Good case (1 in 10): {mf(last['p90'])}.",
                          f"सामान्य नतीजा: {mf(last['p50'])}। बुरा हाल (10 में से 1): {mf(last['p10'])}। अच्छा हाल (10 में से 1): {mf(last['p90'])}।"),
                        t(f"You would put in {mf(res['invested'])} in total, including today's portfolio and {mf(monthly)} a month.",
                          f"आप कुल {mf(res['invested'])} लगाएँगे, आज के पोर्टफ़ोलियो और हर महीने {mf(monthly)} सहित।")],
               action=t("Test a worse market with the 'returns are worse by' slider.", "'रिटर्न इतने कम हों तो' स्लाइडर से ख़राब बाज़ार आज़माइए।"),
               detail=t(f"Built from {res['history_years']} years of this portfolio's own history, mostly a rising market, so the future can be worse. A range, not a forecast.",
                        f"इस पोर्टफ़ोलियो के {res['history_years']} साल के इतिहास से बना, जिसमें बाज़ार ज़्यादातर चढ़ा है, इसलिए भविष्य इससे बुरा हो सकता है। रेंज है, पूर्वानुमान नहीं।"),
               facts=[_fact(t("Chance of reaching", "पहुँचने की संभावना"), f"{pt:.0f}%", band), _fact(t("Typical", "सामान्य"), tools.inr(last["p50"])),
                      _fact(t("Bad case", "बुरा हाल"), tools.inr(last["p10"]), "warn")],
               visual={"page": "learn", "label": t("Open the goal chart", "लक्ष्य चार्ट खोलें"), "params": {"monthly": monthly, "years": years, "target": target}})
    a.data = {"goal": {k: v for k, v in res.items() if k != "points"}}
    return _done(a, ctx, _chips("panic", "emerg", "fee"), "goal")


# ---- panic -----------------------------------------------------------------------------
def h_panic(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    low = text.lower()
    key = "adani_2023" if re.search(r"adani|2023", low) else "rate_shock_2022" if re.search(r"2022|rate", low) else "covid"
    if not ctx.portfolio.positions:
        a = Answer(headline=t("Add your holdings first, then I can replay a crash on them.", "पहले अपने शेयर जोड़िए, फिर मैं उन पर गिरावट दोहराकर दिखाऊँगा।"))
        return _done(a, ctx, _chips("help"), "panic")
    r = panic_mod.replay(ctx.pit, ctx.portfolio, ctx.prices, key)
    if not r.get("points"):
        a = Answer(headline=t("I do not have price history for that period.", "उस दौर का दामों का इतिहास मेरे पास नहीं है।"))
        return _done(a, ctx, _chips("help"), "panic")
    mf = tools.inr_hi if ctx.lang == "hi" else tools.inr
    trough, end, start = r["trough_value"], r["end_value"], r["start_value"]
    diff = end - trough
    name = {"covid": t("the Covid crash", "कोविड की गिरावट"), "rate_shock_2022": t("the 2022 rate shock", "2022 की ब्याज दरों की मार"),
            "adani_2023": t("the January 2023 selloff", "जनवरी 2023 की बिकवाली")}[key]
    if diff > 0:
        head = t(f"Selling at the lowest point of {name} would have locked in {mf(trough)}; holding to the end of the window was worth {mf(end)}, {mf(diff)} more.",
                 f"{name} के सबसे निचले बिंदु पर बेचने से {mf(trough)} पक्का हो जाता; खिड़की के अंत तक रुकने पर {mf(end)} होता, यानी {mf(diff)} ज़्यादा।")
    else:
        head = t(f"In {name}, selling at the low would have given {mf(trough)} and holding ended at {mf(end)}: holding did not win this time.",
                 f"{name} में निचले बिंदु पर बेचने पर {mf(trough)} मिलता और रुकने पर {mf(end)}: इस बार रुकना जीता नहीं।")
    a = Answer(headline=head,
               bullets=[t(f"Your portfolio was worth {mf(start)} at the start of that window and {mf(trough)} at its lowest, a fall of {(1 - trough / start) * 100:.0f}%.",
                          f"उस दौर की शुरुआत में पोर्टफ़ोलियो {mf(start)} का था और सबसे निचले बिंदु पर {mf(trough)} का, यानी {(1 - trough / start) * 100:.0f}% की गिरावट।")],
               action=t("History is not a promise: some falls keep going. Decide your limit before a crash, not during it.", "इतिहास वादा नहीं है: कुछ गिरावटें चलती रहती हैं। सीमा गिरावट से पहले तय कीजिए, गिरावट के बीच नहीं।"),
               detail=t("Your current holdings valued at real closing prices through that window.", "आपके मौजूदा शेयर उस दौर के असली बंद भावों पर।"),
               facts=[_fact(t("If sold at the low", "सबसे नीचे बेचा"), tools.inr(trough), "bad"), _fact(t("If held", "रुके रहे"), tools.inr(end), "good" if diff > 0 else "warn")],
               visual={"page": "protect", "label": t("Open the replay", "रीप्ले खोलें"), "params": {"episode": key}})
    return _done(a, ctx, _chips("goal", "emerg", "xray"), "panic")


# ---- digest ----------------------------------------------------------------------------
def h_digest(text: str, ctx: Ctx) -> Answer:
    import datetime
    t = _t(ctx.lang)
    d = digest_mod.build(ctx.pit, ctx.portfolio, ctx.prices, ctx.policy, ctx.lang, datetime.date.today().isocalendar()[1])
    secs = d["sections"]
    a = Answer(headline=d["headline"], bullets=[f"{s['title']}: {s['text']}" for s in secs[1:]],
               speech=d["spoken"],
               action=t("Press play on the Practice page to hear it as a one-minute briefing.", "एक मिनट की ब्रीफ़िंग सुनने के लिए Practice पेज पर प्ले दबाइए।"),
               visual={"page": "practice", "label": t("Open the weekly digest", "साप्ताहिक सार खोलें"), "params": {}})
    return _done(a, ctx, _chips("xray", "overlap", "scam"), "digest")


# ---- scams -----------------------------------------------------------------------------
def h_scam_help(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    lost = re.search(r"\b(lost|gave|shared|paid|sent|transferred|already|fell for|victim|scammed|cheated|debited|deducted)\b", text, re.I)
    if lost:
        a = Answer(headline=t("Act in the next few minutes: the first hour matters most.", "अगले कुछ मिनटों में कार्रवाई कीजिए: पहला घंटा सबसे अहम है।"),
                   bullets=[t("1. Call 1930 (the cyber fraud helpline) or report at cybercrime.gov.in, with the amount, time and the number used.",
                              "1. 1930 (साइबर ठगी हेल्पलाइन) पर फ़ोन कीजिए या cybercrime.gov.in पर रक़म, समय और इस्तेमाल हुए नंबर के साथ शिकायत कीजिए।"),
                            t("2. Call your bank's official number now and ask them to block the card, UPI and net banking.", "2. अभी अपने बैंक के आधिकारिक नंबर पर फ़ोन करके कार्ड, UPI और नेट बैंकिंग बंद करवाइए।"),
                            t("3. Remove any app they made you install, change your banking passwords, and keep screenshots and messages.", "3. जो ऐप उन्होंने इंस्टॉल करवाया उसे हटाइए, बैंकिंग पासवर्ड बदलिए, और स्क्रीनशॉट व संदेश सँभालकर रखिए।")],
                   action=t("Do not send any more money to 'recover' it: that is a second scam.", "पैसा वापस पाने के नाम पर और पैसे मत भेजिए: वह दूसरी ठगी है।"))
        return _done(a, ctx, _chips("scam", "help"), "scam_help")
    flags = []
    if re.search(r"otp|cvv|pin\b|password", text, re.I):
        flags.append(t("It asks for an OTP, PIN or CVV: no bank or officer ever does.", "यह OTP, पिन या CVV माँगता है: कोई बैंक या अधिकारी कभी नहीं माँगता।"))
    if re.search(r"anydesk|quicksupport|teamviewer|remote|install|download|app\b|link", text, re.I):
        flags.append(t("It asks you to install an app or open a link: that hands them your phone.", "यह ऐप इंस्टॉल करने या लिंक खोलने को कहता है: इससे आपका फ़ोन उनके हाथ में चला जाता है।"))
    if re.search(r"arrest|police|cbi|customs|court|parcel|warrant", text, re.I):
        flags.append(t("Police and courts never arrest or ask for money over a call; there is no such thing as a digital arrest.", "पुलिस और अदालत कॉल पर गिरफ़्तारी या पैसा नहीं माँगती; डिजिटल अरेस्ट जैसी कोई चीज़ नहीं।"))
    if re.search(r"kyc|blocked|expire|urgent|minutes|immediately", text, re.I):
        flags.append(t("A deadline of minutes is a pressure tactic; real banks send written notices.", "मिनटों की समय-सीमा दबाव की चाल है; असली बैंक लिखित नोटिस भेजते हैं।"))
    if not flags:
        flags.append(t("Any unexpected call or message that rushes you or asks for money, a code or an app is a red flag.", "कोई भी अनचाही कॉल या संदेश जो जल्दी मचाए या पैसा, कोड या ऐप माँगे, ख़तरे की निशानी है।"))
    a = Answer(headline=t("Treat this as a scam until you have checked it yourself.", "जब तक आप ख़ुद जाँच न लें, इसे ठगी ही मानिए।"),
               bullets=flags[:3],
               action=t("Hang up, then call the number printed on your card or the official website. Report at 1930.", "फ़ोन काटिए, फिर कार्ड पर छपे या आधिकारिक वेबसाइट के नंबर पर ख़ुद फ़ोन कीजिए। 1930 पर शिकायत कीजिए।"),
               facts=[_fact(t("Helpline", "हेल्पलाइन"), "1930", "good")],
               visual={"page": "practice", "label": t("Rehearse this call", "इस कॉल का अभ्यास करें"), "params": {}})
    return _done(a, ctx, _chips("scam", "digest", "help"), "scam_help")


def _tip_body(text: str) -> str:
    m = re.search(r"[:\n]\s*(.{25,})$", text, re.S)
    q = re.search(r"[\"“'](.{25,})[\"”']", text, re.S)
    return (q.group(1) if q else m.group(1) if m else text).strip()


def h_tip_scan(text: str, ctx: Ctx) -> Answer:
    from analysis import scanner
    t = _t(ctx.lang)
    body = _tip_body(text)
    if len(body.split()) < 6:
        a = Answer(headline=t("Paste the tip itself and I will check it for scam tactics and for claims I can test.", "टिप ख़ुद चिपकाइए, मैं ठगी की चालें और जाँच लायक़ दावे परखूँगा।"),
                   bullets=[t("For example: Is this tip legit: SURE SHOT! TCS profit up 300%, target 9000, join my VIP group.", "जैसे: क्या यह टिप सही है: पक्की टिप! TCS का मुनाफ़ा 300% बढ़ा, टारगेट 9000, मेरे VIP ग्रुप में जुड़ें।")])
        return _done(a, ctx, _chips("scam"), "tip_scan")
    r = scanner.scan(ctx.pit, body)
    if r.get("empty"):
        a = Answer(headline=t("I could not find anything to check in that.", "उसमें जाँचने लायक़ कुछ नहीं मिला।"))
        return _done(a, ctx, _chips("scam"), "tip_scan")
    band = r.get("tone", "")
    verdict = {"red": t("High risk of a scam", "ठगी का ऊँचा जोखिम"), "amber": t("Some warning signs", "कुछ चेतावनी के संकेत"),
               "green": t("No scam tactics found", "ठगी की कोई चाल नहीं मिली")}.get(band, r.get("verdict", ""))
    a = Answer(headline=t(f"{verdict}: risk score {r['score']} out of 100.", f"{verdict}: जोखिम स्कोर सौ में से {r['score']}।"),
               bullets=[t("Tactic found: " + f["label"] + f" ({f['quote']}).", "चाल मिली: " + f["label"] + f" ({f['quote']})।") for f in r["flags"][:3]] +
                       [t(f"Claim tested: {c['text']} is {c['status']}.", f"दावा जाँचा: {c['text']} → {c['status']}।") for c in r["claims"][:2]],
               action=t("Do not act on it. Check the company on the exchange site, and never pay anyone to join a tips group.", "इस पर कार्रवाई मत कीजिए। कंपनी की जाँच एक्सचेंज की साइट पर कीजिए, और टिप ग्रुप में जुड़ने के लिए पैसे कभी मत दीजिए।"),
               facts=[_fact(t("Risk score", "जोखिम स्कोर"), f"{r['score']}/100", {"red": "bad", "amber": "warn", "green": "good"}.get(band, ""))],
               visual={"page": "protect", "label": t("Open the tip scanner", "टिप स्कैनर खोलें"), "params": {}})
    return _done(a, ctx, _chips("scam", "predict" if False else "panic", "help"), "tip_scan")


# ---- ledger ----------------------------------------------------------------------------
def h_ledger(text: str, ctx: Ctx) -> Answer:
    t = _t(ctx.lang)
    v = ledger_mod.verify(ctx.conn)
    if v["ok"]:
        head = t(f"Your record is intact: {v['entries']} entr{'y' if v['entries'] == 1 else 'ies'}, none altered.", f"आपका रिकॉर्ड सुरक्षित है: {v['entries']} प्रविष्टियाँ, किसी में बदलाव नहीं।")
    else:
        head = t(f"Tampering detected at entry {v['broken_at']}. Everything after it cannot be trusted.", f"प्रविष्टि {v['broken_at']} पर छेड़छाड़ मिली। उसके बाद का कुछ भरोसेमंद नहीं।")
    a = Answer(headline=head,
               bullets=[t("Each trade stores a fingerprint of the one before it, so editing any past entry breaks every later one. The database also refuses edits and deletes.",
                          "हर लेन-देन पिछले का फ़िंगरप्रिंट रखता है, इसलिए कोई पुरानी प्रविष्टि बदलने से बाद की सारी टूट जाती हैं। डेटाबेस बदलाव और मिटाना भी नहीं मानता।")],
               facts=[_fact(t("Entries", "प्रविष्टियाँ"), str(v["entries"])), _fact(t("Status", "स्थिति"), t("Intact", "सुरक्षित") if v["ok"] else t("Broken", "टूटा"), "good" if v["ok"] else "bad")],
               visual={"page": "govern", "label": t("Try to tamper with it", "छेड़छाड़ करके देखें"), "params": {}})
    return _done(a, ctx, _chips("xray", "help"), "ledger")


HANDLERS: dict[str, Callable[[str, Ctx], Answer]] = {
    "help": h_help, "chitchat": h_chitchat, "clarify": h_clarify, "out_of_scope": h_out_of_scope, "predict": h_predict,
    "fund_overlap": h_fund_overlap, "fund_list": h_fund_list, "fund_info": h_fund_info, "fund_vs_direct": h_fund_vs_direct,
    "my_funds_add": h_my_funds_add, "my_funds_remove": h_my_funds_remove, "my_funds_show": h_my_funds_show,
    "fee_drag": h_fee_drag, "emergency": h_emergency, "goal": h_goal, "panic": h_panic, "digest": h_digest,
    "scam_help": h_scam_help, "tip_scan": h_tip_scan, "ledger": h_ledger,
}


def _drop_echo(a: Answer, asked: str) -> None:
    """Never offer, as a next step, the very question that was just asked."""
    def norm(x: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", x.lower()).strip()
    keep = [i for i, q in enumerate(a.follow_ups) if norm(q) != norm(asked)]
    a.follow_ups = [a.follow_ups[i] for i in keep]
    if a.follow_ups_hi:
        a.follow_ups_hi = [a.follow_ups_hi[i] for i in keep if i < len(a.follow_ups_hi)]


# =================================================================== LLM intent fallback
INTENT_DOC = {
    "fund_overlap": "do mutual funds hold the same stocks / are funds duplicates / compare two funds",
    "fund_list": "which sample mutual funds are available",
    "fund_info": "what stocks a particular fund holds",
    "fund_vs_direct": "how much of the user's own direct stocks is already inside a fund",
    "my_funds_add": "the user states which funds they own",
    "my_funds_show": "show the funds the user saved",
    "fee_drag": "what a fund fee / expense ratio / plan type costs over time",
    "emergency": "how long cash savings last without income / emergency fund",
    "goal": "will a SIP or portfolio reach a target amount in some years / retirement planning",
    "panic": "what would have happened if the user sold during a crash",
    "digest": "weekly summary of the user's portfolio",
    "scam_help": "a suspicious call/message/link, OTP request, or the user was scammed",
    "tip_scan": "check if a pasted stock tip / group promise is legitimate",
    "predict": "asks for price predictions or hot stock picks",
    "ledger": "is the trade record tamper-proof",
    "help": "what can the assistant do",
    "xray": "overall health summary of the user's portfolio",
    "why": "why is the portfolio risk high / main risks",
    "fix": "what to sell or reduce to lower risk",
    "stress": "what happens in a market fall or crash scenario",
    "diversification": "is the portfolio spread out enough",
    "correlation": "which holdings move together",
    "should_buy": "should the user buy / add a specific stock",
    "define": "definition of a finance term",
    "out_of_scope": "unrelated to money or investing",
    "none": "none of these / too unclear",
}


async def llm_intent(text: str) -> tuple[str | None, float]:
    """Ask the local model to PICK one intent from the closed list above. It never writes the
    answer: whatever it picks is run by the same calculators, and a handler that lacks the
    figures it needs still asks for them."""
    from agents.llm import ANALYST_MODEL, chat_json
    schema = {"type": "object", "properties": {"intent": {"type": "string", "enum": list(INTENT_DOC)},
                                                 "confidence": {"type": "number"}}, "required": ["intent", "confidence"]}
    menu = "\n".join(f"- {k}: {v}" for k, v in INTENT_DOC.items())
    prompt = (f"Classify the user's message about money into exactly one intent.\nIntents:\n{menu}\n\n"
              f"Message: {text}\nReturn the best intent and your confidence from 0 to 1. "
              f"If it is unclear, choose none.")
    try:
        out = await chat_json(prompt, schema, model=ANALYST_MODEL, temperature=0.0, max_tokens=40,
                              attempts=1, timeout=8.0)
    except Exception:  # noqa: BLE001
        return None, 0.0
    intent = out.get("intent")
    return (intent if intent in INTENT_DOC else None), float(out.get("confidence") or 0.0)


LLM_MIN = 0.75


# =================================================================== entry point
def _run(intent: str, how: str, resolved: str, ctx: Ctx) -> Answer:
    convo = ctx.convo
    if intent in HANDLERS:
        out = HANDLERS[intent](resolved, ctx)
        if convo is not None and intent not in ("clarify", "chitchat", "out_of_scope"):
            convo.last_question = resolved
        out.data["intent"] = intent
        out.data["routed_by"] = how
        _drop_echo(out, resolved)
        return out
    out = explain.answer(resolved, ctx.pit, ctx.portfolio, ctx.prices, ctx.policy, convo=convo,
                         level=ctx.level, kind=intent if intent in LEGACY else None)
    out.data["intent"] = intent
    out.data["routed_by"] = how
    if convo is not None:
        convo.last_question = None
    return out


def answer(text: str, ctx: Ctx) -> Answer:
    """One question in, one structured answer out."""
    convo = ctx.convo
    resolved = convo.resolve(text) if convo and hasattr(convo, "resolve") else text
    intent, how = detect(resolved)

    # "explain that simpler" after a tool answer: replay that question at the simpler level.
    if intent == "simplify" and convo is not None and getattr(convo, "last_kind", None) in NEW_KINDS and getattr(convo, "last_question", None):
        ctx.level = "simple"
        resolved = convo.last_question
        intent, how = detect(resolved)
    return _run(intent, how, resolved, ctx)


async def aanswer(text: str, ctx: Ctx) -> Answer:
    """Like answer(), but when the rules do not recognise the question a local model may pick
    the intent. Anything it is not confident about is asked about, never guessed."""
    resolved = ctx.convo.resolve(text) if ctx.convo is not None and hasattr(ctx.convo, "resolve") else text
    intent, how = detect(resolved)
    # Specific rules are trusted. The model is consulted when nothing matched, and also when
    # only one of the older loose keyword rules matched on a long sentence (a stray word like
    # "fall" or "invest" can mislead those); it must be confident to overrule them.
    if intent != "clarify" and not (how == "legacy" and len(resolved.split()) >= 8):
        return answer(text, ctx)
    picked, conf = await llm_intent(resolved)
    if picked and picked != "none" and conf >= LLM_MIN and picked != intent:
        out = _run(picked, "llm", resolved, ctx)
        out.data["llm_confidence"] = round(conf, 2)
        return out
    return answer(text, ctx)
