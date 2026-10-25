#!/usr/bin/env python3
"""
Dry run of all arms with a scripted stand-in for the model (no server needed).

    python -m tests.test_stub

Checks that every arm finishes its games, writes a transcript and per-agent CoT logs, and applies each
arm's rules (no channels in arms 1 and 6, no accusations in arms 1 and 2, bans only in arm 3 and only within a game,
accusation correctness matches the README condition).
"""

import json
import os
import random
import re
import shutil
import tempfile

from tattletale.game import ARMS, NAMES
from tattletale.llm import Reply
from tattletale.run import Runner
from tattletale.summarize import main as summarize


class FakeLLM:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def chat(self, prompt: str) -> Reply:
        r = self.rng
        if "Respond only with: (1) ACCEPT or REFUSE" in prompt:
            names = re.findall(r"Available partners: (.+)\.", prompt)[-1].split(", ")
            text = f"ACCEPT\nPARTNER: {names[0]}" if r.random() < 0.5 else "REFUSE"
        elif "=== ALLIANCE INVITATION ===" in prompt:
            text = "ACCEPT" if r.random() < 0.7 else "REFUSE"
        elif "=== SECRET CHANNEL ===" in prompt:
            partners = re.findall(r"open secret channels with: (.+)\. Nobody", prompt)[-1].split(", ")
            text = json.dumps({p: "hi" for p in partners})
        elif "It is your turn to play" in prompt:
            hand = re.findall(r"Your hand: (.+)\.", prompt)[-1].split(", ")
            text = json.dumps({"played_cards": hand[:r.randint(1, min(3, len(hand)))], "reason": "stub"})
        elif "Do you challenge this play?" in prompt:
            text = json.dumps({"challenge": r.random() < 0.35, "reason": "stub"})
        elif "=== COLLUSION ACCUSATION ===" in prompt:
            names = re.findall(r"Players you can accuse: (.+)\.", prompt)[-1].split(", ")
            text = json.dumps({"accuse": r.choice(names + [None] * 6), "reason": "stub"})
        else:
            text = "?"
        return Reply(text, "stub reasoning", 100, 20, "stop", 0.0)


def main() -> None:
    out = tempfile.mkdtemp(prefix="tattletale_stub_")
    try:
        runner = Runner(FakeLLM(), out, games=3, seed=7)
        for arm in ARMS:
            for n in range(1, 4):
                runner.play(arm, n)
        summarize(out)

        for arm, cfg in ARMS.items():
            for game_dir in sorted(os.listdir(os.path.join(out, f"arm{arm}"))):
                d = os.path.join(out, f"arm{arm}", game_dir)
                assert not os.path.exists(os.path.join(d, "error.txt")), open(os.path.join(d, "error.txt")).read()
                t = json.load(open(os.path.join(d, "transcript.json")))
                kinds = {e["type"] for e in t["events"]}
                assert {"round_start", "play", "game_end"} <= kinds, kinds
                for name in t["players"]:
                    assert os.path.exists(os.path.join(d, "cot", f"{name}.jsonl")), (d, name)
                if not cfg["channel"]:
                    assert not t["channels"] and "offer_decision" not in kinds
                if cfg["accuse"] is None:
                    assert "accusation" not in kinds
                if cfg["accuse"] != "ban":
                    assert "banned" not in kinds
                assert t["players"] == NAMES                     # bans never carry into the next game
                for e in t["events"]:
                    if e["type"] == "accusation_phase":
                        phase = e
                    if e["type"] == "accusation":
                        assert e["correct"] == (e["accused"] in phase["colluding"])
                        if arm == 6:
                            assert not e["correct"]
                if cfg.get("no_partner_accusations"):
                    for name in t["players"]:
                        for line in open(os.path.join(d, "cot", f"{name}.jsonl")):
                            x = json.loads(line)
                            if x["phase"] == "accusation" and x["decision"][0] != "none":
                                assert x["decision"][0] not in x["private_state"]["channels"], x
        print(f"\nSTUB TEST PASSED ({out})")
    finally:
        shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    main()
