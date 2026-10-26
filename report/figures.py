#!/usr/bin/env python3
"""
Figures 2-4 of main.tex, computed from the released transcripts.

    python3 report/figures.py [results/run1] [out_dir]

Writes fig2_offers.pdf, fig3_targets.pdf and fig4_points.pdf (the names main.tex's \\figimg expects)
and prints every plotted number next to the value the text reports, so the two can be checked.

All rates are pooled over decisions within an arm; 95% intervals resample whole games
(10,000 bootstrap resamples, percentile method), as in the paper.
"""
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUN = sys.argv[1] if len(sys.argv) > 1 else "results/run1"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
B = 10_000
SEED = 0

# ---------------------------------------------------------------- per-game counts from transcripts
POINTS_MODE = {4, 7}             # arms where a correct accusation moves points (+3 accuser, -2 accused)
NO_PARTNER = {7}                 # arm 7: own partners cannot be accused


def game_counts(t):
    arm = t["arm"]
    players = t["players"]
    c = defaultdict(float)
    active = set(players)
    partners = defaultdict(set)
    for e in t["events"]:
        ty = e["type"]
        if ty == "offer_decision":
            c["offer_decisions"] += 1
            c["offers"] += e["decision"] == "ACCEPT"
        elif ty == "invitation_decision":
            c["invitations"] += 1
            c["invitations_accepted"] += bool(e["accepted"])
        elif ty == "channel_opened":
            a, b = e["members"]
            partners[a].add(b); partners[b].add(a)
        elif ty == "trigger" and e["fired"]:
            active.discard(e["player"])
        elif ty == "banned":
            active.discard(e["player"])
        elif ty == "accusation_phase":
            # who had at least one player they were allowed to accuse
            for a in active:
                opts = [b for b in active if b != a and not (arm in NO_PARTNER and b in partners[a])]
                c["accusation_decisions"] += bool(opts)
            c["phases"] += 1
            c["colluding_share_sum"] += len(e["colluding"]) / len(active)
        elif ty == "accusation":
            c["accusations"] += 1
            c["partner_accusations"] += e["accused"] in partners[e["accuser"]]
            if arm in POINTS_MODE and e["correct"]:
                c["pts_accusation"] += 3 - 2
        elif ty == "challenge":
            if e["bluff"]:
                c["pts_caught_bluff"] += 2
            else:
                c["pts_declined_honest"] += 2 * len(e["declined_before"])
        elif ty == "no_challenge":
            if not e["bluff"]:
                c["pts_declined_honest"] += 2 * len(e["declined"])
    c["pts_total"] = sum(t["final_scores"].values())
    c["pts_rest"] = c["pts_total"] - c["pts_declined_honest"] - c["pts_caught_bluff"] - c["pts_accusation"]
    c["agents"] = len(players)
    return c


games = defaultdict(list)
for p in sorted(glob.glob(os.path.join(RUN, "arm*", "*", "transcript.json"))):
    t = json.load(open(p))
    games[t["arm"]].append(game_counts(t))
ARMS = sorted(games)
rng = np.random.default_rng(SEED)
IDX = {arm: rng.integers(0, len(games[arm]), size=(B, len(games[arm]))) for arm in ARMS}


def ratio(arm, num, den):
    """pooled num/den with a game-clustered bootstrap CI."""
    n = np.array([g[num] for g in games[arm]]); d = np.array([g[den] for g in games[arm]])
    if d.sum() == 0:
        return None
    boot = n[IDX[arm]].sum(1) / np.maximum(d[IDX[arm]].sum(1), 1e-12)
    return n.sum() / d.sum(), *np.percentile(boot, [2.5, 97.5])


# ---------------------------------------------------------------- style: Times to match the paper
# TrueType Times faces only, so the PDFs embed clean Type 42 fonts (no Type 3, no CFF mismatch)
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Liberation Serif", "Times", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#8a8984",
    "axes.linewidth": 0.6, "xtick.color": "#52514e", "ytick.color": "#52514e",
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "axes.labelcolor": "#2b2b2a",
    "text.color": "#2b2b2a", "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})
BLUE, ORANGE, AQUA, GREY, LIGHT = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984", "#c8c7c0"
INK2 = "#52514e"
ARM_LABEL = {1: "Arm 1\nbaseline", 2: "Arm 2\nchannels", 3: "Arm 3\nban", 4: "Arm 4\npoints",
             5: "Arm 5\ngrader", 6: "Arm 6\nno channels", 7: "Arm 7\npoints,\nno partner"}
ERR = dict(ecolor="#2b2b2a", elinewidth=0.7, capsize=2.2, capthick=0.7)


def grid(ax, axis="y"):
    ax.grid(axis=axis, color="#e6e5e0", linewidth=0.5, zorder=0)
    ax.set_axisbelow(True)


def pct_axis(ax, top=100):
    ax.set_ylim(0, top)
    ax.set_yticks(range(0, top + 1, 25))
    ax.set_yticklabels([f"{v}%" for v in range(0, top + 1, 25)])


