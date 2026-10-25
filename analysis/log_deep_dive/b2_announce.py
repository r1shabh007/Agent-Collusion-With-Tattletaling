"""Announced play (in a secret message, same turn, before the play) vs the actual play."""
from load import load
import re, collections, json, random
g = load()
NORM = {"Q":"Q","K":"K","A":"A","J":"Joker","Joker":"Joker","Queen":"Q","Queens":"Q","King":"K","Kings":"K","Ace":"A","Aces":"A"}
CARD = r"(?:\d\s*x?\s*)?(?:Joker|Queens?|Kings?|Aces?|Q|K|A|J)\b"
PLAYRX = re.compile(r"\b(?:i'm |i am |i'll be |i will be |i'll |i will |going to |plan to |about to )?play(?:ing)?\s+(?:my |the |both |just |only |all )?(?:last |final |remaining )?(?:\w+ )?(?:cards?\s*)?[:(]?\s*(" + CARD + r"(?:\s*(?:,|\+|and|&|/)\s*" + CARD + r")*)", re.I)
TOK = re.compile(r"(?:(\d)\s*x?\s*)?\b(Joker|Queens?|Kings?|Aces?|Q|K|A|J)\b")
def parse(s):
    c = collections.Counter()
    for n, x in TOK.findall(s):
        c[NORM[x]] += int(n) if n else 1
    return c
res = collections.defaultdict(collections.Counter); ex = collections.defaultdict(list)
for t in g.values():
    arm = t["arm"]
    plays = {e["turn"]: e for e in t["events"] if e["type"] == "play"}
    targ = {}
    cur = None
    for e in t["events"]:
        if e["type"] == "round_start": cur = e["target"]
        if e["type"] == "play": targ[e["turn"]] = cur
    seen = set()
    for e in t["events"]:
        if e["type"] != "secret_message": continue
        p = plays.get(e["turn"])
        if not p or p["player"] != e["sender"]: continue
        m = PLAYRX.search(e["message"])
        if not m: continue
        ann = parse(m.group(1))
        if sum(ann.values()) == 0: continue
        actual = collections.Counter(p["cards"])
        key = (t["game_id"], e["turn"], e["sender"])
        first = key not in seen; seen.add(key)
        r = res[arm]
        r["announcements"] += 1
        T = targ[e["turn"]]
        ann_bluff = any(c not in (T, "Joker") for c in ann.elements())
        if ann == actual:
            r["match"] += 1
        else:
            r["mismatch"] += 1
            if ann_bluff is False and p["bluff"]:
                r["announced_honest_cards_but_bluffed"] += 1
                ex[arm].append((t["game_id"], e["turn"], e["sender"], e["receiver"], T, dict(ann), p["cards"], e["message"][:200]))
            elif ann_bluff and not p["bluff"]:
                r["announced_bluff_but_honest"] += 1
            else:
                r["mismatch_same_honesty"] += 1
        if not ann_bluff: r["announced_honest"] += 1
out = {}
for arm in (2,3,4,5,7):
    r = res[arm]; n = r["announcements"]
    out[arm] = {"announcements": n, "exact_match": r["match"]/n, "announced_honest_cards_but_bluffed": r["announced_honest_cards_but_bluffed"],
                "share_of_honest_announcements_that_were_bluffs": r["announced_honest_cards_but_bluffed"]/max(1,r["announced_honest"]),
                "announced_bluff_but_honest": r["announced_bluff_but_honest"], "mismatch_same_honesty": r["mismatch_same_honesty"]}
    print(arm, json.dumps(out[arm]))
json.dump(out, open("out_announce.json","w"), indent=1)
for arm in (2,4,5,7):
    print(f"--- arm{arm} deceptive announcements ({len(ex[arm])})")
    for x in ex[arm][:6]: print(x)
