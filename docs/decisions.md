# Decision & Deferred-Task Log

A running record of the design decisions we've locked in and the things we've
consciously postponed. Update this whenever a decision is made or a deferred
item is resolved, so nothing gets lost between phases.

## Finalized inclusion filters

A show is included in the analysis dataset if **all** of the following hold:

| Rule | Value |
|------|-------|
| `titleType` | `tvSeries` or `tvMiniSeries` |
| Minimum episodes (with a rating) | >= 13 |
| Minimum seasons | >= 2 |
| Minimum mean votes per episode | >= 50 |
| Excluded genres | any of Game-Show, Reality-TV, Talk-Show, News |
| Documentary special case | Documentary-tagged is kept only if episode count < 100 |

Rationale, in short:
- **>= 13 episodes**: enough length to talk about a trajectory.
- **>= 2 seasons**: a decline "across seasons" needs at least two seasons to
  compare (e.g. Sherlock has only 15 episodes but 4 seasons, so it stays; the
  single-season anime giants like One Piece / Naruto are dropped).
- **mean votes/episode >= 50**: cuts statistical noise from barely-voted shows
  without narrowing all the way down to only the mega-popular ones.
- **Genre exclusions**: "decline" is a narrative concept; game shows, reality
  TV, talk shows and news have no season-to-season story arc to decline.
- **Documentary < 100 episodes**: separates season-based story documentaries
  (Chef's Table, Drive to Survive, Cheer) from anthology/magazine strands
  (Nova, Frontline, Biography). Platform-independent — we have no channel/
  platform field in the data, so the rule applies equally to every documentary.

## Deferred tasks (do not forget)

1. **Per-episode vote noise → handled at ANALYSIS stage, not in build.**
   Keep `numVotes` per episode in the processed table; address low-vote noisy
   episodes in Phase 2/3 by **weighting** episode ratings by `numVotes` rather
   than a hard per-episode vote cutoff. Not yet implemented.

2. **Ongoing shows (`endYear` empty) → flag, don't drop.**
   Add an `ongoing` boolean in build. Keep these shows for descriptive/general
   analysis, but **exclude** them from the "final season curse" analysis (a show
   that hasn't ended has no real final season). Spot-check showed empty endYear
   is mostly genuinely-still-airing shows, so we accepted the proxy — but the
   exclusion in the final-season analysis still has to be applied later.

3. **Episode-level air-year precision (optional refinement).**
   For a more precise "still active" signal we could pull each show's latest
   episode air year from the `tvEpisode` rows in title.basics (currently unused;
   we only use the tvSeries rows). Deferred; only do it if the endYear proxy
   proves insufficient.

4. **Shows with missing `genres` — edge case.**
   Series with empty genres currently pass all exclusion rules by default.
   Check the count in build and decide whether to keep or drop them.

## Language convention

All code, comments, function/variable names, filenames and figure labels are in
**English**. Turkish is used only for discussion and (optionally) the final blog
narrative.
