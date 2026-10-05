"""Diagrams for the v2 product brief (docx_assets/brief_v2/*.png). Run: python -m tools.brief_v2_figures

Every label is fitted to its box: the font shrinks, then the text wraps, until it fits. That is what removes the overlaps
the first version had. Coordinates run 0-100 on both axes for every figure."""
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent.parent / "docx_assets" / "brief_v2"
OUT.mkdir(parents=True, exist_ok=True)
INK, GOLD, GRAPH, GREEN, CORAL, BLUE, PAPER, MUTE, LINE = "#1d1b16", "#c98a12", "#2a2c31", "#1f7a4a", "#c4453a", "#3f57c4", "#fbf8f1", "#7a766b", "#c9c4b6"
plt.rcParams.update({"font.family": "DejaVu Sans"})


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.fig, self.ax = plt.subplots(figsize=(w, h))
        self.ax.set_xlim(0, 100); self.ax.set_ylim(0, 100); self.ax.axis("off")
        self.fig.patch.set_facecolor("white")
        self.pt_x = w * 72 / 100       # points per unit, horizontal
        self.pt_y = h * 72 / 100

    def fit(self, text, w, h, base=9.0, min_fs=6.2, pad=1.2):
        """(font size, wrapped text) such that the text fits a w x h unit box."""
        wpt, hpt = (w - 2 * pad) * self.pt_x, (h - 2 * pad) * self.pt_y
        fs = base
        while fs >= min_fs:
            cpl = max(4, int(wpt / (0.66 * fs)))
            lines = []
            for para in text.split("\n"):
                lines += textwrap.wrap(para, cpl) or [""]
            if len(lines) * fs * 1.28 <= hpt:
                return fs, "\n".join(lines)
            fs -= 0.4
        cpl = max(4, int(wpt / (0.66 * min_fs)))
        lines = []
        for para in text.split("\n"):
            lines += textwrap.wrap(para, cpl) or [""]
        return min_fs, "\n".join(lines[: max(1, int(hpt / (min_fs * 1.28)))])

    def box(self, x, y, w, h, text, fc=PAPER, ec=GOLD, tc=INK, base=9.0, bold=False, lw=1.3):
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2", fc=fc, ec=ec, lw=lw, zorder=3))
        fs, t = self.fit(text, w, h, base)
        self.ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=fs, color=tc, weight="bold" if bold else "normal", linespacing=1.28, zorder=4)

    def label(self, x, y, text, base=9.5, color=INK, bold=True, ha="left", va="center", w=90, h=4):
        fs, t = self.fit(text, w, h, base)
        self.ax.text(x, y, t, fontsize=fs, color=color, weight="bold" if bold else "normal", ha=ha, va=va, linespacing=1.28)

    def arrow(self, x1, y1, x2, y2, c=MUTE, rad=0.0):
        self.ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=11, lw=1.3, color=c, connectionstyle=f"arc3,rad={rad}", zorder=1))

    def save(self, name):
        self.fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white", pad_inches=0.08)
        plt.close(self.fig)


def problems():
    c = Canvas(6.6, 4.4)
    c.label(1, 98, "The problem people live with", color=INK, w=44, h=3); c.label(56, 98, "What the platform gives them", color=INK, w=44, h=3)
    rows = [("Moneylender quotes '5 per 100 a month';\nnobody converts it", "Moneylender check: 60% a year, rupees paid"),
            ("Fake KYC, 'digital arrest' and tip-group scams", "Scam scripts, rehearsal, recovery coach"),
            ("Government payment or subsidy never arrives", "Schemes finder, papers checklist, payment tracer"),
            ("Income comes in lumps (harvest, daily wage)", "Plan my year, sell or hold, daily saving"),
            ("Records kept on paper; group accounts unclear", "Group ledger and meeting report, offline"),
            ("Investors pay hidden fees and buy duplicate funds", "Fee drag, fund overlap, tax shield, research")]
    for i, (p, s) in enumerate(rows):
        y = 80 - i * 14
        c.box(1, y, 41, 11, p, ec=CORAL, base=8.6)
        c.box(56, y, 43, 11, s, ec=GREEN, base=8.6)
        c.arrow(42.6, y + 5.5, 55.4, y + 5.5, GREEN)
    c.save("problems.png")


