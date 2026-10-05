"""Diagrams for the product brief (docx_assets/brief/*.png). Run: python tools/brief_figures.py"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Wedge

OUT = Path(__file__).resolve().parent.parent / "docx_assets" / "brief"
OUT.mkdir(parents=True, exist_ok=True)
INK, GOLD, GRAPH, GREEN, CORAL, BLUE, PAPER, MUTE = "#1d1b16", "#d99a1e", "#2a2c31", "#2e9d73", "#d9564a", "#4a5fd0", "#fbf8f1", "#7a766b"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def canvas(w, h, name):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w * 10); ax.set_ylim(0, h * 10); ax.axis("off")
    fig.patch.set_facecolor("white")
    return fig, ax


def box(ax, x, y, w, h, text, fc=PAPER, ec=GOLD, tc=INK, fs=9, bold=False, r=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.2,rounding_size={r}", fc=fc, ec=ec, lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc, weight="bold" if bold else "normal", wrap=True, linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, c=MUTE, rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13, lw=1.5, color=c, connectionstyle=f"arc3,rad={rad}"))


def save(fig, name):
    fig.savefig(OUT / name, dpi=190, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# 1. who it serves: the 75 / 20 / 5 design weighting
def audience():
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    ax.axis("off"); ax.set_xlim(-1.2, 8.6); ax.set_ylim(-1.2, 1.25); ax.set_aspect("equal")
    parts = [(75, GOLD, "75%  Underprivileged and rural\nfarm and wage families, SHG women,\nfirst-time borrowers"), (20, BLUE, "20%  Retail and middle class\nsalaried, small investors, gig workers"), (5, GRAPH, "5%  Affluent\nactive investors, family offices")]
    a = 90
    for v, c, _ in parts:
        ax.add_patch(Wedge((0, 0), 1.0, a - v * 3.6, a, width=0.42, fc=c, ec="white", lw=2)); a -= v * 3.6
    ax.text(0, 0.05, "Who the\nplatform\nis built for", ha="center", va="center", fontsize=10, weight="bold", color=INK)
    for i, (v, c, t) in enumerate(parts):
        y = 0.85 - i * 0.78
        ax.add_patch(plt.Rectangle((1.35, y - 0.12), 0.26, 0.26, fc=c)); ax.text(1.75, y + 0.01, t, va="center", fontsize=9.3, color=INK, linespacing=1.35)
    ax.set_title("Design weighting: where most of the effort goes", fontsize=11, weight="bold", loc="left", color=INK)
    save(fig, "audience.png")


# 2. problems -> features
def problems():
    fig, ax = canvas(7.4, 4.6, "p")
    rows = [("Pays 5-10% a month to a moneylender\nwithout knowing the yearly cost", "Moneylender check, credit-score guide"),
            ("Loses savings to fake schemes,\nOTP and 'digital arrest' calls", "Scam scripts, rehearsal, recovery coach, UPI check"),
            ("Misses government money they\nare owed, or payment never arrives", "Schemes finder, papers checklist, payment tracer"),
            ("Income comes in lumps\n(harvest, daily wage)", "Plan-my-year, sell-or-hold, daily saving, SHG ledger"),
            ("Cannot read English or a long form;\nno data, shared phone", "WhatsApp/SMS, Hindi voice, offline pack, kiosk mode"),
            ("Invests without knowing fees, overlap,\ntax or risk; follows tips", "Portfolio X-ray, fee drag, overlap, tax shield, research desk"),
            ("Needs rules that cannot be argued with,\nand a record that cannot be edited", "Risk firewall, hash-chained audit record, attribution")]
    ax.text(0, 46, "Problem the person lives with", fontsize=10, weight="bold", color=INK); ax.text(46, 46, "What the platform gives them", fontsize=10, weight="bold", color=INK)
    for i, (p, f) in enumerate(rows):
        y = 38 - i * 6.1
        col = GOLD if i < 5 else (BLUE if i == 5 else GRAPH)
        box(ax, 0, y, 41, 5, p, ec=CORAL, fs=8.3); box(ax, 46, y, 27, 5, f, ec=col, fs=8.3)
        arrow(ax, 41.4, y + 2.5, 45.6, y + 2.5, GREEN)
    save(fig, "problems.png")


# 3. system architecture
def architecture():
    fig, ax = canvas(7.6, 5.2, "a")
    layers = [("PEOPLE", 44, [("Phone / WhatsApp\nSMS (Twilio-ready)", GOLD), ("Web app (React)\nHindi + English", GOLD), ("Kiosk / shared\ndevice, offline pack", GOLD)]),
              ("INTERFACE", 33, [("FastAPI + WebSocket", BLUE), ("Voice in:\nfaster-whisper (local)", BLUE), ("Voice out:\nPiper / Kokoro (local)", BLUE)]),
              ("BRAIN", 22, [("Understanding layer\n(rules, closed-list pick)", GREEN), ("Calculators\n(rural, fees, goals, tax)", GREEN), ("Hand-written answers\n(EN + HI, 32 topics)", GREEN)]),
              ("ENGINES", 11, [("Research desks\n+ citation gate", GRAPH), ("Risk firewall +\nhash-chained ledger", GRAPH), ("Charts, attribution,\nportfolio X-ray", GRAPH)]),
              ("DATA", 0, [("Point-in-time store\n(SQLite)", MUTE), ("Prices, statements,\nownership, news (free)", MUTE), ("Optional local model\n(Ollama) - picks only", MUTE)])]
    for name, y, items in layers:
        ax.text(0, y + 4.3, name, fontsize=8, weight="bold", color=MUTE, rotation=0)
        for i, (t, c) in enumerate(items):
            box(ax, 11 + i * 21.5, y, 20, 8.6, t, ec=c, fs=8)
    for y in (9.2, 20.2, 31.2, 42.2):
        for x in (21, 42.5, 64):
            arrow(ax, x, y + 2.1, x, y + 1.5 - 0.1 + 0.8, "#c9c4b6")
    save(fig, "architecture.png")


# 4. journey of one question
def journey():
    fig, ax = canvas(7.6, 4.0, "j")
    steps = [("1  Ask\ntyped or spoken\n(Hindi/English)", GOLD), ("2  Read the\nwhole sentence", BLUE), ("3  Choose the kind\nof request", BLUE), ("4  Tool or\nchecked answer", GREEN), ("5  Show: card, chart,\nsteps, tour", GREEN)]
    for i, (t, c) in enumerate(steps):
        box(ax, 1 + i * 15, 24, 13, 9, t, ec=c, fs=8)
        if i < 4:
            arrow(ax, 14.4 + i * 15, 28.5, 16 + i * 15, 28.5)
    kinds = [("App question\n-> guided tour", 3), ("Company\n-> facts + chart", 18), ("Money concept\n-> checked answer", 33), ("Your numbers\n-> calculator", 48), ("Scam / rural\n-> script or tool", 63)]
    ax.text(1, 18.5, "Step 3 branches into five kinds:", fontsize=8.5, weight="bold", color=INK)
    for t, x in kinds:
        box(ax, x, 6, 13.2, 9, t, ec=BLUE, fs=7.8); arrow(ax, 37, 23.6, x + 6.6, 15.4, "#c9c4b6", 0.0)
    ax.text(1, 1, "A local model, when used at all, only picks from a fixed list. It never writes an answer or a number.", fontsize=8.3, style="italic", color=CORAL)
    save(fig, "journey.png")


# 5. trust pipeline
def trust():
    fig, ax = canvas(7.4, 2.9, "t")
    items = [("Dated public data\n(prices, statements)", MUTE), ("Deterministic code\n(calculators, ratios)", GREEN), ("Hand-written EN/HI\ntemplates", GREEN), ("Confidence mark +\nage of data", GOLD), ("Answer shown\n'how it was worked out'", GOLD)]
    for i, (t, c) in enumerate(items):
        box(ax, 1 + i * 14.6, 12, 12.6, 9, t, ec=c, fs=7.8)
        if i < 4:
            arrow(ax, 13.9 + i * 14.6, 16.5, 15.5 + i * 14.6, 16.5)
    box(ax, 15, 1, 40, 6.5, "No step lets a language model invent a figure", ec=CORAL, fs=9, bold=True, tc=CORAL)
    save(fig, "trust.png")


# 6. feature x audience matrix
def matrix():
    feats = ["WhatsApp / SMS menu", "Hindi voice + text", "Offline pack, kiosk", "Moneylender cost", "Schemes, papers, payment tracer", "Scam scripts + recovery coach",
             "Harvest plan, daily saving, SHG ledger", "Guided tours", "Fee drag, overlap, emergency meter", "Portfolio X-ray + allocation map", "Research desk + plain summary",
             "Tax shield, panic replay", "Risk firewall + limits", "Hash-chained audit record", "Attribution, time machine, reports"]
    aud = ["Underprivileged\n(75%)", "Retail / middle\n(20%)", "Affluent\n(5%)"]
    w = [[3, 2, 1], [3, 2, 1], [3, 2, 1], [3, 1, 1], [3, 1, 0], [3, 3, 2], [3, 1, 0], [3, 3, 2], [1, 3, 2], [0, 3, 3], [0, 3, 3], [0, 3, 2], [0, 2, 3], [0, 1, 3], [0, 2, 3]]
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    cm = {0: "#f3efe4", 1: "#f5dca4", 2: "#e8b64f", 3: "#c27f0a"}
    for i, row in enumerate(w):
        for j, v in enumerate(row):
            ax.add_patch(plt.Rectangle((j, len(w) - i - 1), 0.96, 0.9, fc=cm[v], ec="white"))
            ax.text(j + 0.48, len(w) - i - 0.55, ["", "some", "good", "core"][v], ha="center", va="center", fontsize=7.5, color="white" if v == 3 else INK)
    ax.set_xlim(0, 3); ax.set_ylim(0, len(w)); ax.set_yticks([len(w) - i - 0.55 for i in range(len(w))]); ax.set_yticklabels(feats, fontsize=8.2)
    ax.set_xticks([0.48, 1.48, 2.48]); ax.set_xticklabels(aud, fontsize=8.5, weight="bold"); ax.xaxis.tick_top(); ax.tick_params(length=0)
    for s in ax.spines.values(): s.set_visible(False)
    save(fig, "matrix.png")


# 7. rural user journey over WhatsApp
def wa():
    fig, ax = canvas(7.4, 3.7, "w")
    msgs = [(1, 27, "me", "Sahukar 5 rupaye sainkda\nper mahina, 50,000 liye"), (30, 20, "bot", "Rs 5 per 100 a month = 60% a year.\nYou pay Rs 30,000 a year in interest."), (1, 11, "me", "Kya sarkari yojana milegi?"), (30, 2, "bot", "3 schemes you may qualify for.\nPapers to keep ready: 1 Aadhaar, 2 bank...")]
    for x, y, who, t in msgs:
        box(ax, x, y, 40 if who == "bot" else 28, 7.5, t, fc="#e5f6e7" if who == "bot" else "white", ec=GREEN if who == "bot" else MUTE, fs=7.8)
    ax.text(48, 24, "Same answer as the web app.\nHindi or English, text or voice note.\nNo app to install, works on a basic\nsmartphone; SMS for feature phones.", fontsize=8.5, va="center", color=INK, linespacing=1.5)
    save(fig, "whatsapp.png")


# 8. business flow
def business():
    fig, ax = canvas(7.6, 4.3, "b")
    box(ax, 30, 31, 16, 8, "THE PLATFORM\nfree, local, bilingual", fc="#fff4d8", ec=GOLD, fs=9, bold=True)
    left = [("Users: farmers, wage\nfamilies, SHG women", 2, 33), ("Retail investors,\nsalaried families", 2, 20), ("Affluent / advisers", 2, 7)]
    right = [("Banks, BCs, co-op banks,\nMFIs: fraud + outreach", 54, 33), ("NGOs, CSR, state missions:\nreach + measurement", 54, 20), ("Fintechs, advisers:\nlicence, white-label", 54, 7)]
    for t, x, y in left:
        box(ax, x, y, 20, 7.5, t, ec=BLUE, fs=8); arrow(ax, x + 20.4, y + 3.7, 29.6, 35 if y > 30 else 33, "#c9c4b6")
    for t, x, y in right:
        box(ax, x, y, 20, 7.5, t, ec=GREEN, fs=8); arrow(ax, 46.4, 35, x - 0.4, y + 3.7, GREEN)
    ax.text(0, 1.2, "Users pay little or nothing. Institutions that gain from fewer frauds, more inclusion and better reach pay.", fontsize=8.3, style="italic", color=MUTE)
    save(fig, "business.png")


# 9. roadmap
def roadmap():
    fig, ax = canvas(7.6, 3.4, "r")
    ph = [("NOW\nPrototype", "web + WhatsApp sim\nHindi, offline, 25 tours\n520 tests", GOLD), ("0-6 months\nPilot", "2-3 partners (NGO / SHG\nfederation / co-op bank)\nreal WhatsApp number", BLUE), ("6-18 months\nScale", "4-5 more languages\nvoice-first, USSD/IVR\nbank + CSC channels", GREEN), ("18-36 months\nPlatform", "API + white-label\nregional language models\nimpact dashboard", GRAPH)]
    ax.plot([4, 70], [22, 22], color="#c9c4b6", lw=3)
    for i, (t, d, c) in enumerate(ph):
        x = 4 + i * 20
        ax.scatter([x + 4], [22], s=190, color=c, zorder=3)
        ax.text(x + 4, 28, t, ha="center", fontsize=8.8, weight="bold", color=c, linespacing=1.3)
        ax.text(x + 4, 14, d, ha="center", va="center", fontsize=7.8, color=INK, linespacing=1.4)
    save(fig, "roadmap.png")


# 10. positioning
def position():
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    ax.axhline(5, color="#c9c4b6"); ax.axvline(5, color="#c9c4b6")
    pts = [("Trading / broker apps", 8.2, 2.2, MUTE), ("Robo-advisers", 7, 4, MUTE), ("Bank apps", 5.6, 3, MUTE), ("Finance YouTube /\nTelegram groups", 8.3, 5.9, CORAL), ("Govt. portals\n(scattered)", 2.4, 3.4, MUTE), ("Financial-literacy\nNGO content", 2.2, 7.6, MUTE), ("THIS PLATFORM", 2.6, 9.0, GOLD)]
    for t, x, y, c in pts:
        ax.scatter([x], [y], s=240 if "THIS" in t else 90, color=c, zorder=3); ax.text(x + 0.25, y, t, fontsize=8.2, va="center", weight="bold" if "THIS" in t else "normal", color=INK)
    ax.set_xlabel("Built for the investing elite  <-----  built for the masses", fontsize=8.5, loc="center")
    ax.set_xlabel("Serves wealthy, active investors  --->", fontsize=8.5); ax.set_ylabel("Passive content  --->  does the task for you, verified", fontsize=8.5)
    ax.set_xticks([]); ax.set_yticks([])
    ax.text(0.2, 0.3, "Poor reach, no action", fontsize=7.5, color=MUTE); ax.text(0.2, 5.3, "Reaches the masses, acts", fontsize=7.5, color=GOLD, weight="bold")
    save(fig, "position.png")


# 11. maturity
def maturity():
    fig, ax = plt.subplots(figsize=(7, 3.7))
    items = [("Rural tools (12) + WhatsApp sim", 90), ("Scam protection (scripts, coach, rehearsal)", 85), ("Assistant understanding + tours", 80), ("Research desk + plain summary", 75), ("Portfolio, Govern, audit record", 80), ("Voice in Hindi (local)", 65), ("Real WhatsApp / SMS delivery", 45), ("Live data feeds at scale", 40), ("More Indian languages", 20)]
    ys = list(range(len(items)))[::-1]
    for y, (n, v) in zip(ys, items):
        ax.barh(y, 100, color="#f3efe4", height=0.6); ax.barh(y, v, color=GREEN if v >= 75 else (GOLD if v >= 45 else CORAL), height=0.6)
        ax.text(101, y, f"{v}%", va="center", fontsize=8)
    ax.set_yticks(ys); ax.set_yticklabels([n for n, _ in items], fontsize=8.5); ax.set_xlim(0, 112); ax.set_xticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title("Prototype readiness (team's own estimate)", fontsize=10, weight="bold", loc="left")
    save(fig, "maturity.png")


# 12. illustrative unit economics
def economics():
    fig, ax = plt.subplots(figsize=(7, 3.4))
    seg = ["Underprivileged\nusers", "Retail users", "Affluent users"]
    rev = [0, 3, 40]; cost = [2, 4, 6]
    x = range(3)
    ax.bar([i - 0.18 for i in x], rev, 0.34, color=GOLD, label="Direct revenue / user / month (Rs)")
    ax.bar([i + 0.18 for i in x], cost, 0.34, color=GRAPH, label="Serving cost / user / month (Rs)")
    ax.set_xticks(list(x)); ax.set_xticklabels(seg, fontsize=9); ax.legend(fontsize=8, frameon=False)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.text(0, 9, "funded by institutions\n(banks, NGOs, CSR)", ha="center", fontsize=8, color=GREEN, weight="bold")
    ax.set_title("Illustrative only: the mass segment is funded by partners, the premium segment by users", fontsize=9, loc="left")
    save(fig, "economics.png")


# 13. tech stack
def stack():
    fig, ax = canvas(7.4, 3.3, "s")
    rows = [("Front end", "React, Vite, TypeScript, Zustand, SVG charts, React-Three-Fiber orb, service worker"), ("API", "FastAPI, WebSocket events, REST (/ask, /tours, /research/summary)"),
            ("Intelligence", "rule router, closed-list model pick (Ollama llama3.1:8b), scikit-learn text similarity"), ("Voice", "faster-whisper (speech to text), Piper / Kokoro (text to speech), Hindi + English"),
            ("Data", "SQLite point-in-time store, yfinance (free), Google News RSS, NSE list"), ("Offline", "Pyodide runs the Python calculators in the browser; cached app shell")]
    for i, (a, b) in enumerate(rows):
        y = 27 - i * 5
        box(ax, 0, y, 14, 4.2, a, fc=GRAPH, ec=GRAPH, tc="white", fs=8.5, bold=True); box(ax, 15, y, 58, 4.2, b, fs=7.8, ec="#e4dcc6")
    save(fig, "stack.png")


# 14. point-in-time
def pit():
    fig, ax = canvas(7.4, 2.6, "pit")
    ax.plot([3, 70], [14, 14], color="#c9c4b6", lw=3)
    for x, t, c in [(10, "Report published", GREEN), (30, "Clock set here\n(time machine)", GOLD), (52, "News after the clock", CORAL)]:
        ax.scatter([x], [14], s=150, color=c, zorder=3); ax.text(x, 19, t, ha="center", fontsize=8.2, color=c, weight="bold")
    ax.add_patch(plt.Rectangle((30, 9), 40, 3, fc="#f4d6d2", ec=CORAL)); ax.text(50, 10.5, "hidden from the analysts", ha="center", fontsize=8, color=CORAL)
    ax.add_patch(plt.Rectangle((3, 9), 27, 3, fc="#d9efe4", ec=GREEN)); ax.text(16, 10.5, "visible", ha="center", fontsize=8, color=GREEN)
    save(fig, "pit.png")


for f in (audience, problems, architecture, journey, trust, matrix, wa, business, roadmap, position, maturity, economics, stack, pit):
    f()
print("figures:", sorted(p.name for p in OUT.glob("*.png")))
