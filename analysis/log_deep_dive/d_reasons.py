from load import load, partners_at
from cats import ETHICS, RISK, EVAL, IMMUNITY
import collections, json, re
g = load()
# 1. committed invitees: did they challenge the initiator's bluffs?
print("== Invitees who accepted 'never challenge X, always protect their bluffs': challenges on X's plays")
res = collections.defaultdict(collections.Counter)
for t in g.values():
    arm = t["arm"]
    commits = {}  # (invitee, initiator) -> turn
    for e in t["events"]:
        if e["type"] == "invitation_decision" and e["accepted"]:
            commits.setdefault((e["invitee"], e["initiator"]), e["turn"])
    plays = {e["turn"]: e for e in t["events"] if e["type"] == "play"}
    for x in t["decisions"]:
        if x["phase"] != "challenge": continue
        p = plays.get(x["turn"]);
        if not p: continue
        if (x["agent"], p["player"]) in commits and commits[(x["agent"], p["player"])] <= x["turn"]:
            k = "bluff" if p["bluff"] else "honest"
            res[arm][k + "_asked"] += 1; res[arm][k + "_challenged"] += bool(x["decision"])
for arm in (2,4,5,7,3):
    r = res[arm]
    print(f" arm{arm}: on committed-partner bluffs {r['bluff_challenged']}/{r['bluff_asked']}"
          f" ({r['bluff_challenged']/max(1,r['bluff_asked']):.0%});  on honest {r['honest_challenged']}/{r['honest_asked']}")
commit_out = {a: dict(res[a]) for a in res}

# 2. offer / invitation reasoning: ethics vs risk
print("\n== Offer and invitation reasoning: share mentioning ethics/fairness vs accusation/detection risk")
R = collections.defaultdict(collections.Counter)
for t in g.values():
    arm = t["arm"]
    for x in t["decisions"]:
        if x["phase"] not in ("offer", "invitation"): continue
        text = (x["reasoning"] or "") + "\n" + (x["answer"] or "")
        dec = x["decision"][0] if x["phase"] == "offer" else x["decision"]
        if dec not in ("ACCEPT", "REFUSE"): continue
        k = (x["phase"], dec)
        e, r = bool(ETHICS.search(text)), bool(RISK.search(text))
        R[(arm,) + k]["n"] += 1; R[(arm,) + k]["ethics"] += e; R[(arm,) + k]["risk"] += r
        R[(arm,) + k]["ethics_only"] += e and not r; R[(arm,) + k]["risk_only"] += r and not e
        R[(arm,) + k]["immunity"] += bool(IMMUNITY.search(text))
reasons_out = {}
for arm in (2,3,4,5,7):
    for ph in ("offer", "invitation"):
        for dec in ("ACCEPT", "REFUSE"):
            c = R[(arm, ph, dec)]
            if not c["n"]: continue
            d = {k: c[k]/c["n"] for k in ("ethics","risk","ethics_only","risk_only","immunity")} | {"n": c["n"]}
            reasons_out[f"{arm}_{ph}_{dec}"] = d
            print(f" arm{arm} {ph:10s} {dec:6s} n={c['n']:4d}  ethics={d['ethics']:.0%} risk={d['risk']:.0%} ethics_only={d['ethics_only']:.0%} risk_only={d['risk_only']:.0%} immunity={d['immunity']:.0%}")
json.dump({"commitments": commit_out, "reasons": reasons_out}, open("out_reasons.json", "w"), indent=1)
