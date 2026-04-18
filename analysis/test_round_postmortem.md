# DatsSol Test-Round Postmortem

## Exported artifacts

- Successful accepted commands by round: `/Users/maksimmamchur/Documents/Projects/DatsSol/analysis/successful_moves_by_round.csv`
- Per-round command counts: `/Users/maksimmamchur/Documents/Projects/DatsSol/analysis/successful_moves_by_round_summary.json`
- Aggregated postmortem data: `/Users/maksimmamchur/Documents/Projects/DatsSol/analysis/test_round_postmortem_data.json`
- Test leaderboard comparison snapshot: `/Users/maksimmamchur/Documents/Projects/DatsSol/analysis/test_leaderboard_comparison.json`

## Rules that matter most for score

- Terraforming is the main baseline economy.
  - Ordinary cell: 1000 max score total, 10 points per 1%.
  - Boosted cell (`x % 7 == 0 && y % 7 == 0`): 1500 max score total, 15 points per 1%.
  - A default plantation with `TS=5` earns only `50` points per turn on a normal cell and disappears after finishing the tile.
- Destroying a beaver lair is a large spike EV:
  - reward is `20x` the score of the cell, i.e. `20,000` on a normal cell or `30,000` on a boosted cell,
  - and the tile remains terraformable afterwards.
- Sabotage also scores, but only if we can actually reach and finish enemy plantations.
- Losing HQ is catastrophic:
  - all plantations are destroyed,
  - score penalty is `5%` of current score,
  - upgrades remain.
- Isolated plantations do not score, but the top teams still accumulate many of them, which is evidence of aggressive rolling expansion rather than a sign that isolation itself is good.

## What the data says

- We recorded `109` test/final round results in the DB.
- Median `terraformingScore` per round: `1,500`.
- Best round `terraformingScore`: `29,640`.
- Total accepted commands matched back to rounds: `32,638` across `84` rounds.
- Total accepted upgrade commands: `1,365`.
- Total accepted `relocateMain`: `1,221`.

This means the main problem was no longer "the bot did nothing". It submitted plenty of accepted commands. The problem was command quality and network shape.

## Why we lost to the leaders

- Our total test score was `2,020,889`, while top 1 had `83,778,366`.
- We had `2,871` HQ deaths total. Top 1 had `526`.
- We had `0` beaver lairs destroyed. Top 1 had `138`, top 2 had `931`, top 3 had `201`.
- We had `0` enemy plantations destroyed and `0` kills total.
- We had only `50` plantations lost to isolation. Top 1 had `10,844`.

The profile is clear:

1. We died too often.
   - Our historical DB median is low because late fixes helped, but the cumulative test stats still show that earlier strategy versions repeatedly reset the colony.
   - Even our best terraforming rounds still came with `13-28` deaths.

2. We never built a real rolling carpet.
   - Recent round archives repeatedly showed `max_connected <= 2`.
   - We often had hundreds of accepted submits in a round but still never left the compact `1 -> 2` state.

3. We under-expanded relative to the rules.
   - Top teams convert score by keeping many plantations active across many cells.
   - Our planner spent too long preserving a perfect HQ shell instead of turning the first safe handoff into `2 -> 3 -> 4` network growth.

4. We never monetized beavers.
   - Because we rarely stabilized a `5+` node economy, the beaver logic almost never even became relevant.
   - This is a secondary gap, but it compounds the main terraforming deficit.

5. We were too clean.
   - Top teams tolerate churn: many isolated/lost plantations, storm damage, and old leaves dropping off.
   - Our tiny isolation count is not a virtue here. It mostly means we never had enough breadth to shed old structure while moving the productive core forward.

## Strategic conclusion

The old planner was biased toward "do not risk the HQ" and accidentally serialized the entire opening around that rule. That made sense for transport-hardening, but it is not competitive for score.

The core shift needed for finals is:

- keep the HQ safe enough to avoid resets,
- but after the first safe adjacent handoff exists, immediately unlock parallel construction again,
- convert `2 -> 3 -> 4` before worrying about perfect redundancy or beaver farming.

## Implemented strategy change

Planner change in `/Users/maksimmamchur/Documents/Projects/DatsSol/backend/app/planning/decide.py`:

- `strict_anchor_mode` now stays strict only until there is at least one real safe live HQ anchor,
- once that first safe handoff anchor exists, the planner can continue opening follow-up builds instead of serializing behind a single HQ-route construction,
- construction caps are now wider for small-but-stable cores:
  - `connected == 1`: still single-threaded,
  - `connected == 2` with one safe handoff anchor: may keep `2` constructions,
  - `connected <= 4`: may grow to `3`,
  - `connected <= 7`: may grow to `4`.

This is the first strategy patch in this cycle that explicitly targets score throughput instead of only HQ survival.

