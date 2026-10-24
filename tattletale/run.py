#!/usr/bin/env python3
"""
Run the experiment: one batch of N games per arm.

    python -m tattletale.run --arms 1 2 3 4 5 6 --games 10 --out results/run1

All games are independent (agents have no cross-game memory, and channels and bans last one game), so all of
them run concurrently. Rerunning the same command skips games that already have a transcript.

Output per game: <out>/arm<k>/<game_id>/transcript.json and <out>/arm<k>/<game_id>/cot/<agent>.jsonl.
Across games: <out>/games.csv (one row per agent per game) and <out>/progress.json.
"""

import argparse
import csv
import json
import os
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from tattletale.game import NAMES, Game

CSV_FIELDS = ["arm", "game_id", "game", "agent", "played", "score", "winner", "last_survivor", "removed",
              "offers_made", "offers_accepted_by_partner", "invitations_accepted", "channels_opened",
              "plays", "bluffs", "challenges", "accusations", "accusations_correct", "times_accused",
              "llm_calls", "fallbacks", "prompt_tokens", "completion_tokens", "rounds", "turns",
              "hit_round_cap", "error"]


class Runner:
    def __init__(self, llm, out: str, games: int, seed: int):
        self.llm, self.out, self.games, self.seed = llm, out, games, seed
        self.lock = threading.Lock()
        self.started = time.time()
        self.done = {}
        self.tokens = 0
        os.makedirs(out, exist_ok=True)
        self.csv_path = os.path.join(out, "games.csv")
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="") as f:
                csv.DictWriter(f, fieldnames=CSV_FIELDS).writeheader()

    def play(self, arm: int, n: int) -> None:
        game_id = f"arm{arm}-g{n:02d}"
        game_dir = os.path.join(self.out, f"arm{arm}", game_id)
        if os.path.exists(os.path.join(game_dir, "transcript.json")):
            return                                                  # resume: already played
        error, result = "", None
        game = Game(arm, game_id, self.llm, game_dir, seed=self.seed + 1000 * arm + n)
        try:
            result = game.play()
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            traceback.print_exc()
            with open(os.path.join(game_dir, "error.txt"), "w") as f:
                f.write(traceback.format_exc())
        with self.lock:
            with open(self.csv_path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                for name in NAMES:
                    played = name in game.stats
                    s = game.stats.get(name, {})
                    row = {"arm": arm, "game_id": game_id, "game": n, "agent": name, "played": int(played),
                           "error": error}
                    if played:
                        row.update({k: s.get(k, "") for k in CSV_FIELDS if k in s})
                        if result:
                            row.update(score=result["final_scores"][name], winner=int(name in result["winners"]),
                                       last_survivor=int(name == result["last_survivor"]),
                                       rounds=result["rounds"], turns=result["turns"],
                                       hit_round_cap=int(result["hit_round_cap"]))
                    writer.writerow(row)
                    self.tokens += s.get("prompt_tokens", 0) + s.get("completion_tokens", 0) if played else 0
            self.done.setdefault(arm, 0)
            self.done[arm] += 1
            with open(os.path.join(self.out, "progress.json"), "w") as f:
                json.dump({"games_done_per_arm": self.done, "games_per_arm": self.games,
                           "elapsed_min": round((time.time() - self.started) / 60, 1),
                           "total_tokens": self.tokens}, f, indent=1)
        print(f"[done] {game_id} {'ERROR ' + error if error else result['final_scores']}", flush=True)


def main() -> None:
    from tattletale.llm import LLM

    parser = argparse.ArgumentParser(description="Augmented Liar's Bar whistleblowing experiment")
    parser.add_argument("--arms", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6])
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--out", default="results/run1")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--max-parallel-games", type=int, default=64)
    args = parser.parse_args()

    runner = Runner(LLM(), args.out, args.games, args.seed)
    with ThreadPoolExecutor(max_workers=args.max_parallel_games) as pool:
        futures = [pool.submit(runner.play, arm, n) for arm in args.arms for n in range(1, args.games + 1)]
        for f in futures:
            f.result()
    print(f"ALL DONE in {round((time.time() - runner.started) / 60, 1)} min", flush=True)


if __name__ == "__main__":
    main()
