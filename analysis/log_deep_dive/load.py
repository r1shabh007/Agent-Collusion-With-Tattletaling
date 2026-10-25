"""Shared loader for the deep analysis of results/run1 (transcripts + per-agent CoT logs)."""
import glob, json, os, collections, pickle

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.environ.get("TATTLETALE_RUN", os.path.join(HERE, "..", "..", "results", "run1"))
CACHE = os.path.join(HERE, "cache.pkl")  # local cache, not committed


def load():
    if os.path.exists(CACHE):
        return pickle.load(open(CACHE, "rb"))
    games = {}
    for tp in sorted(glob.glob(os.path.join(RUN, "arm*", "*", "transcript.json"))):
        t = json.load(open(tp))
        gid = t["game_id"]
        calls = []
        for cp in glob.glob(os.path.join(os.path.dirname(tp), "cot", "*.jsonl")):
            for line in open(cp):
                calls.append(json.loads(line))
        # keep the final attempt of each decision. Several invitations to one agent in one turn share
        # (agent, turn, phase); they are separate decisions, each starting at attempt 0.
        calls.sort(key=lambda x: (x["agent"], x["turn"], x["phase"]))
        final = []
        groups = collections.defaultdict(list)
        for x in calls:
            groups[(x["agent"], x["turn"], x["phase"])].append(x)
        for key, L in groups.items():
            # split into decisions: a new decision starts at each attempt==0
            cur = []
            decs = []
            for x in L:  # file order is preserved within an agent file
                if x["attempt"] == 0 and cur:
                    decs.append(cur); cur = []
                cur.append(x)
            if cur:
                decs.append(cur)
            for d in decs:
                final.append(d[-1])
        t["calls"] = calls
        t["decisions"] = final
        games[gid] = t
    pickle.dump(games, open(CACHE, "wb"))
    return games


def partners_at(t, turn, inclusive=True):
    """channel partners per agent for channels opened up to `turn` (inclusive)."""
    P = collections.defaultdict(set)
    for e in t["events"]:
        if e["type"] == "channel_opened" and (e["turn"] <= turn if inclusive else e["turn"] < turn):
            a, b = e["members"]
            P[a].add(b); P[b].add(a)
    return P


def first_channel_turn(t):
    out = {}
    for e in t["events"]:
        if e["type"] == "channel_opened":
            k = frozenset(e["members"])
            out.setdefault(k, e["turn"])
    return out
