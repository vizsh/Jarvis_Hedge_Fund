"""Prototype setup: which features a given audience gets, and what each costs.

The prototype is one codebase with ten features. A setup picks a starting basket (a persona) and lets the person add or remove
features. Every feature keeps working in every basket; the basket only decides what appears in the menu by default.

Pricing is a DUMMY checkout for the pitch: nothing is charged. Rural and self-help features are free by design.
"""
from __future__ import annotations

from typing import Any

FEATURES: list[dict[str, Any]] = [
    {"id": "assistant", "group": "reach", "route": "/assistant", "tier": "free", "price": 0, "en": "Assistant", "hi": "सहायक",
     "blurb": "Ask in words or voice; answers with figures, charts and tours.", "blurb_hi": "बोलकर या लिखकर पूछिए; आँकड़े और चार्ट के साथ जवाब।"},
    {"id": "rural", "group": "credit", "route": "/rural", "tier": "free", "price": 0, "en": "Rural tools", "hi": "ग्रामीण औज़ार",
     "blurb": "Moneylender cost, schemes, papers, harvest plan, group ledger.", "blurb_hi": "साहूकार का ब्याज, योजनाएँ, काग़ज़, फ़सल योजना, समूह बही।"},
    {"id": "whatsapp", "group": "reach", "route": "/whatsapp", "tier": "free", "price": 0, "en": "WhatsApp & SMS", "hi": "व्हाट्सऐप और SMS",
     "blurb": "The same tools on a basic phone, Hindi voice notes included.", "blurb_hi": "सादे फ़ोन पर वही औज़ार, हिंदी वॉइस नोट के साथ।"},
    {"id": "protect", "group": "fraud", "route": "/protect", "tier": "free", "price": 0, "en": "Scam protection", "hi": "ठगी से सुरक्षा",
     "blurb": "Scam scripts, tip checker, recovery coach, tax shield.", "blurb_hi": "ठगी के तरीक़े, टिप जाँच, रिकवरी कोच, टैक्स बचत।"},
    {"id": "learn", "group": "reach", "route": "/learn", "tier": "free", "price": 0, "en": "Learn", "hi": "सीखें",
     "blurb": "Plain-English explanations, goal range, glossary.", "blurb_hi": "सरल भाषा में समझ, लक्ष्य का दायरा, शब्दकोश।"},
    {"id": "portfolio", "group": "invest", "route": "/portfolio", "tier": "paid", "price": 199, "en": "Portfolio X-ray", "hi": "पोर्टफ़ोलियो एक्स-रे",
     "blurb": "Health grade, spread, allocation map and what-to-do list.", "blurb_hi": "सेहत ग्रेड, फैलाव, आवंटन और क्या करें सूची।"},
    {"id": "research", "group": "invest", "route": "/research", "tier": "paid", "price": 299, "en": "Research desk", "hi": "शोध डेस्क",
     "blurb": "Company research: plain summary, analysts, charts, comparisons.", "blurb_hi": "कंपनी शोध: सरल सार, विश्लेषक, चार्ट, तुलना।"},
    {"id": "practice", "group": "invest", "route": "/practice", "tier": "paid", "price": 99, "en": "Practice tools", "hi": "अभ्यास औज़ार",
     "blurb": "Fee drag, fund overlap, emergency meter, weekly digest.", "blurb_hi": "फ़ीस का असर, फ़ंड ओवरलैप, इमरजेंसी मीटर, साप्ताहिक सार।"},
    {"id": "govern", "group": "reach", "route": "/govern", "tier": "paid", "price": 499, "en": "Govern & audit", "hi": "नियम और ऑडिट",
     "blurb": "Risk firewall, limits, rebalance, tamper-evident audit record.", "blurb_hi": "जोखिम की दीवार, सीमाएँ, संतुलन, छेड़छाड़-रोधी रिकॉर्ड।"},
]
# Loss channel each feature addresses (docs/CONTEXT.md section 4): fraud, credit, invest, reach.
GROUPS = ["fraud", "credit", "invest", "reach"]

HOME = {"id": "home", "group": "reach", "route": "/", "tier": "free", "price": 0, "en": "Home", "hi": "होम"}

