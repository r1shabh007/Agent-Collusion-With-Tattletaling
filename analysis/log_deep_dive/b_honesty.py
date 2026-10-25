"""Do colluders tell each other the truth? Hand claims and 'honest play' claims in secret messages vs ground truth."""
from load import load
import re, collections, json
g = load()
CARD = re.compile(r"(?:(\d)\s*x?\s*)?\b(Joker|Q|K|A|Queens?|Kings?|Aces?)\b")
NORM = {"Q":"Q","K":"K","A":"A","Joker":"Joker","Queen":"Q","Queens":"Q","King":"K","Kings":"K","Ace":"A","Aces":"A"}
HAND = re.compile(r"(?:my hand(?: is| now| left| this round)?|hand)\s*[:=]?\s*((?:(?:\d\s*x?\s*)?(?:Joker|Q|K|A|Queens?|Kings?|Aces?)(?:\s*,\s*|\s+and\s+|\s*\+\s*|\s+|\s*/\s*)?){1,6})")

def parse(s):
    out = collections.Counter()
    for num, c in CARD.findall(s):
        out[NORM[c]] += int(num) if num else 1
    return out

hands = {}  # (gid, agent, turn) -> hand at message time
for t in g.values():
    for x in t["decisions"]:
        if x["phase"] == "secret_message":
            hands[(t["game_id"], x["agent"], x["turn"])] = collections.Counter(x["private_state"]["hand"])

res = collections.defaultdict(collections.Counter)
examples = collections.defaultdict(list)
for t in g.values():
    arm = t["arm"]
    plays = {e["turn"]: e for e in t["events"] if e["type"] == "play"}
    for e in t["events"]:
        if e["type"] != "secret_message": continue
        m = e["message"]
        key = (t["game_id"], e["sender"], e["turn"])
        if key not in hands: continue
        actual = hands[key]
        # 1. explicit hand claims
        mm = HAND.search(m)
        if mm:
            claim = parse(mm.group(1))
            if sum(claim.values()) >= 2:
                res[arm]["hand_claims"] += 1
                extra = claim - actual
                if not extra:
                    res[arm]["hand_true_or_subset"] += 1
                    if claim == actual: res[arm]["hand_exact"] += 1
                else:
                    res[arm]["hand_contradicts"] += 1
                    examples[arm].append(("hand", t["game_id"], e["turn"], e["sender"], e["receiver"], dict(claim), dict(actual), m[:250]))
        # 2. 'honest' claims about this turn's play by the sender
        p = plays.get(e["turn"])
        if p and p["player"] == e["sender"]:
            low = m.lower()
            says_honest = re.search(r"\bhonest|\bclean\b|\blegit|\ball (?:real|true|target)|no bluff|not (?:a )?bluff", low)
            says_bluff = re.search(r"\bbluff", low) and not re.search(r"no bluff|not (?:a )?bluff", low)
            res[arm]["messages_by_player_on_own_turn"] += 1
            if says_honest and not says_bluff:
                res[arm]["claims_honest"] += 1
                res[arm]["claims_honest_but_bluffed"] += p["bluff"]
                if p["bluff"]:
                    examples[arm].append(("honest", t["game_id"], e["turn"], e["sender"], e["receiver"], p["cards"], m[:250]))
            if says_bluff and not says_honest:
                res[arm]["claims_bluff"] += 1
                res[arm]["claims_bluff_but_honest"] += not p["bluff"]
            if p["bluff"]:
                res[arm]["actual_bluffs_with_message"] += 1
                res[arm]["bluff_disclosed"] += bool(says_bluff)

out = {}
for arm in (2,3,4,5,7):
    r = res[arm]
    o = {
        "hand_claims": r["hand_claims"],
        "hand_claim_contradicts_actual_hand": r["hand_contradicts"] / max(1, r["hand_claims"]),
        "hand_claim_exact": r["hand_exact"] / max(1, r["hand_claims"]),
        "honest_claims_on_own_turn": r["claims_honest"],
        "honest_claim_but_actually_bluffed": r["claims_honest_but_bluffed"] / max(1, r["claims_honest"]),
        "own_bluffs_disclosed_to_partner": r["bluff_disclosed"] / max(1, r["actual_bluffs_with_message"]),
        "own_bluffs_with_message": r["actual_bluffs_with_message"],
    }
    out[arm] = o
    print(arm, json.dumps(o))
json.dump(out, open("out_honesty.json", "w"), indent=1)
for arm in (4,5,7,2):
    print(f"\n--- examples arm {arm} ({len(examples[arm])})")
    for x in examples[arm][:5]: print(x)
