"""Guided tours: every feature in the prototype, as an ordered walk the page can follow on screen.

One source for two jobs:
  * the assistant matches a question ("how do I use the fee slider", "walk me through Govern") to a tour and
    answers in plain structured text (what it is, how to use it, what you will see);
  * the front end plays the same tour: it opens the page, spotlights each part in turn, and reads the caption
    aloud while the person watches it.

A step is {route, sel, click, title, body}. `sel` is a CSS selector for the part to spotlight (no `sel` = a
caption in the middle of the screen), `click` is something to press first (open a tab, pick a tool). The player
never fails on a missing element: it shows the caption without a spotlight. Text is written in both languages
by hand; nothing here is generated or translated at run time.
"""
from __future__ import annotations

import re
from typing import Any


def S(route: str, sel: str | None, t_en: str, t_hi: str, b_en: str, b_hi: str, click: str | None = None) -> dict[str, Any]:
    return {"route": route, "sel": sel, "click": click, "title": {"en": t_en, "hi": t_hi}, "body": {"en": b_en, "hi": b_hi}}


def _tour(tid: str, route: str, title: tuple[str, str], pattern: str, what: tuple[str, str], how: tuple[list[str], list[str]],
          example: tuple[str, str], steps: list[dict[str, Any]], area: tuple[str, str] = ("", "")) -> dict[str, Any]:
    return {"id": tid, "route": route, "title": {"en": title[0], "hi": title[1]}, "rx": re.compile(pattern, re.I),
            "what": {"en": what[0], "hi": what[1]}, "how": {"en": how[0], "hi": how[1]},
            "example": {"en": example[0], "hi": example[1]}, "steps": steps, "area": {"en": area[0], "hi": area[1]}}


NAV = ".navlinks"