def setup_flow():
    c = Canvas(6.6, 2.5)
    steps = [("1  Who is it for?", "Pick one of five baskets", GOLD), ("2  Switch features", "On or off, from one list", GOLD), ("3  Live menu", "Your menu and demo price update", BLUE), ("4  Start", "Saved once per install", GREEN)]
    for i, (t, s, col) in enumerate(steps):
        x = 1 + i * 25.3
        c.box(x, 36, 22.5, 36, t + "\n" + s, ec=col, base=8.6)
        if i < 3:
            c.arrow(x + 22.8, 54, x + 25.0, 54, MUTE)
    c.label(1, 15, "A feature not in the chosen basket opens a locked page: add it in one tap.", base=8.5, bold=False, w=98, color=MUTE)
    c.save("setup_flow.png")


def basket_matrix():
    feats = ["Assistant", "Rural tools", "WhatsApp & SMS", "Scam protection", "Learn", "Portfolio X-ray", "Research desk", "Practice tools", "Govern & audit"]
    bask = ["Full prototype\n(pitch)", "Banks and\nco-op banks", "Farmers and\nrural families", "Self-help groups\nand NGOs", "Middle-class\ninvestors"]
    has = [[1] * 9,
           [1, 1, 1, 1, 1, 0, 0, 0, 1],
           [1, 1, 1, 1, 1, 0, 0, 0, 0],
           [1, 1, 1, 1, 1, 0, 0, 0, 0],
           [1, 0, 0, 1, 1, 1, 1, 1, 0]]
    price = ["Free (demo)", "₹499 / mo", "Free", "Free", "₹597 / mo"]
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    ax.set_xlim(-0.2, 6.9); ax.set_ylim(-1.7, len(feats) + 1.0); ax.axis("off")
    for j, b in enumerate(bask):
        ax.text(j + 0.5, len(feats) + 0.05, b, ha="center", va="bottom", fontsize=6.4, weight="bold", color=INK, linespacing=1.1)
    for i, f in enumerate(feats):
        y = len(feats) - i - 0.5
        ax.text(-0.15, y, f, ha="right", va="center", fontsize=7.4, color=INK)
        for j in range(len(bask)):
            on = has[j][i]
            ax.add_patch(plt.Rectangle((j + 0.06, y - 0.36), 0.88, 0.72, fc=("#d7eadf" if on else "#f3efe6"), ec="white"))
            ax.text(j + 0.5, y, "✓" if on else "–", ha="center", va="center", fontsize=8, color=GREEN if on else "#b9b3a4", weight="bold")
    for j, p in enumerate(price):
        ax.text(j + 0.5, -0.9, p, ha="center", va="center", fontsize=6.8, color=GOLD if "₹" in p else GREEN, weight="bold")
    ax.text(-0.15, -0.9, "Demo price", ha="right", va="center", fontsize=7.4, color=INK, weight="bold")
    fig.savefig(OUT / "basket_matrix.png", dpi=200, bbox_inches="tight", facecolor="white", pad_inches=0.08)
    plt.close(fig)


def journey():
    c = Canvas(6.6, 3.9)
    steps = ["1  Ask\nby voice or text,\nEnglish or Hindi", "2  Read the\nwhole sentence", "3  Decide the\nkind of request", "4  Answer from\ncalculators or\nchecked text", "5  Show the card,\nchart and steps"]
    for i, t in enumerate(steps):
        c.box(1 + i * 19.8, 68, 17.4, 25, t, ec=GOLD if i == 0 else (BLUE if i < 3 else GREEN), base=8.2)
        if i < 4:
            c.arrow(18.6 + i * 19.8, 80, 20.6 + i * 19.8, 80, MUTE)
    c.label(1, 60, "Step 3 sends the question to one of five paths:", base=8.6, color=INK, w=98, h=4)
    paths = ["App question\n-> guided tour", "Company\n-> facts, chart,\nwatch-outs", "Money concept\n-> checked answer", "Your numbers\n-> calculator", "Scam, tip or loss\n-> script, panel\nor recovery"]
    for i, t in enumerate(paths):
        c.box(1 + i * 19.8, 22, 17.4, 30, t, ec=BLUE, base=7.9)
        c.arrow(9.7 + i * 19.8, 66, 9.7 + i * 19.8, 53.2, "#c9c4b6")
    c.label(1, 9, "A local model, when installed, only picks from a closed list. It never writes an answer or a figure.", base=8, bold=False, color=CORAL, w=98, h=4)
    c.save("journey.png")