ALL_IDS = [f["id"] for f in FEATURES]
PAID_IDS = [f["id"] for f in FEATURES if f["tier"] == "paid"]

PERSONAS: list[dict[str, Any]] = [
    {"id": "pitch", "en": "Full prototype (for pitching)", "hi": "पूरा प्रोटोटाइप (पिच के लिए)",
     "who": "Everything in one place, to show every feature to a funder or partner. Nothing is charged in this demo.",
     "who_hi": "फ़ंडर या साझेदार को हर फ़ीचर दिखाने के लिए, सब एक जगह। इस डेमो में कोई शुल्क नहीं।",
     "features": ALL_IDS},
    {"id": "banks", "en": "Banks & co-operative banks", "hi": "बैंक और सहकारी बैंक",
     "who": "Fraud-loss reduction for customers, credit-cost explanations, WhatsApp outreach, and compliance limits with an audit record.",
     "who_hi": "ग्राहकों की ठगी घटाना, क़र्ज़ की लागत समझाना, व्हाट्सऐप से पहुँच, और ऑडिट वाले नियम।",
     "features": ["assistant", "rural", "whatsapp", "protect", "learn", "govern"]},
    {"id": "farmers", "en": "Farmers & rural families", "hi": "किसान और ग्रामीण परिवार",
     "who": "Moneylender cost, schemes, papers, harvest planning, scam protection, on a basic phone or WhatsApp. Free.",
     "who_hi": "साहूकार का ब्याज, योजनाएँ, काग़ज़, फ़सल योजना, ठगी से सुरक्षा, सादे फ़ोन या व्हाट्सऐप पर। मुफ़्त।",
     "features": ["assistant", "rural", "whatsapp", "protect", "learn"]},
    {"id": "shg", "en": "Self-help groups & NGOs", "hi": "स्वयं सहायता समूह और NGO",
     "who": "Group ledger and meeting reports, daily saving plans, scam awareness, shared-device use. Free.",
     "who_hi": "समूह बही और बैठक रिपोर्ट, रोज़ की बचत योजना, ठगी की जागरूकता, साझा फ़ोन। मुफ़्त।",
     "features": ["assistant", "rural", "whatsapp", "protect", "learn"]},
    {"id": "retail", "en": "Middle-class retail investors", "hi": "मध्यम वर्गीय खुदरा निवेशक",
     "who": "Portfolio health, fund overlap and fees, company research, tax timing and the tip checker.",
     "who_hi": "पोर्टफ़ोलियो की सेहत, फ़ंड ओवरलैप और फ़ीस, कंपनी शोध, टैक्स का समय और टिप जाँच।",
     "features": ["assistant", "portfolio", "research", "practice", "protect", "learn"]},
]
for p in PERSONAS:
    p["price"] = sum(f["price"] for f in FEATURES if f["id"] in p["features"] and f["tier"] == "paid") if p["id"] != "pitch" else 0


def _ensure(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS app_setup (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()


def current(conn) -> dict[str, Any]:
    """The saved setup, or not-done. Home is always on."""
    import json
    _ensure(conn)
    row = conn.execute("SELECT value FROM app_setup WHERE key='setup'").fetchone()
    if not row:
        return {"done": False, "persona": None, "features": ["home", *ALL_IDS]}
    d = json.loads(row[0])
    return {"done": True, "persona": d.get("persona"), "features": ["home", *[f for f in ALL_IDS if f in d.get("features", [])]]}


def save(conn, persona: str | None, features: list[str]) -> dict[str, Any]:
    import json
    _ensure(conn)
    chosen = [f for f in ALL_IDS if f in set(features)]
    conn.execute("INSERT OR REPLACE INTO app_setup(key, value) VALUES('setup', ?)",
                 (json.dumps({"persona": persona, "features": chosen}),))
    conn.commit()
    return current(conn)


def price_of(features: list[str]) -> int:
    return sum(f["price"] for f in FEATURES if f["id"] in features and f["tier"] == "paid")


def catalogue() -> dict[str, Any]:
    return {"features": [HOME, *FEATURES], "personas": PERSONAS, "all": ALL_IDS}