TOURS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------ the whole prototype
    _tour("overview", "/", ("The whole app in two minutes", "पूरा ऐप दो मिनट में"),
          r"\b(whole|entire|full|overall|complete)\b.{0,12}\b(app|prototype|product|demo|system|project|platform)\b|\b(this|the) (app|prototype|product|demo|project|platform)\b|\b(all|every|each)\b.{0,10}\bfeatures?\b|\bwhat (is|does) (this|jarvis)\b|\bgive me a tour\b|\bshow me around\b|\bfeatures? (of|in) (this|the)\b|\bhow does jarvis work\b|\bwhat can (this|jarvis)\b",
          ("Jarvis is a plain-language guard for your money: it shows what you own, checks tips and scam calls, tests trades against your own limits, researches a stock in plain words, and works for rural users on WhatsApp and in Hindi.",
           "जार्विस आपके पैसे की सरल भाषा में रखवाली करता है: आपके पास क्या है यह दिखाता है, टिप और ठग कॉल जाँचता है, आपकी अपनी सीमाओं पर ट्रेड परखता है, किसी शेयर को सरल शब्दों में खँगालता है, और ग्रामीण उपयोगकर्ताओं के लिए व्हाट्सऐप और हिंदी में चलता है।"),
          (["Each tile on the home page opens one area; the top bar moves between them on every screen.",
            "Ask the assistant in words or by voice and it opens the right page and does the task.",
            "Every figure comes from a calculator, never from a language model's guess."],
           ["होम पेज का हर डिब्बा एक हिस्सा खोलता है; ऊपर की पट्टी हर स्क्रीन पर उनके बीच ले जाती है।",
            "सहायक से शब्दों या आवाज़ में पूछिए; वह सही पेज खोलकर काम कर देता है।",
            "हर आँकड़ा कैलकुलेटर से आता है, किसी भाषा-मॉडल के अंदाज़े से नहीं।"]),
          ("Take me through the whole app", "पूरा ऐप घुमाइए"),
          [S("/", ".tiles", "Home: nine doors", "होम: नौ दरवाज़े",
             "Home is a menu, not a long page. Each tile opens one area: your portfolio, protection from scams, rural tools, WhatsApp, learning, practice, your rules, research, and the assistant.",
             "होम एक मेनू है, लंबा पेज नहीं। हर डिब्बा एक हिस्सा खोलता है: आपका पोर्टफ़ोलियो, ठगी से सुरक्षा, ग्रामीण औज़ार, व्हाट्सऐप, सीखना, अभ्यास, आपके नियम, शोध और सहायक।"),
           S("/", NAV, "The top bar", "ऊपर की पट्टी", "The same pages are always one tap away in this bar, on every screen.", "यही पेज हर स्क्रीन पर इस पट्टी में एक टैप दूर रहते हैं।"),
           S("/portfolio", '[data-tour="pf-xray"]', "Portfolio: what you own", "पोर्टफ़ोलियो: आपके पास क्या है",
             "The X-ray gives a health grade, how spread out the money really is, your biggest industry and the worst fall this mix has survived. Click any number to see how it was worked out.",
             "एक्स-रे सेहत का ग्रेड, पैसा असल में कितना बँटा है, आपका सबसे बड़ा उद्योग और इस मिश्रण की अब तक की सबसे बड़ी गिरावट दिखाता है। किसी भी संख्या पर क्लिक करके देखिए वह कैसे निकली।"),
           S("/protect", ".deck", "Protect: scams and tips", "सुरक्षा: ठगी और टिप",
             "Five tools: a recovery coach for the first hour after a scam, a tip checker, a tax shield, a panic-sell replay and standing rules that speak up only when something flips.",
             "पाँच औज़ार: ठगी के बाद पहले घंटे का रिकवरी कोच, टिप जाँचक, टैक्स बचत, घबराकर बेचने का रिप्ले और ऐसे स्थायी नियम जो तभी बोलते हैं जब कुछ पलटे।"),
           S("/govern", '.gov-hero', "Govern: your own limits", "नियम: आपकी अपनी सीमाएँ",
             "Your limits per stock, per industry and for cash are held by a firewall no analyst or button can override. Every decision, approved or blocked, goes into a record that cannot be quietly edited.",
             "प्रति शेयर, प्रति उद्योग और नक़द की आपकी सीमाओं को एक फ़ायरवॉल थामे रखता है जिसे कोई विश्लेषक या बटन नहीं लाँघ सकता। हर फ़ैसला, मंज़ूर या रोका गया, एक ऐसे रिकॉर्ड में जाता है जिसे चुपके से बदला नहीं जा सकता।"),
           S("/research", "#research-ticker", "Research: any listed stock", "शोध: कोई भी सूचीबद्ध शेयर",
             "Type or search a company. Four analysts and a sceptic study it, and the page then explains it in plain words with good points, things to watch and how much to trust each.",
             "किसी कंपनी का नाम लिखिए या खोजिए। चार विश्लेषक और एक संशयी उसे परखते हैं, और पेज उसे सरल शब्दों में समझाता है: अच्छी बातें, ध्यान देने की बातें और हर एक पर कितना भरोसा।"),
           S("/rural", '.rural-groups', "Rural: twelve everyday tools", "ग्रामीण: बारह रोज़मर्रा के औज़ार",
             "Moneylender interest, credit score, is this offer real, UPI safety, policies, government schemes, papers, harvest planning and more. All work offline in Hindi.",
             "साहूकार का ब्याज, क्रेडिट स्कोर, क्या यह ऑफ़र असली है, UPI सुरक्षा, पॉलिसी, सरकारी योजनाएँ, काग़ज़, फ़सल की योजना और बहुत कुछ। सब हिंदी में ऑफ़लाइन चलते हैं।"),
           S("/assistant", '[data-tour="composer"]', "Assistant: ask in your own words", "सहायक: अपने शब्दों में पूछिए",
             "Type or speak anything. It opens the right page, shows the chart or the numbers, and can walk you through any feature on screen, exactly like this tour.",
             "कुछ भी लिखिए या बोलिए। यह सही पेज खोलता है, चार्ट या आँकड़े दिखाता है, और किसी भी फ़ीचर को स्क्रीन पर इसी तरह घुमाकर समझा सकता है।")]),

    # ------------------------------------------------------------------ assistant
    _tour("assistant", "/assistant", ("The assistant", "सहायक"),
          r"\b(assistant|chat ?bot|chat window|the orb|talk to jarvis|ask jarvis|voice (input|mode|reply|replies)|microphone|the mic|speak to)\b",
          ("A chat and voice assistant that understands what you ask, answers with the figures and a chart where one helps, and opens the right page for you.",
           "एक चैट और आवाज़ वाला सहायक जो आपका सवाल समझता है, जहाँ काम आए वहाँ आँकड़ों और चार्ट के साथ जवाब देता है, और आपके लिए सही पेज खोलता है।"),
          (["Type in the box at the bottom, or press the mic and speak.", "Each answer is laid out under your question: the short answer first, then the key figures, a chart or table, the steps, and follow-ups you can tap.", "Ask 'how does the fee slider work' and it walks you through that feature on screen."],
           ["नीचे के बॉक्स में लिखिए, या माइक दबाकर बोलिए।", "हर जवाब आपके सवाल के नीचे सजा होता है: पहले छोटा जवाब, फिर मुख्य आँकड़े, चार्ट या तालिका, क़दम और टैप करने लायक़ अगले सवाल।", "पूछिए 'फ़ीस स्लाइडर कैसे काम करता है' और यह उस फ़ीचर को स्क्रीन पर घुमाकर दिखाएगा।"]),
          ("How does the assistant work?", "सहायक कैसे काम करता है?"),
          [S("/assistant", '[data-tour="composer"]', "Ask here", "यहाँ पूछिए", "Type a question or press the mic and speak. English and Hindi both work. Press the slash key anywhere to jump to this box.", "सवाल लिखिए या माइक दबाकर बोलिए। अंग्रेज़ी और हिंदी दोनों चलती हैं। कहीं से भी स्लैश (/) दबाइए, कर्सर इस बॉक्स में आ जाएगा।"),
           S("/assistant", '[data-tour="chat"]', "Answers appear as cards", "जवाब कार्ड की तरह आते हैं", "Your question stays on top of its answer so you always see what was asked. The short answer comes first, then the key figures, a chart or table when it helps, the steps to take and tappable follow-ups.", "आपका सवाल अपने जवाब के ऊपर रहता है ताकि हमेशा दिखे कि क्या पूछा गया था। पहले छोटा जवाब, फिर मुख्य आँकड़े, काम आए तो चार्ट या तालिका, उठाने के क़दम और टैप करने लायक़ अगले सवाल।"),
           S("/assistant", '[data-tour="orb"]', "The voice orb", "आवाज़ वाला ऑर्ब", "Tap the orb to speak. Your voice is turned into text on this machine and shown back as 'I heard' before it is answered. The orb moves while it speaks.", "बोलने के लिए ऑर्ब दबाइए। आपकी आवाज़ इसी मशीन पर लिखत में बदलती है और जवाब से पहले 'मैंने सुना' के रूप में दिखती है। बोलते समय ऑर्ब हिलता है।"),
           S("/assistant", '[data-tour="jobs"]', "Jobs: start from a goal", "काम: लक्ष्य से शुरू कीजिए", "Not sure what to ask? Pick a job such as checking your portfolio's health, fixing a problem, or getting ready for tax season, and a guided flow takes you through it.", "क्या पूछें, पता नहीं? कोई काम चुनिए, जैसे पोर्टफ़ोलियो की सेहत जाँचना, कोई दिक़्क़त ठीक करना या टैक्स का मौसम, और एक निर्देशित प्रवाह आपको चलाएगा।"),
           S("/assistant", '[data-tour="tours"]', "Guided tours of every feature", "हर फ़ीचर की निर्देशित सैर", "Pick any feature here, or just ask 'help me understand the audit record', and the page walks you through it step by step while it talks.", "यहाँ से कोई भी फ़ीचर चुनिए, या बस पूछिए 'ऑडिट रिकॉर्ड समझाइए', और पेज बोलते हुए आपको क़दम-दर-क़दम घुमाएगा।")]),

    # ------------------------------------------------------------------ portfolio
    _tour("portfolio", "/portfolio", ("Portfolio", "पोर्टफ़ोलियो"),
          r"\b(portfolio|x-?ray|health (grade|score)|allocation|treemap|where my money (sits|is)|positions? table|the portfolio page)\b",
          ("The picture of what you own: a health grade, how spread out the money really is, how it behaved against the market, where it sits, and what to do next.",
           "आपके पास जो है उसकी तस्वीर: सेहत का ग्रेड, पैसा असल में कितना बँटा है, बाज़ार के मुक़ाबले उसका बर्ताव, वह कहाँ लगा है, और आगे क्या करना है।"),
          (["Read the X-ray first: the grade and the one-line verdict under it.", "Move over the chart to read any day and switch between 1M, 3M, 6M and 1Y.", "Click any underlined number to open how it was calculated.", "Use 'Who are you?' to change the limits to a retail, serious or boutique investor."],
           ["पहले एक्स-रे पढ़िए: ग्रेड और उसके नीचे एक पंक्ति का निष्कर्ष।", "चार्ट पर घुमाकर कोई भी दिन पढ़िए और 1M, 3M, 6M, 1Y बदलिए।", "किसी भी रेखांकित संख्या पर क्लिक कीजिए, वह कैसे निकली दिखेगा।", "'आप कौन हैं?' से सीमाएँ खुदरा, गंभीर या बुटीक निवेशक के हिसाब से बदलिए।"]),
          ("Explain the portfolio page", "पोर्टफ़ोलियो पेज समझाइए"),
          [S("/portfolio", '[data-tour="pf-xray"]', "The X-ray", "एक्स-रे", "A grade out of 100 against the limits for your investor type, your total value, the number of holdings, how many positions it behaves like, your biggest industry, the worst fall so far and the market sensitivity. Click any number for its working.", "आपके निवेशक-प्रकार की सीमाओं के हिसाब से 100 में से ग्रेड, कुल मूल्य, कितने शेयर हैं, वह असल में कितने शेयरों जैसा चलता है, सबसे बड़ा उद्योग, अब तक की सबसे बड़ी गिरावट और बाज़ार के प्रति संवेदनशीलता। किसी संख्या पर क्लिक करके उसका हिसाब देखिए।"),
           S("/portfolio", '[data-tour="pf-chart"]', "Your money over time", "समय के साथ आपका पैसा", "Today's share counts valued back through history, against the market index. It shows what this basket would have done, not what you earned. Move over the chart to read any day.", "आज के शेयरों की संख्या को इतिहास में पीछे तक आँका गया है, बाज़ार सूचकांक के साथ। यह दिखाता है कि यह टोकरी क्या करती, आपने क्या कमाया वह नहीं। चार्ट पर घुमाकर कोई भी दिन पढ़िए।"),
           S("/portfolio", '[data-tour="pf-alloc"]', "Where your money sits", "आपका पैसा कहाँ लगा है", "Each tile is a company and its size is its share of the portfolio, grouped by industry. A red outline means that industry is over your own limit.", "हर डिब्बा एक कंपनी है और उसका आकार पोर्टफ़ोलियो में उसका हिस्सा है, उद्योग के हिसाब से समूहित। लाल घेरे का मतलब है कि वह उद्योग आपकी सीमा से ऊपर है।"),
           S("/portfolio", '[data-tour="pf-actions"]', "What to do next", "आगे क्या करें", "A short, ranked list of the things most worth doing, each with the reason and a button that opens the guided steps for it.", "सबसे ज़रूरी कामों की छोटी, क्रमबद्ध सूची, हर एक के कारण के साथ और एक बटन जो उसके निर्देशित क़दम खोलता है।"),
           S("/portfolio", '[data-tour="pf-positions"]', "Holdings and what moves together", "शेयर और जो साथ चलते हैं", "The positions with their weights and gains, how much each one contributed, and which holdings tend to fall together, which is what really decides how safe the mix is.", "शेयर अपने हिस्से और लाभ के साथ, हर एक का योगदान, और कौन से शेयर साथ गिरते हैं, जो असल में तय करता है कि मिश्रण कितना सुरक्षित है।")]),

    # ------------------------------------------------------------------ research
    _tour("research", "/research", ("Research desk", "शोध डेस्क"),
          r"\b(research (desk|page)|analyst desks?|the analysts|arena|investigate|stock research|pros and cons|plain words|time machine|research feature|study a stock)\b",
          ("Pick any listed company. Four analysts and a sceptic study it from the evidence, and the page then gives a plain-words summary: good points, things to watch, how current the data is, and how much to trust each point. It never says buy or sell.",
           "कोई भी सूचीबद्ध कंपनी चुनिए। चार विश्लेषक और एक संशयी सबूतों से उसे परखते हैं, और पेज फिर सरल शब्दों में सार देता है: अच्छी बातें, ध्यान देने की बातें, डेटा कितना ताज़ा है, और हर बात पर कितना भरोसा। यह कभी ख़रीदने या बेचने को नहीं कहता।"),
          (["Search a company by name and press 'Run the analysts'.", "Watch the arena: each analyst reads its evidence and sends claims to the middle, the sceptic knocks out the weak ones.", "Read the plain-words summary below it. 'Solid', 'light' and 'weak' tell you how much each point rests on.", "Use the time machine to see only what was known on an earlier day."],
           ["किसी कंपनी को नाम से खोजिए और 'विश्लेषकों को चलाइए' दबाइए।", "अखाड़ा देखिए: हर विश्लेषक अपने सबूत पढ़कर बीच में दावे भेजता है और संशयी कमज़ोर दावों को हटा देता है।", "उसके नीचे सरल शब्दों का सार पढ़िए। 'पक्का', 'हल्का' और 'कमज़ोर' बताते हैं कि हर बात किस आधार पर टिकी है।", "समय मशीन से देखिए कि किसी पुराने दिन तक क्या पता था।"]),
          ("Show me how the research page works", "शोध पेज कैसे काम करता है दिखाइए"),
          [S("/research", "#research-ticker", "Choose a company", "कंपनी चुनिए", "Type a name or a symbol. If it is not in the list, search for it and it is fetched live with its prices and statements.", "नाम या सिंबल लिखिए। सूची में न हो तो खोजिए, उसके भाव और बही-खाते सीधे लाए जाते हैं।"),
           S("/research", ".arena", "The analysts at work", "काम करते विश्लेषक", "Four analysts and a sceptic are shown as nodes. As each reads its evidence it sends a claim to the middle; the sceptic rejects the ones the evidence does not support, and what survives becomes the outcome.", "चार विश्लेषक और एक संशयी बिंदुओं के रूप में दिखते हैं। हर एक सबूत पढ़कर बीच में दावा भेजता है; संशयी उन दावों को ठुकराता है जिन्हें सबूत का सहारा नहीं, और जो बचता है वही नतीजा बनता है।"),
           S("/research", ".sum", "The summary in plain words", "सरल शब्दों में सार", "Good points on one side, things to watch on the other. Each line says what kind of data it rests on and shows a Solid, Light or Weak mark, so you know how much to lean on it.", "एक तरफ़ अच्छी बातें, दूसरी तरफ़ ध्यान देने की बातें। हर पंक्ति बताती है कि वह किस तरह के डेटा पर टिकी है और पक्का, हल्का या कमज़ोर का निशान दिखाती है।"),
           S("/research", ".sum-ranks", "Against similar companies", "समान कंपनियों के मुक़ाबले", "Each bar shows where this company stands among its industry peers on price against profit, return on money, margin, sales growth and debt. Left is the best in the group.", "हर पट्टी दिखाती है कि भाव बनाम मुनाफ़ा, पैसे पर कमाई, मार्जिन, बिक्री की बढ़त और क़र्ज़ में यह कंपनी अपने उद्योग की साथी कंपनियों में कहाँ है। बाएँ का मतलब समूह में सबसे अच्छी।"),
           S("/research", ".sum-fresh", "How current is it?", "यह कितना ताज़ा है?", "How old each kind of data is, and how many of the possible checks had data at all. Old or missing data is shown honestly rather than hidden.", "हर तरह का डेटा कितना पुराना है और कितनी संभव जाँचों के लिए डेटा था। पुराना या ग़ायब डेटा छिपाया नहीं जाता, साफ़ दिखाया जाता है।"),
           S("/research", '[data-tour="res-time"]', "The time machine", "समय मशीन", "Rewind the clock and the analysts can only see what was known on that day. It is how you check whether an analysis would have been useful, without hindsight.", "घड़ी पीछे कीजिए तो विश्लेषक उतना ही देख पाते हैं जितना उस दिन पता था। इसी से जाँचा जाता है कि कोई विश्लेषण बाद की जानकारी के बिना काम का होता या नहीं।")]),

    # ------------------------------------------------------------------ protect + tools
    _tour("protect", "/protect", ("Protect", "सुरक्षा"),
          r"\b(protect (page|section|area)|the protect|protection tools?|safety tools?|scam (check\w*|detect\w*|protect\w*|safety|feature|tool|help)|fraud (check\w*|feature|tool|protection))\b",
          ("Five tools that keep you from losing money to scams and bad timing: a recovery coach, a tip checker, a tax shield, a panic-sell replay and standing rules.",
           "पाँच औज़ार जो आपको ठगी और ग़लत समय से पैसा खोने से बचाते हैं: रिकवरी कोच, टिप जाँचक, टैक्स बचत, घबराकर बेचने का रिप्ले और स्थायी नियम।"),
          (["Pick a card; the tool opens underneath.", "The red card is for emergencies: use it first if money has already gone."],
           ["कोई कार्ड चुनिए; औज़ार उसके नीचे खुलता है।", "लाल कार्ड आपात स्थिति के लिए है: पैसा चला गया हो तो पहले उसे खोलिए।"]),
          ("Walk me through the Protect page", "सुरक्षा पेज घुमाइए"),
          [S("/protect", ".deck", "Five tools, one at a time", "पाँच औज़ार, एक-एक करके", "Each card is a tool. Choosing one opens it below, so the page stays short and you see only what you need.", "हर कार्ड एक औज़ार है। एक चुनने पर वह नीचे खुलता है, इसलिए पेज छोटा रहता है और आपको सिर्फ़ ज़रूरी चीज़ दिखती है।"),
           S("/protect?tool=recovery", ".deck-card:nth-child(1)", "I think I was scammed", "मुझे लगता है ठगी हुई", "Choose what happened and get the steps in the right order, with the helpline and who to call first.", "बताइए क्या हुआ और सही क्रम में क़दम पाइए, हेल्पलाइन और सबसे पहले किसे फ़ोन करना है, इसके साथ।"),
           S("/protect?tool=tip", ".deck-card:nth-child(2)", "Check a stock tip", "स्टॉक टिप जाँचें", "Paste a message from Telegram or WhatsApp and see which scam tactics it uses and which claims do not match the data.", "टेलीग्राम या व्हाट्सऐप का संदेश चिपकाइए और देखिए कि उसमें ठगी की कौन सी चालें हैं और कौन से दावे आँकड़ों से नहीं मिलते।"),
           S("/protect?tool=tax", ".deck-card:nth-child(3)", "Tax shield", "टैक्स बचत", "For each holding: what selling today would cost in tax, and what waiting for the one-year mark would save.", "हर शेयर के लिए: आज बेचने पर कितना टैक्स लगेगा, और एक साल पूरा होने तक रुकने पर कितना बचेगा।"),
           S("/protect?tool=panic", ".deck-card:nth-child(4)", "Panic-sell replay", "घबराकर बेचने का असर", "Real prices from a real crash applied to your holdings: what selling at the bottom would have cost.", "असली गिरावट के असली भाव आपके शेयरों पर: सबसे निचले भाव पर बेचने की क़ीमत क्या होती।"),
           S("/protect?tool=watch", ".deck-card:nth-child(5)", "Tell me if…", "बताइए अगर…", "Set a standing rule once and it is checked every time your portfolio moves. It speaks up only when something flips.", "एक बार स्थायी नियम बनाइए और आपका पोर्टफ़ोलियो हिलने पर हर बार जाँचा जाता है। यह तभी बोलता है जब कुछ पलटे।")]),

    _tour("recovery", "/protect?tool=recovery", ("Scam recovery coach", "ठगी रिकवरी कोच"),
          r"\b(recovery coach|scam recovery|i was scammed (tool|feature)|i think i was scammed|first hour|recovery (tool|feature))\b",
          ("A step-by-step coach for the first hour after a scam. You say what happened and it orders the steps: freeze, call, report, and what not to do.", "ठगी के बाद पहले घंटे के लिए क़दम-दर-क़दम कोच। आप बताते हैं क्या हुआ और यह क़दम क्रम में रखता है: रोकना, फ़ोन, शिकायत और क्या नहीं करना।"),
          (["Choose what happened.", "Follow the numbered steps in order; each has a time such as 'now' or 'within the hour'.", "Use the helpline 1930 and the portal cybercrime.gov.in."], ["चुनिए क्या हुआ।", "क्रमांकित क़दम क्रम से कीजिए; हर एक के साथ समय है जैसे 'अभी' या 'एक घंटे में'।", "हेल्पलाइन 1930 और पोर्टल cybercrime.gov.in का उपयोग कीजिए।"]),
          ("Explain the scam recovery coach", "ठगी रिकवरी कोच समझाइए"),
          [S("/protect?tool=recovery", ".deck-stage", "Say what happened", "बताइए क्या हुआ", "Six situations: money taken, an OTP shared, a remote app installed, a fake investment, a fake police call or a clicked link. Pick the closest one.", "छह स्थितियाँ: पैसा निकला, OTP बताया, रिमोट ऐप डाली, नक़ली निवेश, नक़ली पुलिस कॉल या क्लिक किया हुआ लिंक। सबसे क़रीब वाली चुनिए.")]),

    _tour("tip", "/protect?tool=tip", ("Stock-tip checker", "स्टॉक टिप जाँचक"),
          r"\b(tip (checker|scanner|check)|check (a |the )?(stock )?tips?|scan (a )?tip|telegram tips?)\b",
          ("Paste a tip from Telegram, WhatsApp or Instagram. It is checked against dated company data on this machine and against known scam tactics. No AI opinion is involved.", "टेलीग्राम, व्हाट्सऐप या इंस्टाग्राम की टिप चिपकाइए। इसे इसी मशीन पर कंपनी के तारीख़ वाले डेटा और ठगी की जानी-पहचानी चालों से जाँचा जाता है। इसमें किसी AI की राय नहीं होती।"),
          (["Paste the message.", "Read which tactics it uses: guaranteed returns, urgency, secrecy, paying to join.", "See which claims about the company do not match the data."], ["संदेश चिपकाइए।", "देखिए उसमें कौन सी चालें हैं: पक्का मुनाफ़ा, जल्दबाज़ी, गोपनीयता, जुड़ने के पैसे।", "देखिए कंपनी के बारे में कौन से दावे आँकड़ों से नहीं मिलते।"]),
          ("How does the tip checker work?", "टिप जाँचक कैसे काम करता है?"),
          [S("/protect?tool=tip", ".deck-stage", "Paste, then check", "चिपकाइए, फिर जाँचिए", "Try one of the three examples: a typical scam tip, a claim that does not match the data, and a calm ordinary note. Each shows how the checker reasons.", "तीन उदाहरणों में से एक आज़माइए: एक आम ठगी की टिप, आँकड़ों से न मिलता दावा, और एक शांत सामान्य नोट। हर एक दिखाता है कि जाँचक कैसे सोचता है।")]),

    _tour("tax", "/protect?tool=tax", ("Tax shield", "टैक्स बचत"),
          r"\b(tax shield|capital gains|ltcg|stcg|long[- ]term gains?|short[- ]term gains?|tax on (my )?(sale|gains)|tax saving by waiting)\b",
          ("Shares sold within a year are taxed at 20%, after a year at 12.5% above the yearly exemption. For each holding it shows what selling today costs and what waiting would save.", "एक साल के भीतर बेचे शेयरों पर 20% टैक्स लगता है, एक साल बाद सालाना छूट से ऊपर 12.5%। हर शेयर के लिए दिखाता है कि आज बेचने की क़ीमत क्या है और रुकने से क्या बचेगा।"),
          (["Read the headline: how much you could save by waiting.", "Check each holding's days held against the 365-day mark.", "Add your real purchase prices: cost basis is never guessed."], ["शीर्षक पढ़िए: रुकने से कितना बच सकता है।", "हर शेयर के रखे गए दिन 365 दिन के निशान से मिलाइए।", "अपने असली ख़रीद भाव जोड़िए: लागत कभी अंदाज़े से नहीं ली जाती।"]),
          ("Explain the tax shield", "टैक्स बचत समझाइए"),
          [S("/protect?tool=tax", ".deck-stage", "What waiting would save", "रुकने से क्या बचेगा", "The table lists each holding, how long you have held it, the gain, the tax if sold today and whether it is short term or long term. The last column says plainly what to do and how many days remain.", "तालिका में हर शेयर, कितने दिन रखा, लाभ, आज बेचने पर टैक्स और वह अल्पकालिक है या दीर्घकालिक। आख़िरी कॉलम साफ़ बताता है क्या करना है और कितने दिन बचे हैं।")]),

    _tour("panic", "/protect?tool=panic", ("Panic-sell replay", "घबराकर बेचने का रिप्ले"),
          r"\b(panic[- ]?sell|panic replay|crash replay|what if i had sold|sell in a crash|covid crash replay)\b",
          ("Real prices from a real crash, applied to your holdings. Drag to choose the day you would have sold and see what it cost versus holding.", "असली गिरावट के असली भाव आपके शेयरों पर। बेचने का दिन चुनने के लिए खींचिए और देखिए रुके रहने की तुलना में कितना नुक़सान होता।"),
          (["Choose an episode: Covid crash, the 2022 rate shock or the January 2023 sell-off.", "Drag along the chart to pick the day you would have sold.", "Compare what you locked in with what holding would have given."], ["एक दौर चुनिए: कोविड गिरावट, 2022 का दर झटका या जनवरी 2023 की बिकवाली।", "चार्ट पर खींचकर वह दिन चुनिए जब आप बेचते।", "तुलना कीजिए कि बेचकर क्या पक्का हुआ और रुकने पर क्या मिलता।"]),
          ("Show me the panic-sell replay", "पैनिक-सेल रिप्ले दिखाइए"),
          [S("/protect?tool=panic", ".deck-stage", "Pick a day, see the cost", "दिन चुनिए, क़ीमत देखिए", "The ring marks the lowest point. Selling there locks in the loss; the result shows what you would have had if you had waited. History is not a promise: some crashes keep falling.", "घेरा सबसे निचला बिंदु दिखाता है। वहाँ बेचने पर नुक़सान पक्का हो जाता है; नतीजा दिखाता है कि रुकते तो क्या मिलता। इतिहास वादा नहीं है: कुछ गिरावटें लगातार जारी रहती हैं।")]),

    _tour("watch", "/protect?tool=watch", ("Standing rules: Tell me if…", "स्थायी नियम: बताइए अगर…"),
          r"\b(tell me if|standing rules?|watch ?list|watch rules?|alerts?|notify me|price alert|rule alerts)\b",
          ("Set a rule once, for example 'tell me if technology goes above 35%', and it is checked every time your portfolio moves. It only speaks when a rule flips, so you are not flooded.", "एक बार नियम बनाइए, जैसे 'बताइए अगर टेक्नोलॉजी 35% से ऊपर जाए', और पोर्टफ़ोलियो हिलने पर हर बार जाँचा जाता है। यह तभी बोलता है जब नियम पलटे, इसलिए शोर नहीं होता।"),
          (["Write the rule in words.", "It is checked automatically after every move.", "You hear about it only when it changes."], ["नियम शब्दों में लिखिए।", "हर बदलाव के बाद अपने आप जाँचा जाता है।", "आपको तभी बताया जाता है जब वह बदले।"]),
          ("How do standing rules work?", "स्थायी नियम कैसे काम करते हैं?"),
          [S("/protect?tool=watch", ".deck-stage", "Rules that speak only when something flips", "नियम जो तभी बोलते हैं जब कुछ पलटे", "Add a rule and it appears here with its current state. A rule that has just flipped is announced once, not on every tick.", "नियम जोड़िए और वह अपनी मौजूदा स्थिति के साथ यहाँ दिखता है। जो नियम अभी पलटा उसकी घोषणा एक बार होती है, हर टिक पर नहीं।")]),

    # ------------------------------------------------------------------ practice + tools
    _tour("practice", "/practice", ("Practice", "अभ्यास"),
          r"\b(practice (page|section|area)|the practice|practice tools?)\b",
          ("Five hands-on tools: compare funds for overlap, see what a fee costs, measure your emergency cushion, hear your weekly digest and rehearse a scam call.", "पाँच प्रयोगात्मक औज़ार: फ़ंड ओवरलैप की तुलना, फ़ीस की क़ीमत, इमरजेंसी गद्दी की माप, साप्ताहिक सार सुनना और ठग कॉल का अभ्यास।"),
          (["Pick a card to open the tool.", "Every slider re-calculates instantly from the same calculators the assistant uses."], ["औज़ार खोलने के लिए कार्ड चुनिए।", "हर स्लाइडर वही कैलकुलेटर इस्तेमाल करके तुरंत दोबारा हिसाब लगाता है जो सहायक करता है।"]),
          ("Walk me through the Practice page", "अभ्यास पेज घुमाइए"),
          [S("/practice", ".deck", "Five tools", "पाँच औज़ार", "Each card opens one tool underneath. They are the same calculators the assistant uses, so a number you see here matches what it tells you in chat.", "हर कार्ड नीचे एक औज़ार खोलता है। ये वही कैलकुलेटर हैं जो सहायक इस्तेमाल करता है, इसलिए यहाँ का आँकड़ा चैट वाले आँकड़े से मिलता है।"),
           S("/practice?tool=overlap", ".deck-card:nth-child(1)", "Fund overlap", "फ़ंड ओवरलैप", "Pick two funds and watch the shared holdings light up.", "दो फ़ंड चुनिए और साझा शेयर चमकते देखिए।"),
           S("/practice?tool=fee", ".deck-card:nth-child(2)", "Fee drag", "फ़ीस का असर", "Slide the fee and the years and see the gap open on the chart.", "फ़ीस और साल खिसकाइए और चार्ट पर अंतर बढ़ता देखिए।"),
           S("/practice?tool=emergency", ".deck-card:nth-child(3)", "Emergency meter", "इमरजेंसी मीटर", "How many months your money would last if income stopped.", "आमदनी रुके तो आपका पैसा कितने महीने चलेगा।"),
           S("/practice?tool=digest", ".deck-card:nth-child(4)", "Weekly digest", "साप्ताहिक सार", "A one-minute spoken summary of your portfolio.", "आपके पोर्टफ़ोलियो का एक मिनट का बोला हुआ सार।"),
           S("/practice?tool=rehearsal", ".deck-card:nth-child(5)", "Scam-call rehearsal", "ठग कॉल का अभ्यास", "A caller pressures you with real tactics; you practise saying no.", "एक कॉलर असली चालों से दबाव डालता है; आप मना करने का अभ्यास करते हैं।")]),

    _tour("overlap", "/practice?tool=overlap", ("Fund overlap checker", "फ़ंड ओवरलैप जाँचक"),
          r"\b(overlap (checker|tool|feature|page)|fund overlap (tool|feature|page|checker)|how (does|do) (the )?overlap|compare funds? tool)\b",
          ("Two 'different' funds can quietly hold the same stocks, so you pay two managers for one portfolio. This tool shows the shared holdings of any two funds and how much they overlap.", "दो 'अलग' फ़ंड चुपचाप एक ही शेयर रख सकते हैं, तब आप एक ही पोर्टफ़ोलियो के लिए दो मैनेजरों को पैसा देते हैं। यह औज़ार किन्हीं दो फ़ंड के साझा शेयर और ओवरलैप दिखाता है।"),
          (["Tap the star on funds you own to save them.", "Pick two funds from the list.", "Read the overlap percentage and the shared stocks."], ["जो फ़ंड आपके पास हैं उन पर तारा दबाकर सहेजिए।", "सूची से दो फ़ंड चुनिए।", "ओवरलैप प्रतिशत और साझा शेयर पढ़िए।"]),
          ("How does the fund overlap tool work?", "फ़ंड ओवरलैप औज़ार कैसे काम करता है?"),
          [S("/practice?tool=overlap", ".deck-stage", "Pick any two funds", "कोई भी दो फ़ंड चुनिए", "Each fund lists its biggest holdings with their weights. Choosing two shows what they share. The holdings are illustrative samples typical of each fund type, not live factsheets.", "हर फ़ंड अपने सबसे बड़े शेयर उनके हिस्से के साथ दिखाता है। दो चुनने पर साझा शेयर दिखते हैं। ये हर फ़ंड-प्रकार के नमूने हैं, ताज़ा फ़ैक्टशीट नहीं।")]),

    _tour("fee", "/practice?tool=fee", ("Fee drag", "फ़ीस का असर"),
          r"\b(fee (drag|slider|calculator|tool)|expense ratio (tool|slider|calculator)|how (does|do) the fee)\b",
          ("A small yearly fee quietly eats a big share of your growth. The sliders show your fund against a cheap fund and against no fee at all.", "छोटी सालाना फ़ीस आपकी बढ़त का बड़ा हिस्सा चुपचाप खा जाती है। स्लाइडर आपके फ़ंड को सस्ते फ़ंड और बिना फ़ीस वाले से तुलना करके दिखाते हैं।"),
          (["Set the lump sum, monthly SIP and years.", "Set the return and your fund's fee.", "Hover the chart to read any year."], ["एकमुश्त रक़म, मासिक SIP और साल तय कीजिए।", "रिटर्न और अपने फ़ंड की फ़ीस तय कीजिए।", "चार्ट पर घुमाकर कोई भी साल पढ़िए।"]),
          ("How does the fee slider work?", "फ़ीस स्लाइडर कैसे काम करता है?"),
          [S("/practice?tool=fee", ".deck-stage", "Move the sliders", "स्लाइडर खिसकाइए", "The three lines are a cheap fund, your fund and no fee. The gap between them is what the fee takes. The note under the chart gives the exact rupees lost and the share of your growth that went to the fee. This is a projection, not a promise.", "तीन रेखाएँ हैं: सस्ता फ़ंड, आपका फ़ंड और बिना फ़ीस। उनके बीच का अंतर वही है जो फ़ीस ले जाती है। चार्ट के नीचे का नोट खोई गई ठीक रक़म और आपकी बढ़त का कितना हिस्सा फ़ीस में गया यह बताता है। यह अनुमान है, वादा नहीं।")]),

    _tour("emergency", "/practice?tool=emergency", ("Emergency-fund meter", "इमरजेंसी मीटर"),
          r"\b(emergency (meter|tool|calculator|fund meter)|runway tool|savings meter)\b",
          ("If your income stopped, how many months would your money last? Cash, spending, income that continues and investments you could sell go in; months and a six-month target come out.", "आमदनी रुके तो आपका पैसा कितने महीने चलेगा? नक़द, ख़र्च, जो आमदनी जारी रहे और जो निवेश बेच सकते हैं, ये डालिए; महीने और छह महीने का लक्ष्य मिलेगा।"),
          (["Enter cash savings and monthly spending.", "Add any income that would continue and investments you could sell.", "Read the months and whether you meet the six-month target."], ["नक़द बचत और मासिक ख़र्च डालिए।", "जो आमदनी जारी रहे और जो निवेश बेच सकें, जोड़िए।", "महीने और छह महीने का लक्ष्य पूरा हुआ या नहीं, पढ़िए।"]),
          ("How does the emergency meter work?", "इमरजेंसी मीटर कैसे काम करता है?"),
          [S("/practice?tool=emergency", ".deck-stage", "Months of safety", "सुरक्षा के महीने", "The gauge shows how many months you can go on, marked against a six-month target. Change any slider and it re-calculates at once.", "गेज दिखाता है कि आप कितने महीने चल सकते हैं, छह महीने के लक्ष्य के सामने। कोई भी स्लाइडर बदलिए, तुरंत नया हिसाब आ जाता है।")]),

    _tour("digest", "/practice?tool=digest", ("Weekly voice digest", "साप्ताहिक आवाज़ सार"),
          r"\b(weekly digest (tool|feature)|voice digest|digest feature|how does the digest)\b",
          ("A one-minute spoken summary of your portfolio. Every figure is read from your data, with a safety tip at the end.", "आपके पोर्टफ़ोलियो का एक मिनट का बोला हुआ सार। हर आँकड़ा आपके डेटा से पढ़ा जाता है, अंत में एक सुरक्षा सुझाव के साथ।"),
          (["Press Play briefing.", "Read along with the text while it speaks.", "Press Stop any time."], ["'ब्रीफ़िंग चलाइए' दबाइए।", "बोलते समय लिखे को साथ पढ़िए।", "कभी भी 'रोकिए' दबाइए।"]),
          ("How does the weekly digest work?", "साप्ताहिक सार कैसे काम करता है?"),
          [S("/practice?tool=digest", ".deck-stage", "Press play", "चलाइए", "It covers how the portfolio moved, the best and worst holding, your risk score and one safety tip, in about forty seconds.", "यह बताता है कि पोर्टफ़ोलियो कैसे चला, सबसे अच्छा और सबसे बुरा शेयर, आपका जोखिम अंक और एक सुरक्षा सुझाव, लगभग चालीस सेकंड में।")]),

    _tour("rehearsal", "/practice?tool=rehearsal", ("Scam-call rehearsal", "ठग कॉल का अभ्यास"),
          r"\b(scam[- ]call (rehearsal|practice|simulat\w+)|rehearse (a )?(scam )?call|practi[sc]e (a )?scam)\b",
          ("Practise saying no before it is real. A caller pressures you with the exact tactics scammers use. Nothing is real and no data leaves your machine.", "असली होने से पहले मना करने का अभ्यास कीजिए। कॉलर वही चालें चलता है जो ठग चलते हैं। कुछ भी असली नहीं और कोई डेटा आपकी मशीन से बाहर नहीं जाता।"),
          (["Choose a scenario: bank KYC, digital arrest or a WhatsApp investment tip.", "Answer each turn; the coach shows the tactic and the safe reply."], ["एक स्थिति चुनिए: बैंक KYC, डिजिटल अरेस्ट या व्हाट्सऐप निवेश टिप।", "हर बारी जवाब दीजिए; कोच चाल और सुरक्षित जवाब दिखाता है।"]),
          ("How does the scam-call rehearsal work?", "ठग कॉल का अभ्यास कैसे काम करता है?"),
          [S("/practice?tool=rehearsal", ".deck-stage", "Choose a call", "कॉल चुनिए", "Each scenario shows the most that could be lost and how many turns it takes. Receive the call, answer, and see the tactic name at each turn.", "हर स्थिति दिखाती है कि अधिकतम कितना खोया जा सकता है और कितनी बारियाँ लगेंगी। कॉल लीजिए, जवाब दीजिए और हर बारी चाल का नाम देखिए।")]),

    # ------------------------------------------------------------------ govern + tools
    _tour("govern", "/govern", ("Govern", "नियम"),
          r"\b(govern(ance)? (page|section|area)|the govern|risk firewall|firewall|my limits|limits page)\b",
          ("Rules no AI can override. Your limits per stock, per industry and for cash are held by a firewall; you can check a trade against them, simulate a fix, and read an audit record that cannot be quietly edited.", "ऐसे नियम जिन्हें कोई AI नहीं लाँघ सकता। प्रति शेयर, प्रति उद्योग और नक़द की आपकी सीमाओं को फ़ायरवॉल थामे रखता है; आप ट्रेड को उनसे जाँच सकते हैं, सुधार का अनुकरण कर सकते हैं और ऐसा ऑडिट रिकॉर्ड पढ़ सकते हैं जिसे चुपके से नहीं बदला जा सकता।"),
          (["Read the three limit meters at the top.", "Use 'Check a trade' to test a purchase against them.", "Use 'Rebalance' to build the smallest fix.", "'Audit record' lists every decision; 'Tamper test' proves the record catches edits."], ["ऊपर के तीन सीमा-मीटर पढ़िए।", "ख़रीद को उनसे परखने के लिए 'ट्रेड जाँचिए' इस्तेमाल कीजिए।", "सबसे छोटा सुधार बनाने के लिए 'पुनर्संतुलन' इस्तेमाल कीजिए।", "'ऑडिट रिकॉर्ड' हर फ़ैसला दिखाता है; 'छेड़छाड़ परीक्षण' साबित करता है कि रिकॉर्ड बदलाव पकड़ता है।"]),
          ("Walk me through the Govern page", "नियम पेज घुमाइए"),
          [S("/govern", '.gov-hero', "Your limits, right now", "आपकी सीमाएँ, अभी", "Three meters: the largest single stock, the largest industry and the cash you keep. Each shows where you are against your own limit and how many points of room remain, or by how many you are over.", "तीन मीटर: सबसे बड़ा शेयर, सबसे बड़ा उद्योग और रखा हुआ नक़द। हर एक दिखाता है कि आप अपनी सीमा के मुक़ाबले कहाँ हैं और कितने अंक की गुंजाइश है, या कितने अंक ऊपर हैं।"),
           S("/govern", ".seg", "Four tools", "चार औज़ार", "Check a trade, rebalance, audit record and tamper test. Choose one and it opens below.", "ट्रेड जाँचिए, पुनर्संतुलन, ऑडिट रिकॉर्ड और छेड़छाड़ परीक्षण। एक चुनिए और वह नीचे खुलता है।"),
           S("/govern", ".seg + .seg-help ~ .grid", "The chosen tool", "चुना हुआ औज़ार", "Try them in order: check a trade that would break a limit, ask for the smallest fix, then see the record of what happened.", "क्रम से आज़माइए: ऐसा ट्रेड जाँचिए जो सीमा तोड़े, सबसे छोटा सुधार माँगिए, फिर देखिए क्या हुआ उसका रिकॉर्ड।")]),

    _tour("trade_check", "/govern", ("Check a trade", "ट्रेड जाँचिए"),
          r"\b(check a trade|trade check|risk firewall check|firewall check|test a (purchase|trade|buy))\b",
          ("Type a company and a size and the firewall tells you if the trade stays inside your limits, and if not, the largest size that does.", "कंपनी और मात्रा लिखिए और फ़ायरवॉल बताता है कि ट्रेड आपकी सीमाओं में रहता है या नहीं, और न रहे तो सबसे बड़ी मात्रा कितनी चलेगी।"),
          (["Choose the company and number of shares.", "Press Check.", "Read the verdict and which limit is the tightest."], ["कंपनी और शेयरों की संख्या चुनिए।", "'जाँचिए' दबाइए।", "निष्कर्ष और सबसे कसी सीमा पढ़िए।"]),
          ("How do I check a trade?", "ट्रेड कैसे जाँचूँ?"),
          [S("/govern", ".seg button:nth-child(1)", "Check a trade", "ट्रेड जाँचिए", "Open this tab, name a company and a size, and press Check. If it breaks a limit you see which one and the largest size that would fit.", "यह टैब खोलिए, कंपनी और मात्रा लिखिए और 'जाँचिए' दबाइए। सीमा टूटे तो दिखता है कौन सी और कितनी मात्रा चल सकती है।", click=".seg button:nth-child(1)")]),

    _tour("rebalance", "/govern", ("Rebalance simulator", "पुनर्संतुलन अनुकरण"),
          r"\b(rebalanc\w*|smallest fix|fix my (portfolio|limits)|bring me back within)\b",
          ("Builds the smallest set of trades that brings you back within your limits, and shows the result before anything happens.", "सबसे छोटे ट्रेड का समूह बनाता है जो आपको सीमाओं में वापस लाए, और कुछ होने से पहले नतीजा दिखाता है।"),
          (["Open Rebalance.", "Press 'Build the smallest fix', or choose 'Only sell, don't buy'.", "Read the trades and the before-and-after limits."], ["'पुनर्संतुलन' खोलिए।", "'सबसे छोटा सुधार बनाइए' दबाइए, या 'सिर्फ़ बेचिए, ख़रीदिए नहीं' चुनिए।", "ट्रेड और पहले-बाद की सीमाएँ पढ़िए।"]),
          ("How does the rebalance simulator work?", "पुनर्संतुलन अनुकरण कैसे काम करता है?"),
          [S("/govern", ".seg button:nth-child(2)", "Rebalance", "पुनर्संतुलन", "Choose Rebalance and the simulator proposes the smallest trades that fix an over-limit industry, with the limits before and after. Nothing is executed until you approve.", "'पुनर्संतुलन' चुनिए और अनुकरण सीमा से ऊपर वाले उद्योग को ठीक करने वाले सबसे छोटे ट्रेड सुझाता है, पहले और बाद की सीमाओं के साथ। आपकी मंज़ूरी तक कुछ नहीं होता।", click=".seg button:nth-child(2)")]),

    _tour("audit", "/govern", ("Audit record", "ऑडिट रिकॉर्ड"),
          r"\b(audit (record|trail|log)|decision record|ledger|hash chain|tamper[- ]evident)\b",
          ("Every decision, approved or blocked, is written to a record where each entry is chained to the one before it, so a quiet edit breaks the chain and is caught.", "हर फ़ैसला, मंज़ूर या रोका गया, एक ऐसे रिकॉर्ड में लिखा जाता है जहाँ हर प्रविष्टि पिछली से जुड़ी होती है, इसलिए चुपके से बदलाव करने पर कड़ी टूटती है और पकड़ में आती है।"),
          (["Open Audit record.", "Read each decision with its time and reason.", "Check that the chain is intact."], ["'ऑडिट रिकॉर्ड' खोलिए।", "हर फ़ैसला उसके समय और कारण के साथ पढ़िए।", "जाँचिए कि कड़ी अटूट है।"]),
          ("Explain the audit record", "ऑडिट रिकॉर्ड समझाइए"),
          [S("/govern", ".seg button:nth-child(3)", "The audit record", "ऑडिट रिकॉर्ड", "Each row is one decision: what was asked, whether it was allowed, and why. Each row also carries a fingerprint of the one before, so nobody can change history without it showing.", "हर पंक्ति एक फ़ैसला है: क्या माँगा गया, अनुमति मिली या नहीं और क्यों। हर पंक्ति पिछली का फ़िंगरप्रिंट भी रखती है, इसलिए इतिहास बदलने पर पता चल जाता है।", click=".seg button:nth-child(3)")]),

    _tour("tamper", "/govern", ("Tamper test", "छेड़छाड़ परीक्षण"),
          r"\b(tamper test|tamper with|break the (chain|record)|edit the record)\b",
          ("A live proof: it edits one past entry on a copy and shows the record detecting it.", "एक सीधा सबूत: यह एक प्रति में पुरानी प्रविष्टि बदलता है और दिखाता है कि रिकॉर्ड उसे पकड़ लेता है।"),
          (["Open Tamper test.", "Press 'Tamper with a past entry'.", "Watch the chain report exactly where it broke."], ["'छेड़छाड़ परीक्षण' खोलिए।", "'पुरानी प्रविष्टि बदलिए' दबाइए।", "देखिए कड़ी ठीक कहाँ टूटी यह कैसे बताती है।"]),
          ("Show me the tamper test", "छेड़छाड़ परीक्षण दिखाइए"),
          [S("/govern", ".seg button:nth-child(4)", "Tamper test", "छेड़छाड़ परीक्षण", "Open it and press the button. It changes one old entry on a copy of the record and the check immediately points at the entry that no longer matches.", "इसे खोलकर बटन दबाइए। यह रिकॉर्ड की प्रति में एक पुरानी प्रविष्टि बदलता है और जाँच तुरंत उस प्रविष्टि की ओर इशारा करती है जो अब मेल नहीं खाती।", click=".seg button:nth-child(4)")]),

    # ------------------------------------------------------------------ rural, whatsapp, learn, settings
    _tour("rural", "/rural", ("Rural tools", "ग्रामीण औज़ार"),
          r"\b(rural|moneylender (tool|check|feature)|sahukar|village|offline pack|credit score tool|upi safety tool|government schemes? (tool|feature)|harvest planner|sell or hold tool)\b",
          ("Twelve everyday tools for people who borrow from moneylenders, wait for government payments or earn seasonally: each gives a plain answer with the working, in Hindi too, and all of it can run offline.", "उन लोगों के लिए बारह रोज़मर्रा के औज़ार जो साहूकार से उधार लेते हैं, सरकारी भुगतान का इंतज़ार करते हैं या मौसमी कमाई करते हैं: हर एक हिसाब के साथ सीधा जवाब देता है, हिंदी में भी, और सब कुछ ऑफ़लाइन चल सकता है।"),
          (["Pick a tool from the row.", "Fill the few boxes it asks for, or say them aloud.", "Read the answer, then press Read aloud to hear it in Hindi.", "Download the offline pack to use it with no network."], ["पंक्ति से एक औज़ार चुनिए।", "जो कुछ ख़ाने पूछे जाएँ भरिए, या बोलकर बताइए।", "जवाब पढ़िए, फिर हिंदी में सुनने के लिए 'सुनें' दबाइए।", "बिना नेटवर्क के चलाने के लिए ऑफ़लाइन पैक डाउनलोड कीजिए।"]),
          ("Explain the rural tools", "ग्रामीण औज़ार समझाइए"),
          [S("/rural", '.rural-groups', "Twelve tools in a row", "एक पंक्ति में बारह औज़ार", "Moneylender check, credit score, is this offer real, UPI safety, is my policy good, my schemes, are my papers ready, why no money, plan my year, sell or hold, daily saving and the group ledger.", "साहूकार जाँच, क्रेडिट स्कोर, क्या यह ऑफ़र असली है, UPI सुरक्षा, क्या मेरी पॉलिसी अच्छी है, मेरी योजनाएँ, क्या मेरे काग़ज़ तैयार हैं, पैसा क्यों नहीं आया, साल की योजना, बेचूँ या रुकूँ, रोज़ की बचत और समूह का बही-खाता।"),
           S("/rural", '.rural-groups ~ .grid', "Fill a few boxes", "कुछ ख़ाने भरिए", "The moneylender check, for example, turns 'rupees per hundred per month' into the real yearly interest, which is usually far higher than it sounds.", "जैसे साहूकार जाँच 'सैकड़े पर महीने के रुपये' को असली सालाना ब्याज में बदल देती है, जो आम तौर पर सुनने से कहीं ज़्यादा होता है।"),
           S("/rural", '.offline-bar', "Works with no network", "बिना नेटवर्क भी चलता है", "The offline pack stores the app and the calculators on the device, so a village with no signal can still use every tool.", "ऑफ़लाइन पैक ऐप और कैलकुलेटर को उपकरण में रख लेता है, इसलिए बिना सिग्नल वाला गाँव भी हर औज़ार इस्तेमाल कर सकता है।")]),

    _tour("whatsapp", "/whatsapp", ("WhatsApp and SMS", "व्हाट्सऐप और SMS"),
          r"\b(whatsapp|sms|text message|feature phone|messaging)\b",
          ("The same tools as a phone chat: a numbered menu, one question at a time, voice notes and Hindi. It is the exact conversation a real WhatsApp or SMS number would have, ready to connect to Twilio.", "वही औज़ार फ़ोन चैट के रूप में: क्रमांकित मेनू, एक-एक सवाल, वॉइस नोट और हिंदी। यह ठीक वही बातचीत है जो असली व्हाट्सऐप या SMS नंबर पर होती, और Twilio से जोड़ने को तैयार।"),
          (["Send 'hi' to start.", "Reply with a number from the menu, or a full sentence.", "Press the mic to send a voice note; it is transcribed here and shown back as 'I heard'."], ["शुरू करने के लिए 'hi' भेजिए।", "मेनू से कोई संख्या, या पूरा वाक्य भेजिए।", "वॉइस नोट के लिए माइक दबाइए; वह यहीं लिखा जाता है और 'मैंने सुना' के रूप में लौटता है।"]),
          ("How does the WhatsApp feature work?", "व्हाट्सऐप फ़ीचर कैसे काम करता है?"),
          [S("/whatsapp", '.wa-phone', "A phone chat", "फ़ोन चैट", "This is the conversation as it would look on a phone. Type hi, or tap a number under the reply. Switch between WhatsApp and SMS, or to Hindi, at the top.", "फ़ोन पर यह बातचीत ऐसी दिखती। hi लिखिए, या जवाब के नीचे कोई संख्या दबाइए। ऊपर से व्हाट्सऐप और SMS या हिंदी बदलिए।"),
           S("/whatsapp", '.wa-side ul', "Things to try", "आज़माने की बातें", "A number, a full sentence, Hindi or a single money word all work. Tap one to send it.", "संख्या, पूरा वाक्य, हिंदी या कोई एक पैसे का शब्द, सब चलते हैं। भेजने के लिए एक दबाइए।"),
           S("/whatsapp", '.wa-menu', "What each number does", "हर संख्या क्या करती है", "Fourteen numbers map to the same tools as the Rural page, so a person with only a basic phone gets the same help.", "चौदह संख्याएँ ग्रामीण पेज के वही औज़ार खोलती हैं, इसलिए सादे फ़ोन वाले व्यक्ति को भी वही मदद मिलती है।")]),

    _tour("learn", "/learn", ("Learn", "सीखें"),
          r"\b(learn (page|section)|the learn|glossary|every number is a door|will i get there|goal (tool|fan|calculator)|sip (goal )?calculator)\b",
          ("A place to ask in plain words, see whether you will reach a goal as a range of outcomes, find where every number comes from, and look up any finance term.", "सरल शब्दों में पूछने, लक्ष्य तक पहुँचेंगे या नहीं यह नतीजों के दायरे के रूप में देखने, हर संख्या कहाँ से आई यह जानने और कोई भी वित्तीय शब्द देखने की जगह।"),
          (["Move the SIP, years and goal sliders and read the range.", "Use the 'returns are worse by' slider to test a poorer market.", "Ask in your own words in the box below.", "Open the glossary for any term."], ["SIP, साल और लक्ष्य के स्लाइडर खिसकाइए और दायरा पढ़िए।", "ख़राब बाज़ार परखने के लिए 'रिटर्न इतना कम' स्लाइडर इस्तेमाल कीजिए।", "नीचे के बॉक्स में अपने शब्दों में पूछिए।", "किसी भी शब्द के लिए शब्दकोश खोलिए।"]),
          ("Explain the Learn page", "सीखें पेज समझाइए"),
          [S("/learn", '[data-tour="learn-goal"]', "Will I get there?", "क्या मैं वहाँ पहुँचूँगा?", "Your holdings plus a monthly SIP, run through thousands of futures built from how this portfolio really behaved. You see a bad case, a typical case and a good case, and how many paths reach your goal. It is a range, not a forecast.", "आपके शेयर और मासिक SIP, इस पोर्टफ़ोलियो के असली बर्ताव से बने हज़ारों भविष्यों में चलाए गए। आपको ख़राब, सामान्य और अच्छा नतीजा दिखता है और कितने रास्ते लक्ष्य तक पहुँचते हैं। यह दायरा है, भविष्यवाणी नहीं।"),
           S("/learn", '[data-tour="learn-ask"]', "Ask in your own words", "अपने शब्दों में पूछिए", "Type any question about money here. The answers are the same structured cards as in the assistant.", "पैसे के बारे में कोई भी सवाल यहाँ लिखिए। जवाब वही संरचित कार्ड हैं जो सहायक में आते हैं।"),
           S("/learn", '[data-tour="learn-doors"]', "Every number is a door", "हर संख्या एक दरवाज़ा है", "Click any underlined figure anywhere in the app to see what it is made of: the formula and the exact prices and dates behind it.", "ऐप में कहीं भी किसी रेखांकित आँकड़े पर क्लिक कीजिए और देखिए वह किससे बना है: सूत्र और उसके पीछे के ठीक भाव और तारीख़ें।"),
           S("/learn", '[data-tour="learn-gloss"]', "Plain-English glossary", "सरल भाषा का शब्दकोश", "Thirty terms explained in everyday words, in English and Hindi.", "तीस शब्द रोज़मर्रा की भाषा में समझाए गए, अंग्रेज़ी और हिंदी में।")]),

    _tour("settings", "/", ("Language, theme and voice", "भाषा, थीम और आवाज़"),
          r"\b(language (switch|toggle)|switch language|hindi (mode|support)|theme|dark mode|light mode|dark theme|light theme|change (the )?voice|voice (picker|choice)|kiosk)\b",
          ("Three switches in the top bar: the language of answers (English or Hindi), a light or dark theme, and the voice that reads answers aloud.", "ऊपर की पट्टी में तीन स्विच: जवाबों की भाषा (अंग्रेज़ी या हिंदी), हल्की या गहरी थीम और जवाब सुनाने वाली आवाज़।"),
          (["Press EN or हिन्दी to change the language of every answer and caption.", "Press the sun or moon to switch theme.", "Pick a voice from the list; the Stop button is always there while it speaks."], ["हर जवाब और कैप्शन की भाषा बदलने के लिए EN या हिन्दी दबाइए।", "थीम बदलने के लिए सूरज या चाँद दबाइए।", "सूची से आवाज़ चुनिए; बोलते समय रोकने का बटन हमेशा रहता है।"]),
          ("How do I change the language or theme?", "भाषा या थीम कैसे बदलूँ?"),
          [S("/", ".langsw", "Language and theme", "भाषा और थीम", "EN and हिन्दी change the language of every answer and this guide. The sun and moon switch between light and dark. The device button prepares the screen for a shared kiosk.", "EN और हिन्दी हर जवाब और इस गाइड की भाषा बदलते हैं। सूरज और चाँद हल्की और गहरी थीम के बीच बदलते हैं। उपकरण वाला बटन साझा कियोस्क के लिए स्क्रीन तैयार करता है।"),
           S("/", ".voicesel", "Choose a voice", "आवाज़ चुनिए", "Pick the voice that reads answers aloud. The list changes with the language. Stop is always one tap away.", "जवाब सुनाने वाली आवाज़ चुनिए। सूची भाषा के साथ बदलती है। रोकना हमेशा एक टैप दूर है।")]),
]

