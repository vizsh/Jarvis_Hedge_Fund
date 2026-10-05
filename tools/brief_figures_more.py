"""More diagrams for the brief. Imported and run by brief_figures.py."""
import matplotlib.pyplot as plt

from brief_figures import BLUE, CORAL, GOLD, GREEN, INK, MUTE, arrow, box, canvas, save


def lender():
    fig, ax = plt.subplots(figsize=(7, 3.5))
    rates = [2, 3, 5, 8, 10]
    yearly = [r * 12 for r in rates]
    cols = [GOLD, GOLD, CORAL, CORAL, CORAL]
    ax.bar([f"Rs {r} per 100\nper month" for r in rates], yearly, color=cols, width=0.55)
    for i, v in enumerate(yearly):
        ax.text(i, v + 3, f"{v}% a year\nRs {int(50000 * v / 100):,} on Rs 50,000", ha="center", fontsize=8, color=INK)
    ax.axhline(14, color=GREEN, ls="--")
    ax.text(4.45, 18, "typical bank loan range (about 10-15%)", ha="right", fontsize=7.8, color=GREEN)
    ax.set_ylim(0, 150); ax.set_yticks([])
    for s_ in ("top", "right", "left"):
        ax.spines[s_].set_visible(False)
    ax.set_title("Why 'a few rupees per hundred' is expensive (simple yearly interest)", fontsize=9.5, loc="left", weight="bold")
    save(fig, "lender.png")


def recovery():
    fig, ax = canvas(7.4, 2.9, "rc")
    ax.plot([3, 70], [14, 14], color="#c9c4b6", lw=3)
    pts = [(6, "Now", "Stop. Do not\nsend more money", CORAL), (22, "Minutes", "Freeze card / UPI\nin the bank app", GOLD), (38, "Within the hour", "Call 1930 and\nreport online", GOLD),
           (54, "Today", "Tell the bank in\nwriting; keep proof", BLUE), (68, "This week", "Change passwords,\nwatch accounts", GREEN)]
    for x, a, b, c in pts:
        ax.scatter([x], [14], s=150, color=c, zorder=3)
        ax.text(x, 20, a, ha="center", fontsize=8.5, weight="bold", color=c)
        ax.text(x, 7, b, ha="center", va="center", fontsize=7.8, color=INK, linespacing=1.4)
    save(fig, "recovery.png")


def chain():
    fig, ax = canvas(7.4, 2.9, "ch")
    items = [("Entry 1\nTRADE BLOCKED\nhash a91f", GREEN), ("Entry 2\nPLAN APPROVED\nprev a91f, hash 4c07", GREEN), ("Entry 3\nTRADE BLOCKED\nprev 4c07, hash e2b3", CORAL), ("Entry 4\nREBALANCE\nprev e2b3, hash 7d19", GREEN)]
    for i, (t, c) in enumerate(items):
        box(ax, 1 + i * 18, 12, 16, 11, t, ec=c, fs=7.8)
        if i < 3:
            arrow(ax, 17.4 + i * 18, 17.5, 18.8 + i * 18, 17.5)
    ax.text(1, 5, "Edit entry 3 and its hash changes; entry 4 no longer matches, so the chain reports exactly where it broke.", fontsize=8.3, style="italic", color=CORAL)
    save(fig, "chain.png")


def partners():
    fig, ax = canvas(7.4, 3.6, "pm")
    box(ax, 28, 15, 18, 8, "PLATFORM\n(content, tools,\nchannel)", fc="#fff4d8", ec=GOLD, fs=9, bold=True)
    ring = [("SHG federations,\nNRLM missions", 2, 28), ("Co-operative banks,\nMFIs, BCs", 28, 30), ("NGOs, CSR funds", 54, 28), ("Common Service\nCentres, post offices", 2, 4), ("Registered advisers\n(premium advice)", 28, 1), ("Telecom / WhatsApp\nproviders", 54, 4)]
    for t, x, y in ring:
        box(ax, x, y, 18, 6, t, ec=BLUE, fs=7.8)
        arrow(ax, x + 9, y + (0 if y > 15 else 6.2), 37, 23.4 if y > 15 else 14.6, "#c9c4b6")
    save(fig, "partners.png")


def run():
    for f in (lender, recovery, chain, partners):
        f()