def check(label, got, expected):
    flag = "" if expected is None or abs(got - expected) <= 0.6 else "   <-- differs"
    print(f"  {label:<48} {got:7.1f}   paper: {'' if expected is None else expected}{flag}")


# ---------------------------------------------------------------- Figure 2: offers and acceptances
print("Figure 2: offers and invitation acceptance (%)")
arms2 = [2, 3, 4, 5, 7]
paper2 = {2: (96, 74), 3: (42, 10), 4: (65, 24), 5: (91, 53), 7: (51, 27)}
off = {a: ratio(a, "offers", "offer_decisions") for a in arms2}
inv = {a: ratio(a, "invitations_accepted", "invitations") for a in arms2}
for a in arms2:
    check(f"arm {a} offer [{off[a][1]*100:.0f}, {off[a][2]*100:.0f}]", off[a][0] * 100, paper2[a][0])
    check(f"arm {a} invitation accepted [{inv[a][1]*100:.0f}, {inv[a][2]*100:.0f}]", inv[a][0] * 100, paper2[a][1])

fig, ax = plt.subplots(figsize=(5.2, 2.35))
x = np.arange(len(arms2)); w = 0.36
for k, (vals, col, lab) in enumerate([(off, BLUE, "offer extended (share of offer decisions)"),
                                      (inv, ORANGE, "invitation accepted (share of invitations)")]):
    m = np.array([vals[a][0] for a in arms2]) * 100
    lo = m - np.array([vals[a][1] for a in arms2]) * 100
    hi = np.array([vals[a][2] for a in arms2]) * 100 - m
    xs = x + (k - 0.5) * (w + 0.03)
    ax.bar(xs, m, w, color=col, label=lab, zorder=2)
    ax.errorbar(xs, m, yerr=[lo, hi], fmt="none", zorder=3, **ERR)
    for xi, mi, hii in zip(xs, m, hi):
        ax.text(xi, mi + hii + 2, f"{mi:.0f}", ha="center", va="bottom", fontsize=7.5, color=INK2)
ax.set_xticks(x); ax.set_xticklabels([ARM_LABEL[a] for a in arms2])
pct_axis(ax, 100); ax.set_ylim(0, 112); grid(ax)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.2), ncol=2, frameon=False, handlelength=1, handleheight=0.9,
          columnspacing=1.4)
fig.savefig(os.path.join(OUT, "fig2_offers.pdf"))
plt.close(fig)

# ---------------------------------------------------------------- Figure 3: accusation targets, saturation
print("\nFigure 3a: accusation decisions (%)")
arms3 = [3, 4, 5, 6, 7]
paper_any = {3: 16, 4: 94, 5: 91, 6: 54, 7: 84}
paper_share = {3: 97, 4: 95, 5: 100}
any_ = {a: ratio(a, "accusations", "accusation_decisions") for a in arms3}
own = {a: ratio(a, "partner_accusations", "accusation_decisions") for a in arms3}
share = {a: ratio(a, "partner_accusations", "accusations") for a in arms3}
for a in arms3:
    check(f"arm {a} accuse anyone [{any_[a][1]*100:.0f}, {any_[a][2]*100:.0f}]", any_[a][0] * 100, paper_any[a])
    check(f"arm {a} accuse own partner (of decisions)", own[a][0] * 100, None)
    if a in paper_share:
        check(f"arm {a} own partner (of accusations)", share[a][0] * 100, paper_share[a])

print("\nFigure 3b: share of active players counted as colluding (%)")
arms3b = [3, 4, 5, 7]
paper_sat = {4: 99, 5: 100, 7: 100}
sat = {a: ratio(a, "colluding_share_sum", "phases") for a in arms3b}
for a in arms3b:
    check(f"arm {a} colluding share [{sat[a][1]*100:.0f}, {sat[a][2]*100:.0f}]", sat[a][0] * 100, paper_sat.get(a))

fig, (axa, axb) = plt.subplots(1, 2, figsize=(5.85, 2.45), gridspec_kw=dict(width_ratios=[5, 3.6], wspace=0.32))
x = np.arange(len(arms3)); w = 0.62
m_any = np.array([any_[a][0] for a in arms3]) * 100
m_own = np.array([own[a][0] for a in arms3]) * 100
axa.bar(x, m_any, w, color=LIGHT, label="accuses anyone", zorder=2)
axa.bar(x, m_own, w * 0.56, color=ORANGE, label="accuses own partner", zorder=3)
axa.errorbar(x, m_any, yerr=[m_any - np.array([any_[a][1] for a in arms3]) * 100,
                             np.array([any_[a][2] for a in arms3]) * 100 - m_any], fmt="none", zorder=4, **ERR)
for xi, a in zip(x, arms3):
    top = any_[a][2] * 100
    if a in paper_share:
        txt = f"{share[a][0]*100:.0f}% at\npartner"
    elif a == 6:
        txt = "no\nchannels"
    else:
        txt = "partners\nexcluded"
    axa.text(xi, top + 2.5, txt, ha="center", va="bottom", fontsize=6.8, color=INK2, linespacing=0.95)
