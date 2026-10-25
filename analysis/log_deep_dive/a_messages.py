from load import load
from cats import MSG_CATS
import collections, random, json, sys
g = load()
rows = collections.defaultdict(collections.Counter)
n = collections.Counter()
ex = collections.defaultdict(list)
for t in g.values():
    for e in t["events"]:
        if e["type"] != "secret_message": continue
        arm = t["arm"]; n[arm] += 1
        for c, rx in MSG_CATS.items():
            if rx.search(e["message"]):
                rows[arm][c] += 1
                ex[(arm, c)].append((t["game_id"], e["turn"], e["sender"], e["receiver"], e["message"]))
print("messages per arm", dict(n))
print(f"{'category':28s}" + "".join(f"arm{a:<6d}" for a in (2,3,4,5,7)))
for c in MSG_CATS:
    print(f"{c:28s}" + "".join(f"{100*rows[a][c]/n[a]:6.1f}% " for a in (2,3,4,5,7)))
json.dump({str(a): {c: rows[a][c]/n[a] for c in MSG_CATS} | {"n": n[a]} for a in (2,3,4,5,7)}, open("out_msg_cats.json","w"), indent=1)
if len(sys.argv) > 1:
    r = random.Random(0)
    for c in sys.argv[1:]:
        for a in (4,5,7):
            L = ex[(a, c)]
            print(f"\n=== {c} arm{a} ({len(L)})")
            for x in r.sample(L, min(4, len(L))):
                print(" -", x[0], "t", x[1], x[2], "->", x[3], ":", x[4][:300])
