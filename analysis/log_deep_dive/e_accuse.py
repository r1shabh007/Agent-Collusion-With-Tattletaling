from load import load, partners_at
from cats import ACC_REASONS
import collections, json, re
g = load()
def reason(x):
    a = x["answer"] or ""
    m = re.search(r'"reason"\s*:\s*"((?:[^"\\]|\\.)*)"', a, re.S)
    return m.group(1) if m else a
R = collections.defaultdict(collections.Counter)
ex = collections.defaultdict(list)
for t in g.values():
    arm = t["arm"]
    for x in t["decisions"]:
        if x["phase"] != "accusation": continue
        tgt = x["decision"][0] if isinstance(x["decision"], list) and x["decision"] else None
        mine = set(x["private_state"]["channels"])
        kind = "none" if tgt in (None, "none") else ("partner" if tgt in mine else "outsider")
        txt = reason(x)
        R[(arm, kind)]["n"] += 1
        for c, rx in ACC_REASONS.items():
            if rx.search(txt):
                R[(arm, kind)][c] += 1
                ex[(arm, kind, c)].append((t["game_id"], x["agent"], x["turn"], tgt, txt[:260]))
out = {}
cats = list(ACC_REASONS)
print(f"{'arm/kind':16s} {'n':>5s} " + " ".join(f"{c[:14]:>14s}" for c in cats))
for arm in (3,4,5,6,7):
    for kind in ("partner", "outsider", "none"):
        c = R[(arm, kind)]
        if c["n"] < 5: continue
        out[f"{arm}_{kind}"] = {k: c[k]/c["n"] for k in cats} | {"n": c["n"]}
        print(f"arm{arm} {kind:10s} {c['n']:5d} " + " ".join(f"{c[k]/c['n']:14.0%}" for k in cats))
json.dump(out, open("out_accuse_reasons.json", "w"), indent=1)
import random; r = random.Random(2)
for key in [(5,"partner","honesty_or_grader"), (5,"partner","knows_from_channel"), (3,"partner","preemptive_fear"), (6,"outsider","free_bet"), (6,"outsider","no_evidence_admitted"), (7,"outsider","free_bet"), (4,"partner","pact_or_agreed")]:
    L = ex[key]; print(f"\n--- {key} ({len(L)})")
    for e in r.sample(L, min(3, len(L))): print("  ", e)
