"""Practice tools: fund-overlap checker and scam-call rehearsal.

Fund holdings below are ILLUSTRATIVE samples (rounded, typical of each fund type), not live
factsheets -- the app is free and offline, so it cannot pull real ones. The overlap maths is
the standard one: shared weight = sum over common stocks of the smaller of the two weights.
The scam-call engine is deterministic keyword rules, no model: a rehearsal must behave the
same every time and never say anything a real caller would not.
"""
from __future__ import annotations

import re
from typing import Any

from backend.practice_hi import FLAGS_HI, SCENARIOS_HI, classify_hi

FUNDS: dict[str, dict[str, Any]] = {
    "nifty_index": {"name": "Nifty 50 Index Fund", "kind": "Index", "er": 0.20, "h": {
        "HDFCBANK.NS": 13, "RELIANCE.NS": 9, "ICICIBANK.NS": 8, "INFY.NS": 6, "ITC.NS": 4, "TCS.NS": 4,
        "LT.NS": 4, "BHARTIARTL.NS": 4, "AXISBANK.NS": 3, "KOTAKBANK.NS": 3, "SBIN.NS": 3, "M&M.NS": 2.5,
        "HINDUNILVR.NS": 2.5, "BAJFINANCE.NS": 2, "MARUTI.NS": 2, "SUNPHARMA.NS": 2, "TITAN.NS": 1.5}},
    "largecap_a": {"name": "Sample Large Cap Fund A", "kind": "Active", "er": 1.60, "h": {
        "HDFCBANK.NS": 9, "ICICIBANK.NS": 8, "RELIANCE.NS": 7, "INFY.NS": 6, "TCS.NS": 5, "LT.NS": 4,
        "BHARTIARTL.NS": 4, "AXISBANK.NS": 4, "SBIN.NS": 3, "ITC.NS": 3, "MARUTI.NS": 2.5,
        "KOTAKBANK.NS": 2.5, "SUNPHARMA.NS": 2, "BAJFINANCE.NS": 2, "ASIANPAINT.NS": 1.5}},
    "bluechip_b": {"name": "Sample Bluechip Fund B", "kind": "Active", "er": 1.70, "h": {
        "HDFCBANK.NS": 9.5, "ICICIBANK.NS": 8.5, "RELIANCE.NS": 6, "INFY.NS": 5.5, "TCS.NS": 4.5,
        "LT.NS": 4, "BHARTIARTL.NS": 3.5, "AXISBANK.NS": 3.5, "SBIN.NS": 3, "KOTAKBANK.NS": 3,
        "ITC.NS": 2.5, "HINDUNILVR.NS": 2, "BAJFINANCE.NS": 2, "TITAN.NS": 2, "NESTLEIND.NS": 1.5}},
    "flexicap_c": {"name": "Sample Flexi Cap Fund C", "kind": "Active", "er": 1.55, "h": {
        "HDFCBANK.NS": 8, "ICICIBANK.NS": 7, "INFY.NS": 5, "RELIANCE.NS": 4, "BAJFINANCE.NS": 4,
        "TITAN.NS": 3.5, "PERSISTENT.NS": 3, "COFORGE.NS": 3, "SUNPHARMA.NS": 3, "M&M.NS": 3,
        "TATAELXSI.NS": 2, "APOLLOHOSP.NS": 2.5, "ASIANPAINT.NS": 2, "ULTRACEMCO.NS": 2, "DIVISLAB.NS": 2}},
    "it_fund": {"name": "Sample Technology Fund", "kind": "Sector", "er": 1.0, "h": {
        "TCS.NS": 17, "INFY.NS": 17, "HCLTECH.NS": 9, "WIPRO.NS": 6, "TECHM.NS": 6, "PERSISTENT.NS": 7,
        "COFORGE.NS": 6, "MPHASIS.NS": 5, "LTTS.NS": 4, "TATAELXSI.NS": 4}},
    "bank_fund": {"name": "Sample Banking Fund", "kind": "Sector", "er": 1.1, "h": {
        "HDFCBANK.NS": 22, "ICICIBANK.NS": 20, "AXISBANK.NS": 10, "KOTAKBANK.NS": 9, "SBIN.NS": 9,
        "INDUSINDBK.NS": 4, "BAJFINANCE.NS": 5, "BAJAJFINSV.NS": 3, "HDFCLIFE.NS": 2, "SBILIFE.NS": 2}},
    "pharma_fund": {"name": "Sample Healthcare Fund", "kind": "Sector", "er": 1.2, "h": {
        "SUNPHARMA.NS": 18, "CIPLA.NS": 10, "DRREDDY.NS": 10, "DIVISLAB.NS": 9, "APOLLOHOSP.NS": 9}},
    "consumption": {"name": "Sample Consumption Fund", "kind": "Sector", "er": 1.3, "h": {
        "HINDUNILVR.NS": 12, "ITC.NS": 11, "NESTLEIND.NS": 8, "TITAN.NS": 8, "BRITANNIA.NS": 6,
        "TATACONSUM.NS": 5, "MARUTI.NS": 7, "ASIANPAINT.NS": 6, "M&M.NS": 6, "BHARTIARTL.NS": 6}},
}