def tip_panel():
    c = Canvas(6.6, 4.6)
    c.box(1, 84, 98, 11, "A tip is read into a fixed form: which stock, buy or sell, target, time frame, reason offered, and what the reader is asked to do", ec=GOLD, base=8.4)
    names = ["Feasibility\nprice model", "Fundamentals\nimplied P/E", "Technicals\nchart and range", "Market structure\nliquidity, listing", "Source and incentive\nwho gains", "SEBI rules\nadviser limits", "Wording\none weak witness", "Consequence\nrupees at risk"]
    for i, n in enumerate(names):
        col, row = i % 4, i // 4
        c.box(1 + col * 25.3, 52 - row * 22, 22.5, 16, n, ec=BLUE, base=7.9)
    c.arrow(50, 84, 50, 79, MUTE)
    c.box(1, 2, 47, 16, "Chance it is a scam\n(independent signals combined)", ec=CORAL, base=8.4, bold=True)
    c.box(52, 2, 47, 16, "Backing for the idea\n(0 to 100, reasons shown)", ec=GREEN, base=8.4, bold=True)
    c.label(50, -4.5, "Result: ignore and report  |  ignore  |  verify first  |  research it  |  information only", base=7.6, bold=False, ha="center", w=98, h=3)
    c.save("tip_panel.png")


def trust():
    c = Canvas(6.6, 2.5)
    items = [("Dated public data", MUTE), ("Deterministic code", GREEN), ("Hand-written EN and HI", GREEN), ("Confidence and data age", GOLD), ("Shown with its working", GOLD)]
    for i, (t, col) in enumerate(items):
        c.box(1 + i * 19.8, 40, 17.4, 26, t, ec=col, base=8.2)
        if i < 4:
            c.arrow(18.6 + i * 19.8, 53, 20.6 + i * 19.8, 53, MUTE)
    c.box(14, 2, 72, 22, "No step lets a language model produce a number", ec=CORAL, base=9, bold=True, tc=CORAL)
    c.save("trust.png")


def architecture():
    c = Canvas(6.6, 5.4)
    layers = [("PEOPLE", [("Web app\n(Hindi, English)", GOLD), ("WhatsApp and SMS\n(simulator in app)", GOLD), ("Companion phone\n(real WhatsApp, separate build)", GOLD)]),
              ("INTERFACE", [("FastAPI and\nWebSocket events", BLUE), ("Voice in and out\n(local models)", BLUE), ("Setup and features\n(baskets, prices)", BLUE)]),
              ("BRAIN", [("Understanding layer\n(whole sentence)", GREEN), ("Calculators and\nchecked text", GREEN), ("Tip panel and\nresearch summary", GREEN)]),
              ("DATA", [("Point-in-time store\n(SQLite, dated)", MUTE), ("Prices, statements,\nownership, news", MUTE), ("Optional local model\n(picks only)", MUTE)])]
    for k, (name, items) in enumerate(layers):
        y = 78 - k * 20
        c.label(1, y + 6.5, name, base=7.6, color=MUTE, w=11, h=3)
        for i, (t, col) in enumerate(items):
            c.box(13 + i * 28.6, y, 26.2, 13, t, ec=col, base=8.2)
        if k < 3:
            for i in range(3):
                c.arrow(26.1 + i * 28.6, y - 0.5, 26.1 + i * 28.6, y - 5.6, "#c9c4b6")
    c.save("architecture.png")


def companion():
    c = Canvas(6.6, 3.2)
    c.box(1, 30, 22, 40, "WhatsApp\non the user's\nown phone", ec=GREEN, base=8.2)
    c.box(31, 30, 26, 40, "Companion session\n(Baileys or\nwhatsapp-web.js)\non a second device", ec=BLUE, base=8.2)
    c.box(64, 30, 35, 40, "Jarvis backend\nthe same answer path\nas the web assistant", ec=GOLD, base=8.2)
    c.arrow(23.4, 50, 30.6, 50, MUTE); c.arrow(57.4, 50, 63.6, 50, MUTE)
    c.arrow(63.6, 40, 57.4, 40, "#c9c4b6"); c.arrow(30.6, 40, 23.4, 40, "#c9c4b6")
    c.label(1, 19, "Built on a different device, not in this repository.\nNot an official WhatsApp API: terms of service and number safety\nmust be checked before any public launch.", base=8, bold=False, color=CORAL, w=98, h=17)
    c.label(1, 2, "The official alternative is the WhatsApp Business Platform through a licensed provider.", base=8, bold=False, color=MUTE, w=98, h=4)
    c.save("companion.png")


