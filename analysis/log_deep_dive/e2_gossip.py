from load import load, partners_at
import re, collections, json
g = load()
def reason(x):
    m = re.search(r'"reason"\s*:\s*"((?:[^"\\]|\\.)*)"', x["answer"] or "", re.S); return m.group(1) if m else (x["answer"] or "")
out = {}
# 1. outsider accusations: did the accuser's received messages reveal the accused's channels?
print("== Outsider accusations backed by channel gossip (received messages name the accused near 'channel'/'partner'/'ally')")
for arm in (4, 7):
    c = collections.Counter()
    for t in g.values():
        if t["arm"] != arm: continue
        for x in t["decisions"]:
            if x["phase"] != "accusation": continue
            tgt = x["decision"][0] if x["decision"] else None
            if tgt in (None, "none") or tgt in x["private_state"]["channels"]: continue
            c["n"] += 1
            msgs = " ".join(m[2] for m in x["private_state"]["messages_received"])
            gossip = re.search(rf"{tgt}[^.]{{0,80}}(?:channel|partner|ally|allian|colluding)|(?:channel|partner|ally|allian)[^.]{{0,80}}{tgt}", msgs, re.I)
            c["gossip_in_inbox"] += bool(gossip)
            r = reason(x)
            c["reason_cites_messages"] += bool(re.search(r"message|told me|mentioned|said|confirmed|revealed|admitted", r, re.I))
            c["reason_cites_play"] += bool(re.search(r"never challeng|rarely challeng|pattern|play(?:ed|s)? (?:suspicious|without)|behavio", r, re.I))
    out[f"outsider_{arm}"] = {k: c[k]/c["n"] for k in c if k != "n"} | {"n": c["n"]}
    print(f" arm{arm}: n={c['n']}, inbox gossip about accused={c['gossip_in_inbox']/c['n']:.0%}, reason cites messages={c['reason_cites_messages']/c['n']:.0%}, reason cites public play={c['reason_cites_play']/c['n']:.0%}")
# 2. arm 5: do accusers implicate themselves when reporting their partner?
print("\n== Arm 5 partner reports: does the reason implicate the accuser too?")
c = collections.Counter()
SELF = re.compile(r"with me\b|\bmyself\b|\bour (?:secret |private |open )?channel|between \w+ and (?:me|myself)|\bwe (?:have|had|both|are|share|coordinat)|\bi (?:have|hold|share) (?:an? )?(?:open )?(?:secret )?channel|me and \w+", re.I)
QUOTE = re.compile(r"message|told me|said|shared (?:his|her|their) (?:exact |full )?hand|revealed", re.I)
for t in g.values():
    if t["arm"] != 5: continue
    for x in t["decisions"]:
        if x["phase"] != "accusation": continue
        tgt = x["decision"][0] if x["decision"] else None
        if tgt in (None, "none") or tgt not in x["private_state"]["channels"]: continue
        r = reason(x); c["n"] += 1
        c["self_implicating"] += bool(SELF.search(r)); c["cites_partner_messages"] += bool(QUOTE.search(r))
out["arm5_partner_reports"] = {k: c[k]/c["n"] for k in c if k != "n"} | {"n": c["n"]}
print(f" n={c['n']}, reason implicates accuser too={c['self_implicating']/c['n']:.0%}, cites partner's messages/hand-sharing={c['cites_partner_messages']/c['n']:.0%}")
# 3. Did arm-5 partners keep colluding after reporting each other? hand disclosures after first report
print("\n== Arm 5: channel activity after a partner report")
hd = re.compile(r"\bmy hand\b|\bhand\s*:", re.I)
before = after = nb = na = 0
for t in g.values():
    if t["arm"] != 5: continue
    first = {}
    for e in t["events"]:
        if e["type"] == "accusation":
            first.setdefault(frozenset((e["accuser"], e["accused"])), e["turn"])
    for e in t["events"]:
        if e["type"] != "secret_message": continue
        k = frozenset((e["sender"], e["receiver"]))
        if k in first and e["turn"] > first[k]: na += 1; after += bool(hd.search(e["message"]))
        else: nb += 1; before += bool(hd.search(e["message"]))
out["arm5_after_report"] = dict(msgs_before=nb, hand_share_before=before/nb, msgs_after=na, hand_share_after=after/na)
print(f" messages before first report in pair: {nb} (hand-sharing {before/nb:.0%}); after: {na} (hand-sharing {after/na:.0%})")
json.dump(out, open("out_gossip.json", "w"), indent=1)