def fund_list() -> list[dict[str, Any]]:
    return [{"id": k, "name": v["name"], "kind": v["kind"], "er": v["er"],
             "top": sorted(v["h"], key=v["h"].get, reverse=True)[:3]} for k, v in FUNDS.items()]


def overlap(a: str, b: str, name_of, own: dict[str, float] | None = None) -> dict[str, Any]:
    fa, fb = FUNDS[a], FUNDS[b]
    ha, hb = fa["h"], fb["h"]
    shared = [{"ticker": t, "name": name_of(t), "wa": ha[t], "wb": hb[t], "common": min(ha[t], hb[t])}
              for t in ha if t in hb]
    shared.sort(key=lambda r: -r["common"])
    pct = sum(r["common"] for r in shared)
    ta, tb = sum(ha.values()), sum(hb.values())
    share = pct / min(ta, tb) if min(ta, tb) else 0.0       # share of the smaller fund that is duplicated
    dearer = max(fa["er"], fb["er"])

    def side(f: dict, fid: str, h: dict) -> dict:
        return {"id": fid, "name": f["name"], "er": f["er"], "kind": f["kind"],
                "holdings": [{"ticker": t, "name": name_of(t), "w": w}
                             for t, w in sorted(h.items(), key=lambda x: -x[1])]}

    out: dict[str, Any] = {
        "a": side(fa, a, ha), "b": side(fb, b, hb),
        "shared": shared, "overlap_pct": round(share * 100, 1), "shared_stocks": len(shared),
        # per Rs 1 lakh in the smaller-overlap fund: the duplicated slice pays the dearer fee
        # for stocks already held through the other fund
        "wasted_fee_per_lakh": round(100000 * share * dearer / 100),
        "verdict": "red" if share > 0.6 else "amber" if share > 0.3 else "green"}
    if own:
        tot = sum(own.values()) or 1.0
        out["own_in_a"] = round(sum(w for t, w in own.items() if t in ha) / tot * 100, 1)
        out["own_in_b"] = round(sum(w for t, w in own.items() if t in hb) / tot * 100, 1)
        out["own_names"] = [name_of(t) for t in own if t in ha or t in hb][:6]
    return out


# ------------------------------------------------------------------ scam-call rehearsal
FLAGS = {
    "authority": ("Claims to be someone official", "Callers invent a title so you stop questioning them."),
    "urgency": ("Fake deadline", "Panic switches off checking. Real banks give written notice, not 30 minutes."),
    "otp": ("Asks for an OTP / PIN / CVV", "No bank, ever, asks for these. An OTP exists only to approve money leaving YOU."),
    "secrecy": ("Do not tell anyone", "Isolation is the scammer's key move: family would spot it instantly."),
    "remote": ("Asks you to install a remote-control app", "Gives them your screen, your banking app and your OTP messages."),
    "threat": ("Threatens arrest or a frozen account", "Police and courts do not arrest by phone or video call."),
    "money": ("Asks you to move money to be safe", "There is no safe account. Any transfer requested over a call is the theft."),
    "greed": ("Guaranteed returns", "Guaranteed high returns do not exist; the promise is the bait."),
}