def stack():
    c = Canvas(6.6, 3.9)
    rows = [("Front end", "React, TypeScript, Vite; SVG charts; 3D orb; service worker"), ("API", "FastAPI, WebSocket events; about 110 routes"),
            ("Brain", "Understanding layer, rules, closed-list model pick (Ollama, optional)"), ("Analysis", "Calculators for fees, goals and tax; first-passage price model; attribution"),
            ("Voice", "faster-whisper in; Piper or Kokoro out; Hindi and English"), ("Data", "SQLite point-in-time store; yfinance; Google News; NSE list"),
            ("Offline", "Pyodide runs the rural calculators; cached app shell"), ("Channels", "Web, WhatsApp simulator, companion phone (separate build)")]
    for i, (a, b) in enumerate(rows):
        y = 88 - i * 11.2
        c.box(1, y, 16, 8.8, a, fc=GRAPH, ec=GRAPH, tc="white", base=8.4, bold=True)
        c.box(19, y, 80, 8.8, b, base=8.2, ec="#e4dcc6")
    c.save("stack.png")


def pit():
    c = Canvas(6.6, 2.7)
    c.ax.plot([3, 97], [40, 40], color=LINE, lw=3)
    for x, t, col in [(12, "Report published", GREEN), (50, "The clock\n(time machine)", GOLD), (84, "Later news", CORAL)]:
        c.ax.scatter([x], [40], s=120, color=col, zorder=3)
        c.label(x, 52, t, base=8.2, color=col, ha="center", w=28, h=9)
    c.box(3, 12, 42, 16, "Visible to the analysts", ec=GREEN, base=8.4, tc=GREEN)
    c.box(53, 12, 44, 16, "Hidden: the future is refused", ec=CORAL, base=8.4, tc=CORAL)
    c.save("pit.png")


def chain():
    c = Canvas(6.6, 2.8)
    items = [("Entry 1\nTRADE BLOCKED\nhash a91f", GREEN), ("Entry 2\nPLAN APPROVED\nprev a91f", GREEN), ("Entry 3\nTRADE BLOCKED\nprev 4c07", CORAL), ("Entry 4\nREBALANCE\nprev e2b3", GREEN)]
    for i, (t, col) in enumerate(items):
        c.box(1 + i * 24.5, 26, 21, 46, t, ec=col, base=8)
        if i < 3:
            c.arrow(22.6 + i * 24.5, 49, 24.0 + i * 24.5, 49, MUTE)
    c.label(1, 10, "Change entry 3 and its fingerprint changes; entry 4 no longer matches, so the break is shown.", base=8, bold=False, color=CORAL, w=98, h=6)
    c.save("chain.png")


def lender():
    fig, ax = plt.subplots(figsize=(6.4, 3.1))
    rates = [2, 3, 5, 8, 10]; yearly = [r * 12 for r in rates]
    ax.bar([f"Rs {r} per 100\na month" for r in rates], yearly, color=[GOLD, GOLD, CORAL, CORAL, CORAL], width=0.55)
    for i, v in enumerate(yearly):
        ax.text(i, v + 4, f"{v}% a year\nRs {int(50000 * v / 100):,} on Rs 50,000", ha="center", fontsize=7.2, color=INK, linespacing=1.25)
    ax.axhspan(10, 15, color=GREEN, alpha=0.12); ax.text(4.45, 17.5, "typical bank loan (about 10-15%)", ha="right", fontsize=7, color=GREEN)
    ax.set_ylim(0, 165); ax.set_yticks([]); ax.tick_params(axis="x", labelsize=7.4)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.set_title("A monthly rate hides the yearly cost (simple interest, illustration)", fontsize=8.6, loc="left", weight="bold")
    fig.savefig(OUT / "lender.png", dpi=200, bbox_inches="tight", facecolor="white", pad_inches=0.08); plt.close(fig)


def recovery():
    c = Canvas(6.6, 2.9)
    c.ax.plot([3, 97], [40, 40], color=LINE, lw=3)
    pts = [(10, "Now", "Stop. Send\nnothing more", CORAL), (30, "Minutes", "Freeze card\nand UPI", GOLD), (50, "Within the hour", "Call 1930;\nreport online", GOLD), (70, "Today", "Tell the bank\nin writing", BLUE), (90, "This week", "Change\npasswords", GREEN)]
    for x, a, b, col in pts:
        c.ax.scatter([x], [40], s=110, color=col, zorder=3)
        c.label(x, 52, a, base=8, color=col, ha="center", w=18, h=5)
        c.label(x, 24, b, base=7.8, bold=False, ha="center", w=18, h=12)
    c.save("recovery.png")


