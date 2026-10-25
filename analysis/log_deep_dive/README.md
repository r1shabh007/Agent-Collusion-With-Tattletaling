# Analysis of secret messages and reasoning traces

These scripts analyse the 9,642 secret messages and 15,795 logged model calls in [`results/run1/`](../../results/run1/). The results are reported in Appendix D of `main.tex`.

The scripts need only the Python standard library. Run them from `outputs/`. Each script writes an `out_*.json` file there, and its printed output is saved as `<script>.txt`:

```bash
cd analysis/log_deep_dive/outputs
for s in a_messages b_honesty b2_announce c_challenges c2_plays d_reasons e_accuse e2_gossip f_dynamics g_betrayal h_stats k_network; do python3 ../$s.py > $s.txt; done
```

On first use, `load.py` builds a local `cache.pkl`, which is not committed. To analyse a different run, set `TATTLETALE_RUN` to its directory.

## How the measures are computed

Each decision is counted once. When a model call had to be retried after an unusable answer, only the final attempt is kept. If an agent received several invitations in one turn, each invitation counts as a separate decision.

Message and reasoning categories come from keyword matches defined in `cats.py`. We checked them by reading samples. They count what a message or trace mentions, which is not necessarily the reason for a decision.

Tests resample whole games, as in the paper.

## Findings

| Appendix | Finding | Main numbers | Script |
|---|---|---|---|
| D.1 | Partners know each other's hands and challenge each other's bluffs. | With channels, 81–92% of bluffs are caught, compared with 58% and 65% in arms 1 and 6. Averaged over games this is 88% against 66% (p = 0.001). Honest plays are challenged 21–25% of the time, against 44% and 40% (over games 26% against 45%, p < 0.001). Of 1,644 messages stating the sender's hand, 96–98% are exact. | `c_challenges.py`, `c2_plays.py`, `h_stats.py`, `b_honesty.py` |
| D.2 | Invitees break the commitment in the invitation. | Invitees who agreed never to challenge the initiator challenged 30 of 39 of the initiator's bluffs (77%). Bluffs the partner had warned about were challenged 83% of the time (206 decisions), against 53% without a warning (47 decisions). Within games the difference is 17 points (p = 0.08, 22 games). | `d_reasons.py`, `g_betrayal.py`, `h_stats.py` |
| D.3 | Refusals mention accusation risk. | In arms 3, 4 and 7, every refusal mentions risk, 8–15% mention fairness, and none mentions fairness without risk. In arm 2, 20% of accepted offers mention fairness. | `d_reasons.py` |
| D.4 | Under bans, channels last one turn. | In 16 of the 17 channels in arm 3, the partner accused in the turn the channel opened. In 13 of these, both partners accused each other. | `g_betrayal.py` |
| D.5 | Under points, accusing a partner always pays. | Mutual accusations started in turn 1 in 6 of 10 games and by turn 3 in all 10. In 4 games they started before any message proposed them. After a one-sided accusation, the victim accused back in the next turn 43% of the time, against 15% otherwise. Number of channels and final score correlate at ρ = 0.63. | `f_dynamics.py`, `k_network.py` |
| D.6 | In arm 7, channels protect against accusations, and outsiders learn about channels from their partners. | 66% of accepted offers say a channel stops a possible accuser. Of 208 accusations against outsiders, 67% followed a received message naming the accused's channels. 58% of the reasons cite messages and 10% cite public play. | `d_reasons.py`, `e2_gossip.py` |
| D.7 | In arm 5, reports name the partner and do not change behaviour. | 0.4% of messages mention accusations. 77% of reports cite the partner's messages. Hand-sharing appears in 27% of a pair's messages before its first report and 29% after. | `e_accuse.py`, `e2_gossip.py`, `k_network.py` |
| D.8 | In arm 6, accusations rely on misleading patterns. | 92% of the 395 accusations, all wrong, cite a pattern in play. | `e_accuse.py` |

## Limits

Agents never see the messages they sent themselves, because each prompt includes only the last eight messages received. When an announced play differs from the actual play (29–50% of cases), we cannot tell lying from forgetting. Finding D.2 is not affected, because it uses messages the deciding agent received.

The commitment in the invitation applies only to invitees. Channels opened by two simultaneous offers include no such text.

Fewer than 1% of decisions in any arm mention being tested or observed (`f_dynamics.py`).

`refs.bib` contains BibTeX entries for the references added to Related Work.