SCENARIOS: dict[str, dict[str, Any]] = {
    "kyc": {"title": "Bank KYC call", "caller": "Bank Security Dept", "number": "+91 98xxx 44021",
            "loss": 240000, "intro": "Unknown number calling...",
            "nodes": [
                {"line": "Good afternoon sir, I am calling from the bank's security department. Your KYC has expired and your account will be blocked in thirty minutes.",
                 "flags": ["authority", "urgency"], "danger": False,
                 "hints": ["Okay, what do I need to do?", "Which branch are you calling from?", "I will hang up and call the bank on its official number."]},
                {"line": "Sir, I am sending a six digit code to your phone right now. Please read it out to me so I can update your KYC.",
                 "flags": ["otp"], "danger": True,
                 "hints": ["It is 482913.", "Why do you need the code?", "No. Banks never ask for codes. I am calling the bank myself."]},
                {"line": "Sir, do not disconnect. If you hang up, two lakh forty thousand rupees will be frozen. And please do not tell your family, this is confidential.",
                 "flags": ["threat", "secrecy", "urgency"], "danger": False,
                 "hints": ["Please do not freeze it, I will do whatever you say.", "Why can I not tell my family?", "This is a scam. I am hanging up."]},
                {"line": "Then install the QuickSupport app from the link I am sending, so I can fix it on your phone directly.",
                 "flags": ["remote"], "danger": True,
                 "hints": ["Okay, installing it now.", "What does that app do?", "No. I am not installing anything. Goodbye."]}]},
    "police": {"title": "Digital arrest", "caller": "Cyber Crime Cell", "number": "Video call, +91 70xxx 19350",
               "loss": 850000, "intro": "Video call request from a police officer...",
               "nodes": [
                {"line": "This is Inspector Rane, Cyber Crime. A parcel in your name carrying illegal items was intercepted. There is an arrest warrant against you.",
                 "flags": ["authority", "threat"], "danger": False,
                 "hints": ["Please sir, I have done nothing wrong!", "Can you send me the warrant in writing?", "Police do not arrest on video calls. I am hanging up."]},
                {"line": "You are under digital arrest. Stay on this call, do not leave the room and do not speak to anyone. This is a national security matter.",
                 "flags": ["secrecy", "threat", "urgency"], "danger": False,
                 "hints": ["Okay, I will stay on the call.", "Who is your senior officer?", "There is no such thing as digital arrest. Goodbye."]},
                {"line": "To prove your innocence, transfer your savings to the RBI verification account. It will be refunded after the check.",
                 "flags": ["money", "authority"], "danger": True,
                 "hints": ["I will transfer it now.", "Why would the RBI hold my money?", "No transfer. I am calling 1930 and my local police."]}]},
    "invest": {"title": "WhatsApp investment tip", "caller": "Priya, Wealth Club", "number": "WhatsApp call, +91 88xxx 77310",
               "loss": 150000, "intro": "Added you to a group with 240 members...",
               "nodes": [
                {"line": "Hi! I am Priya from the Wealth Club. Our members made forty percent last month. Our expert's tips are guaranteed, and slots close tonight.",
                 "flags": ["greed", "urgency", "authority"], "danger": False,
                 "hints": ["Sounds amazing, yes I want to join!", "Is your firm registered with SEBI?", "Guaranteed returns do not exist. Not interested."]},
                {"line": "See these screenshots, everyone is profiting. Just download our trading app and deposit fifty thousand to start. Do not share this with outsiders, it is a private club.",
                 "flags": ["greed", "secrecy", "money"], "danger": True,
                 "hints": ["Okay, depositing fifty thousand now.", "Can I withdraw whenever I want?", "Screenshots are easy to fake. I will not deposit, bye."]}]},
}

_DIGITS = re.compile(r"\b\d{4,8}\b")
_VERIFY = re.compile(r"(scam|fraud|fake|hang(ing)? up|call(ing)? (the )?(bank|back|1930|police)|official|"
                     r"1930|cyber ?crime|not (share|sharing|installing|interested|transfer)|will not|never ask|"
                     r"no such thing|goodbye|sebi|registered|in writing|branch|visit|verify|senior officer)", re.I)