axa.set_xticks(x); axa.set_xticklabels([ARM_LABEL[a] for a in arms3], fontsize=7.2)
pct_axis(axa, 100); axa.set_ylim(0, 122); grid(axa)
axa.set_ylabel("share of accusation decisions")
axa.legend(loc="upper center", bbox_to_anchor=(0.5, 1.2), ncol=2, frameon=False, handlelength=1, handleheight=0.9,
           columnspacing=1.2)
axa.set_title("(a)", loc="left", fontweight="bold", x=-0.16, y=1.08)

x = np.arange(len(arms3b))
m = np.array([sat[a][0] for a in arms3b]) * 100
axb.bar(x, m, w, color=GREY, zorder=2)
axb.errorbar(x, m, yerr=[m - np.array([sat[a][1] for a in arms3b]) * 100,
                         np.array([sat[a][2] for a in arms3b]) * 100 - m], fmt="none", zorder=3, **ERR)
for xi, mi, a in zip(x, m, arms3b):
    axb.text(xi, sat[a][2] * 100 + 2.5, f"{mi:.0f}%", ha="center", va="bottom", fontsize=7.5, color=INK2)
axb.set_xticks(x); axb.set_xticklabels([ARM_LABEL[a] for a in arms3b], fontsize=7.2)
pct_axis(axb, 100); axb.set_ylim(0, 122); grid(axb)
axb.set_ylabel("active players counted as colluding")
axb.set_title("(b)", loc="left", fontweight="bold", x=-0.27, y=1.08)
fig.savefig(os.path.join(OUT, "fig3_targets.pdf"))
plt.close(fig)

# ---------------------------------------------------------------- Figure 4: points by source
print("\nFigure 4: points per agent-game by source")
arms4 = ARMS
SOURCES = [("pts_declined_honest", "declined an honest play (+2)", BLUE),
           ("pts_caught_bluff", "caught a bluff (+2)", ORANGE),
           ("pts_accusation", "accusation transfers (+3 / −2)", AQUA),
           ("pts_rest", "rest: eliminations, survival, emptied hands, wrong\nchallenges (nets to within ±0.4 in every arm)", LIGHT)]
paper_tot = {1: 16.2, 2: 34.4, 3: 2.9, 4: 40.6, 5: 29.0, 6: 15.3, 7: 37.3}
paper_ci = {1: (10.4, 22.3), 2: (21.7, 46.8), 3: (1.4, 4.3), 4: (24.1, 60.6), 5: (18.4, 41.4),
            6: (10.2, 21.1), 7: (27.4, 48.0)}
vals = {a: {k: ratio(a, k, "agents") for k, _, _ in SOURCES + [("pts_total", "", "")]} for a in arms4}
for a in arms4:
    tot = vals[a]["pts_total"]
    check(f"arm {a} total [{tot[1]:.1f}, {tot[2]:.1f}] (paper CI {paper_ci[a]})", tot[0], paper_tot[a])
    print("    " + ", ".join(f"{k[4:]}={vals[a][k][0]:.1f}" for k, _, _ in SOURCES))

fig, ax = plt.subplots(figsize=(5.85, 2.75))
x = np.arange(len(arms4)); w = 0.6
pos = np.zeros(len(arms4)); neg = np.zeros(len(arms4))
for k, lab, col in SOURCES:
    v = np.array([vals[a][k][0] for a in arms4])
    base = np.where(v >= 0, pos, neg)
    ax.bar(x, v, w, bottom=base, color=col, label=lab, zorder=2, edgecolor="white", linewidth=0.8)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
tot = np.array([vals[a]["pts_total"][0] for a in arms4])
lo = np.array([vals[a]["pts_total"][1] for a in arms4]); hi = np.array([vals[a]["pts_total"][2] for a in arms4])
ax.scatter(x, tot, s=16, color="#0b0b0b", zorder=5, label="total, 95% CI", marker="D", linewidths=0)
ax.errorbar(x, tot, yerr=[tot - lo, hi - tot], fmt="none", zorder=4, **ERR)
for xi, ti, hii in zip(x, tot, hi):
    ax.text(xi + 0.08, hii + 1.2, f"{ti:.1f}", ha="center", va="bottom", fontsize=7.5, color=INK2)
ax.axhline(0, color="#8a8984", linewidth=0.6, zorder=3)
ax.set_xticks(x); ax.set_xticklabels([ARM_LABEL[a] for a in arms4], fontsize=7.4)
ax.set_ylabel("points per agent per game")
ax.set_ylim(min(-2, neg.min() - 1), max(hi.max(), pos.max()) + 7)
grid(ax)
h, l = ax.get_legend_handles_labels()
order = [1, 2, 3, 4, 0]
ax.legend([h[i] for i in order], [l[i] for i in order], loc="upper left", bbox_to_anchor=(0, 1.3), ncol=2,
          frameon=False, handlelength=1, handleheight=0.9, columnspacing=1.2, fontsize=7.6)
fig.savefig(os.path.join(OUT, "fig4_points.pdf"))
plt.close(fig)

print(f"\nwrote fig2_offers.pdf, fig3_targets.pdf, fig4_points.pdf to {os.path.abspath(OUT)}")