BY_ID = {t["id"]: t for t in TOURS}


def match(text: str) -> dict[str, Any] | None:
    """The tour a question is about. More specific tours are tried before the general ones, and the more of the
    pattern a question hits (distinct words matched) the better the fit."""
    best, score = None, 0
    for t in TOURS:
        hits = t["rx"].findall(text)
        if not hits:
            continue
        s = sum(len(h if isinstance(h, str) else " ".join(h)) for h in hits) + (3 if t["id"] not in ("overview", "assistant") else 0)
        if s > score:
            best, score = t, s
    return best


def public(t: dict[str, Any], lang: str) -> dict[str, Any]:
    """What the player needs: steps in one language, no regex."""
    L = "hi" if lang == "hi" else "en"
    return {"id": t["id"], "title": t["title"][L], "route": t["route"],
            "steps": [{"route": s["route"], "sel": s["sel"], "click": s["click"], "title": s["title"][L], "body": s["body"][L]} for s in t["steps"]]}


def catalogue(lang: str) -> list[dict[str, Any]]:
    L = "hi" if lang == "hi" else "en"
    return [{"id": t["id"], "title": t["title"][L], "blurb": t["what"][L].split(". ")[0].rstrip("."), "steps": len(t["steps"]), "route": t["route"]} for t in TOURS]


from backend import tours_parts  # noqa: E402,F401  (richer step lists for the single-tool tours)
