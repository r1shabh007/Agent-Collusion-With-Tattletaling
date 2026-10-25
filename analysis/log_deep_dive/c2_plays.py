"""Per play: was a bluff caught, was an honest play wrongly challenged; challenge precision. Game-clustered bootstrap."""
from load import load
import collections, json, random, statistics as st
g = load()
per_game = collections.defaultdict(list)
for t in g.values():
    ch = {e["turn"]: e for e in t["events"] if e["type"] == "challenge"}
    b = h = bc = hc = 0
    for e in t["events"]:
        if e["type"] != "play": continue
        c = e["turn"] in ch
        if e["bluff"]: b += 1; bc += c
        else: h += 1; hc += c
    per_game[t["arm"]].append((b, bc, h, hc))
def agg(L):
    b = sum(x[0] for x in L); bc = sum(x[1] for x in L); h = sum(x[2] for x in L); hc = sum(x[3] for x in L)
    return dict(bluffs=b, bluff_caught=bc/b if b else float("nan"), honest=h, honest_challenged=hc/h if h else float("nan"),
                challenge_precision=bc/(bc+hc) if bc+hc else float("nan"))
def ci(L, key, n=5000):
    r = random.Random(1); v = sorted(agg(r.choices(L, k=len(L)))[key] for _ in range(n)); return v[int(.025*n)], v[int(.975*n)-1]
out = {}
for arm in range(1, 8):
    a = agg(per_game[arm]); a["bluff_caught_ci"] = ci(per_game[arm], "bluff_caught"); a["precision_ci"] = ci(per_game[arm], "challenge_precision")
    out[arm] = a
    print(arm, {k: (round(v,3) if isinstance(v,float) else v) for k, v in a.items()})
json.dump(out, open("out_plays.json", "w"), indent=1)