def partners():
    c = Canvas(6.6, 3.6)
    c.box(36, 36, 28, 26, "PLATFORM\ncontent, tools, channel", fc="#fff4d8", ec=GOLD, base=8.6, bold=True)
    ring = [("SHG federations\nand state missions", 1, 72), ("Co-operative banks,\nMFIs, correspondents", 36, 80), ("NGOs and CSR funds", 71, 72), ("Common Service\nCentres, post offices", 1, 10), ("Registered advisers\nfor premium advice", 36, 0), ("Messaging and\ntelecom partners", 71, 10)]
    for t, x, y in ring:
        c.box(x, y, 28, 14, t, ec=BLUE, base=7.9)
        cx, cy = x + 14, y + 7
        c.arrow(cx, cy, 50, 49, "#c9c4b6")
    c.save("partners.png")


def business():
    c = Canvas(6.6, 4.0)
    c.box(38, 40, 24, 20, "THE PLATFORM\nfree core, paid tools", fc="#fff4d8", ec=GOLD, base=8.6, bold=True)
    users = [("Rural and self-help users: free", 1, 74, GREEN), ("Retail investors: subscription", 1, 42, BLUE), ("Advisers: API and seats", 1, 10, BLUE)]
    inst = [("Banks: licence for their customers", 68, 74, GOLD), ("NGOs and missions: programme fees", 68, 42, GOLD), ("CSR and funders: outcome reports", 68, 10, GOLD)]
    for t, x, y, col in users:
        c.box(x, y, 29, 14, t, ec=col, base=8)
        c.arrow(x + 29.4, y + 7, 37.6, 50, "#c9c4b6")
    for t, x, y, col in inst:
        c.box(x, y, 29, 14, t, ec=col, base=8)
        c.arrow(62.4, 50, x - 0.4, y + 7, "#c9c4b6")
    c.label(1, 96, "Who pays for what", base=9, color=INK, w=60, h=4)
    c.save("business.png")


def prices():
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    names = ["Full prototype\n(pitch)", "Banks and\nco-op banks", "Farmers and\nrural families", "Self-help groups\nand NGOs", "Middle-class\ninvestors"]
    vals = [0, 499, 0, 0, 597]
    ax.bar(names, vals, color=[GREEN if v == 0 else GOLD for v in vals], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 18, "Free" if v == 0 else f"Rs {v} / month", ha="center", fontsize=7.4, weight="bold", color=INK)
    ax.set_ylim(0, 700); ax.set_yticks([]); ax.tick_params(axis="x", labelsize=7.2)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.set_title("Demo monthly price of each starting basket (dummy, nothing is charged)", fontsize=8.4, loc="left", weight="bold")
    fig.savefig(OUT / "prices.png", dpi=200, bbox_inches="tight", facecolor="white", pad_inches=0.08); plt.close(fig)


def economics():
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    seg = ["Rural and self-help\nusers (free)", "Retail investors\n(subscription)", "Banks and programmes\n(licence, contract)"]
    serve = [2, 4, 6]
    income_direct = [0, 6, 0]
    income_partner = [0, 0, 40]
    x = range(3)
    ax.bar([i - 0.2 for i in x], serve, 0.36, color=GRAPH, label="Cost to serve (illustrative)")
    ax.bar([i + 0.2 for i in x], [a + b for a, b in zip(income_direct, income_partner)], 0.36, color=GOLD, label="Revenue per unit (illustrative)")
    ax.set_xticks(list(x)); ax.set_xticklabels(seg, fontsize=7.4)
    ax.set_ylabel("Rs per user or unit per month", fontsize=7.4)
    ax.tick_params(axis="y", labelsize=7)
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
    ax.set_title("Illustrative structure only: replace with pilot data", fontsize=8.4, loc="left", weight="bold")
    fig.savefig(OUT / "economics.png", dpi=200, bbox_inches="tight", facecolor="white", pad_inches=0.08); plt.close(fig)


def run():
    for f in (problems, setup_flow, basket_matrix, journey, tip_panel, trust, architecture, companion, stack, pit, chain, lender, recovery, partners, business, prices, economics):
        f()
    print("v2 figures:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    run()
