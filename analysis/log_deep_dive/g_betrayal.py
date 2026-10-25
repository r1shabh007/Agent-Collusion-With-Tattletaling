from load import load, partners_at
import re, collections, json
g = load()
out = {}
# arm 3 channel lifetimes
ch = betrayed_same = betrayed_any = 0
for t in g.values():
    if t["arm"] != 3: continue
    acc = [(e["turn"], frozenset((e["accuser"], e["accused"]))) for e in t["events"] if e["type"] == "accusation"]
    for e in t["events"]:
        if e["type"] != "channel_opened": continue
        ch += 1; k = frozenset(e["members"])
        ts = [T for T, p in acc if p == k]
        betrayed_any += bool(ts); betrayed_same += any(T == e["turn"] for T in ts)
out["arm3_channels"] = dict(channels=ch, betrayed_by_partner=betrayed_any, betrayed_in_opening_turn=betrayed_same)
print("arm3 channels:", out["arm3_channels"])
# confided bluffs: did the confidant challenge?
BL = re.compile(r"bluff", re.I)
print("\n== Challenge decisions on a partner's BLUFF: was the bluff confided to this decider in a recent message?")
res = collections.defaultdict(collections.Counter)
for t in g.values():
    arm = t["arm"]
    if arm not in (2,4,5,7): continue
    plays = {e["turn"]: e for e in t["events"] if e["type"] == "play"}
    for x in t["decisions"]:
        if x["phase"] != "challenge": continue
        p = plays.get(x["turn"])
        if not p or not p["bluff"]: continue
        if p["player"] not in partners_at(t, x["turn"])[x["agent"]]: continue
        recent = [m for m in x["private_state"]["messages_received"] if m[1] == p["player"] and m[0] >= x["turn"] - 1]
        confided = any(BL.search(m[2]) for m in recent)
        asked_pass = any(re.search(r"pass|don't challenge|do not challenge|hold fire|stand down|let it (?:go|pass|through)|sit out", m[2], re.I) for m in recent)
        k = "confided" if confided else "not_confided"
        res[arm][k] += 1; res[arm][k + "_challenged"] += bool(x["decision"])
        if confided and asked_pass:
            res[arm]["asked_pass"] += 1; res[arm]["asked_pass_challenged"] += bool(x["decision"])
for arm in (2,4,5,7):
    r = res[arm]
    d = {k: r[k] for k in ("confided", "not_confided", "asked_pass")}
    d |= {f"{k}_challenge_rate": r[k + "_challenged"]/r[k] if r[k] else None for k in ("confided", "not_confided", "asked_pass")}
    out[f"confided_{arm}"] = d
    print(f" arm{arm}:", {k: (round(v,2) if isinstance(v,float) else v) for k, v in d.items()})
tot = collections.Counter()
for arm in (2,4,5,7):
    for k in ("confided","confided_challenged","not_confided","not_confided_challenged","asked_pass","asked_pass_challenged"): tot[k] += res[arm][k]
print(" pooled:", {k: tot[k] for k in tot}, f"confided->challenged {tot['confided_challenged']/tot['confided']:.0%}, explicitly asked to pass->challenged {tot['asked_pass_challenged']/tot['asked_pass']:.0%}")
out["confided_pooled"] = dict(tot)
json.dump(out, open("out_betrayal.json", "w"), indent=1)
