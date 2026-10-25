"""Game-clustered tests for the headline new results."""
from load import load, partners_at
import random, re, collections, json, statistics as st
g = load()
def perm(a, b, n=20000, seed=0):
    r = random.Random(seed); obs = abs(st.mean(a) - st.mean(b)); pool = a + b; k = len(a); c = 0
    for _ in range(n):
        r.shuffle(pool)
        if abs(st.mean(pool[:k]) - st.mean(pool[k:])) >= obs - 1e-12: c += 1
    return (c + 1) / (n + 1)
out = {}
# per-game bluff-catch rate and honest-challenge rate
def game_rates(t):
    ch = {e["turn"] for e in t["events"] if e["type"] == "challenge"}
    b = [e["turn"] in ch for e in t["events"] if e["type"] == "play" and e["bluff"]]
    h = [e["turn"] in ch for e in t["events"] if e["type"] == "play" and not e["bluff"]]
    return (st.mean(b) if b else None, st.mean(h) if h else None)
G = {a: [game_rates(t) for t in g.values() if t["arm"] == a] for a in range(1, 8)}
nochan = [x[0] for a in (1, 6) for x in G[a] if x[0] is not None]
chan = [x[0] for a in (2, 4, 5, 7) for x in G[a] if x[0] is not None]
out["bluff_catch_game_mean"] = dict(no_channel=st.mean(nochan), channel=st.mean(chan), p=perm(chan, nochan), n_games=(len(nochan), len(chan)))
nh = [x[1] for a in (1, 6) for x in G[a] if x[1] is not None]; chh = [x[1] for a in (2, 4, 5, 7) for x in G[a] if x[1] is not None]
out["honest_challenged_game_mean"] = dict(no_channel=st.mean(nh), channel=st.mean(chh), p=perm(chh, nh))
# confided bluffs: per-game difference (games with both kinds)
BL = re.compile(r"bluff", re.I)
diffs = []; conf_rates = []
for t in g.values():
    if t["arm"] not in (2, 4, 5, 7): continue
    plays = {e["turn"]: e for e in t["events"] if e["type"] == "play"}
    c = collections.defaultdict(list)
    for x in t["decisions"]:
        if x["phase"] != "challenge": continue
        p = plays.get(x["turn"])
        if not p or not p["bluff"] or p["player"] not in partners_at(t, x["turn"])[x["agent"]]: continue
        recent = [m for m in x["private_state"]["messages_received"] if m[1] == p["player"] and m[0] >= x["turn"] - 1]
        c[any(BL.search(m[2]) for m in recent)].append(bool(x["decision"]))
    if c[True]: conf_rates.append(st.mean(c[True]))
    if c[True] and c[False]: diffs.append(st.mean(c[True]) - st.mean(c[False]))
# sign-flip permutation test on per-game differences
r = random.Random(0); obs = st.mean(diffs); cnt = 0
for _ in range(20000):
    if abs(st.mean([d * r.choice((1, -1)) for d in diffs])) >= abs(obs) - 1e-12: cnt += 1
out["confided_vs_not"] = dict(games_with_both=len(diffs), mean_within_game_diff=obs, p_signflip=(cnt + 1) / 20001, games_with_confided=len(conf_rates), mean_game_confided_challenge_rate=st.mean(conf_rates))
for k, v in out.items(): print(k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()})
json.dump(out, open("out_stats.json", "w"), indent=1)
