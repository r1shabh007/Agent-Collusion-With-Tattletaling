"""Does the channel change who gets challenged? Challenge decisions split by whether the player is a channel partner,
and by whether the play was a bluff. Game-clustered bootstrap CIs for the partner/non-partner gap."""
from load import load, partners_at
import collections, json, random
g = load()
rows = []  # (arm, gid, partner, bluff, challenged)
for t in g.values():
    arm = t["arm"]
    plays = {e["turn"]: e for e in t["events"] if e["type"] == "play"}
    for x in t["decisions"]:
        if x["phase"] != "challenge": continue
        p = plays.get(x["turn"])
        if not p: continue
        P = partners_at(t, x["turn"])
        rows.append((arm, t["game_id"], p["player"] in P[x["agent"]], p["bluff"], bool(x["decision"]), x["agent"], p["player"]))
def rate(R): return sum(r[4] for r in R) / len(R) if R else float("nan")
def boot_gap(R, n=4000, seed=0):
    rnd = random.Random(seed)
    games = sorted({r[1] for r in R}); by = collections.defaultdict(list)
    for r in R: by[r[1]].append(r)
    gaps = []
    for _ in range(n):
        S = [r for gid in rnd.choices(games, k=len(games)) for r in by[gid]]
        a = [r for r in S if r[2]]; b = [r for r in S if not r[2]]
        if a and b: gaps.append(rate(b) - rate(a))
    gaps.sort(); return gaps[int(.025*len(gaps))], gaps[int(.975*len(gaps))-1]
out = {}
print(f"{'arm':4s} {'cond':10s} {'n_part':>7s} {'chal_part':>9s} {'n_non':>6s} {'chal_non':>8s}  gap(non-part) 95%CI")
for arm in (1,2,3,4,5,6,7):
    A = [r for r in rows if r[0] == arm]
    for cond, F in (("all", lambda r: True), ("bluff", lambda r: r[3]), ("honest", lambda r: not r[3])):
        S = [r for r in A if F(r)]
        pa = [r for r in S if r[2]]; no = [r for r in S if not r[2]]
        ci = boot_gap(S) if pa and no else (float("nan"), float("nan"))
        out[f"{arm}_{cond}"] = dict(n_partner=len(pa), challenge_partner=rate(pa), n_nonpartner=len(no), challenge_nonpartner=rate(no), gap_ci=ci)
        print(f"{arm:<4d} {cond:10s} {len(pa):7d} {rate(pa):9.3f} {len(no):6d} {rate(no):8.3f}  {rate(no)-rate(pa) if pa else float('nan'):+.3f} [{ci[0]:+.3f},{ci[1]:+.3f}]")
json.dump(out, open("out_challenges.json","w"), indent=1)
# Bluff 'protection': among bluffs, P(caught) for partner-owned plays — from transcript: was the play challenged at all?
print("\nPer-play outcome: share of bluffs that got challenged, by whether ALL other active players were partners of the bluffer")
for arm in (2,4,5,7):
    c = collections.Counter()
    for t in g.values():
        if t["arm"] != arm: continue
        for e in t["events"]:
            if e["type"] == "play" and e["bluff"]:
                P = partners_at(t, e["turn"])
                # who was asked: challenge_order event of same turn
                order = next((x["order"] for x in t["events"] if x["type"] == "challenge_order" and x["turn"] == e["turn"]), [])
                allp = order and all(o in P[e["player"]] for o in order)
                caught = any(x["type"] == "challenge" and x["turn"] == e["turn"] for x in t["events"])
                c[(bool(allp), caught)] += 1
    for k in (True, False):
        n = c[(k, True)] + c[(k, False)]
        print(f" arm{arm} all-asked-are-partners={k}: bluffs={n}, challenged={c[(k,True)]/n if n else float('nan'):.2f}")
