# Provenance: model vs Python

Template inventory: 0 distinct normalised outline lines from 2,000 template outlines.


## Staged route (3B)

| run | status | stages with raw output | attempts | retried stages | 'account_' in raw text | culprit raw had secret deed | facts added by Python | clues changed by Python | other differences |
|---|---|---|---|---|---|---|---|---|---|
| e2_staged__g0__00_s1 | ok | 9 | 9 | 0 | False | False | 1 | 1 | 0 |
| e2_staged__g1__00_s2 | ok | 8 | 8 | 0 | False | False | 1 | 1 | 0 |
| e2_staged__g2__00_s3 | failed | 8 | 8 | 0 | False | None | None | None | None |
| e3_staged_repeat__g0__00_s1 | ok | 9 | 9 | 0 | False | False | 1 | 1 | 0 |

**e2_staged__g0__00_s1**
- Python added fact `account_npc_baker` to npc_baker (did, secret=True): I committed the theft of silver locket at the loc_library. the npc_baker slipped it into a coat pocket while the stall was busy at the loc_library at minute 9.
- Python changed clue `clue_1`: implies changed ['account_npc_baker']

**e2_staged__g1__00_s2**
- Python added fact `account_npc_shepherd` to npc_shepherd (did, secret=True): I committed the theft of brass saffron teapot at the loc_park. the brass saffron teapot was slipped into a coat pocket while the owner was preoccupied at the loc_park at minute 7, by the npc_shepherd.
- Python changed clue `clue_1`: implies changed ['account_npc_shepherd']

**e3_staged_repeat__g0__00_s1**
- Python added fact `account_npc_baker` to npc_baker (did, secret=True): I committed the theft of silver locket at the loc_library. the npc_baker slipped it into a coat pocket while the stall was busy at the loc_library at minute 9.
- Python changed clue `clue_1`: implies changed ['account_npc_baker']