_REFUSE = re.compile(r"(\bno\b|\bnot\b|\bnever\b|\bstop\b|\bbye\b|goodbye|don't|won't|hang(ing)? up|scam)", re.I)
_COMPLY = re.compile(r"(\b(ok(ay)?|sure|yes|here|installing|installed|share|sending|transfer|transferring|"
                     r"deposit|depositing|do whatever|please|stay)\b)", re.I)


def classify(text: str) -> str:
    """refuse = hard stop, verify = checking the caller out, comply = doing what was asked,
    stall = unsure. A reply carrying a code-like number is always compliance."""
    t = text.strip()
    if _DIGITS.search(t.replace("1930", "")):
        return "comply"
    if _VERIFY.search(t):
        return "refuse" if _REFUSE.search(t) else "verify"
    if _COMPLY.search(t):
        return "comply"
    return "stall" if t.endswith("?") or len(t.split()) > 2 else "comply"


def _f(code: str, lang: str = "en") -> dict[str, str]:
    label, why = (FLAGS_HI if lang == "hi" else FLAGS)[code]
    return {"code": code, "label": label, "why": why}


def scam_step(scenario: str, node: int, reply: str | None, pressure: int = 0,
              lang: str = "en") -> dict[str, Any]:
    sc = SCENARIOS[scenario]
    hi = SCENARIOS_HI[scenario] if lang == "hi" else None
    nodes = sc["nodes"]
    view = hi["nodes"] if hi else nodes
    if reply is None:                                       # opening line
        n = nodes[0]
        return {"status": "continue", "node": 0, "line": view[0]["line"],
                "flags": [_f(c, lang) for c in n["flags"]], "hints": view[0]["hints"], "pressure": 25}
    node = max(0, min(node, len(nodes) - 1))
    cur = nodes[node]
    kind = classify_hi(reply) if lang == "hi" else classify(reply)
    if kind == "refuse" or (kind == "verify" and cur["danger"]):
        return {"status": "won", "kind": kind, "pressure": 0,
                "feedback": ("आपने ठगी रोक दी। फ़ोन काटकर कार्ड पर छपे या आधिकारिक नंबर पर ख़ुद फ़ोन करना बिल्कुल सही है।"
                             if lang == "hi" else
                             "You stopped it. Hanging up and calling the number on your card or the official site is exactly right.")}
    if kind == "comply" and cur["danger"]:
        return {"status": "lost", "kind": kind, "pressure": 100, "loss": sc["loss"],
                "feedback": (f"असली ठग के पास अब {sc['loss']:,} रुपये तक पहुँच होती। जैसे ही कोड, ऐप या ट्रांसफ़र माँगा गया, कॉल वहीं ख़त्म हो जानी चाहिए थी।"
                             if lang == "hi" else
                             f"A real scammer would now have access to Rs {sc['loss']:,}. The moment they asked for a code, an app or a transfer, the call should have ended.")}
    p = min(95, pressure + (30 if kind == "comply" else 12))
    nxt = node + 1
    if nxt >= len(nodes):                                   # kept asking questions to the end
        return {"status": "won", "kind": kind, "pressure": p,
                "feedback": ("आपने कुछ नहीं दिया। सवाल पूछना अच्छा है, पर कॉल जल्दी काट देना और भी सुरक्षित है।"
                             if lang == "hi" else
                             "You never handed anything over. Questioning is good, but ending the call earlier is safer.")}
    n = nodes[nxt]
    return {"status": "continue", "kind": kind, "node": nxt, "line": view[nxt]["line"],
            "flags": [_f(c, lang) for c in n["flags"]], "hints": view[nxt]["hints"], "pressure": p}


def scenario_list(lang: str = "en") -> list[dict[str, Any]]:
    out = []
    for k, v in SCENARIOS.items():
        h = SCENARIOS_HI[k] if lang == "hi" else v
        out.append({"id": k, "title": h["title"], "caller": h["caller"], "number": h["number"],
                    "intro": h["intro"], "loss": v["loss"], "steps": len(v["nodes"])})
    return out
