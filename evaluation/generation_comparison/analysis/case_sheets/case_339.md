# Case 339

**Title:** The Stolen leather ledger  
**Town:** Littleford

> A theft of silver locket disrupts the quiet routine of the town.

## Places
- Reading House (library) — Shelves floor to ceiling and the smell of old paper. Connects to: Copper Kettle Cafe
- Copper Kettle Cafe (cafe) — Small tables, strong tea, and the town's rumour mill. Connects to: Reading House, Riverside Market
- Riverside Market (market) — A busy square of stalls and shouting vendors. Connects to: Copper Kettle Cafe, Reading House, Town Parking Lot
- Town Parking Lot (parking) — Rows of empty spaces, a cart or two, and cracked paint. Connects to: Riverside Market, Reading House

## Hidden truth
- Crime: theft of **leather ledger** at Reading House, minutes 6–8
- Culprit: **Lena**
- Method: Lifted it off the counter when the vendor turned away.
- Motive: Prove they were smarter than the market folk.
- How: Lena lifted it off the counter when the vendor turned away at the Reading House at minute 7 — the leather ledger is gone.
- Why: They did it to prove they were smarter than the market folk.

### Timeline
- minute 0: Piotr at Town Parking Lot — Was seen going about their day.
- minute 6: Lena at Reading House — prepares covert equipment
- minute 7: Lena at Reading House — commits theft using lifted it off the counter when the vendor turned away
- minute 7: Omar at Copper Kettle Cafe — working at counter
- minute 8: Mira at Riverside Market — notices hurried footsteps
- minute 8: Gus at Town Parking Lot — Was seen going about their day.

### Red herrings
- Omar: They secretly spreads a rumour about the herbalist.

## Clues
- at Reading House, examine: At the Reading House, a physical trace: theft trace.  
  → points to: Lena: "I lifted it off the counter when the vendor turned away at the Reading House during minute 7."
- at Copper Kettle Cafe, npc_reveal (revealed by Mira): Mira saw Omar at the Copper Kettle Cafe at minute 7, and a ledger agrees.  
  → points to: Omar: "I spent that stretch of the day at the Copper Kettle Cafe, plain as that."
- at Riverside Market, npc_reveal (revealed by Omar): Omar saw Mira at the Riverside Market at minute 7, and a ledger agrees.  
  → points to: Mira: "I was at the Riverside Market around that time, ask anyone."
- at Town Parking Lot, npc_reveal (revealed by Omar): Omar saw Gus at the Town Parking Lot at minute 7, and a ledger agrees.  
  → points to: Gus: "I spent that stretch of the day at the Town Parking Lot, plain as that."
- at Town Parking Lot, npc_reveal (revealed by Omar): Omar saw Piotr at the Town Parking Lot at minute 7, and a ledger agrees.  
  → points to: Piotr: "I spent that stretch of the day at the Town Parking Lot, plain as that."
- at Reading House, npc_reveal (revealed by Omar): Omar recalls a document detail: hidden record.  
  → points to: Lena: "I lifted it off the counter when the vendor turned away at the Reading House during minute 7."

## Characters

### Lena
```
{
 "name": "Lena",
 "age": 60,
 "role": "market vendor",
 "traits": [
  "sly",
  "observant"
 ],
 "speech_style": "formal and precise",
 "backstory": "Inherited their trade from a relative in Littleford.",
 "goals": [
  "keep the truth about prove they were smarter than the market folk hidden",
  "protect their reputation"
 ],
 "relationships": {
  "npc_02": "rival"
 },
 "attitude_to_player": "wary of strangers"
}
```
Memory:
- [did, lie, secret] I lifted it off the counter when the vendor turned away at the Reading House during minute 7. (Reading House, minute 7)
- [did, hide, secret] What I did, I did to prove they were smarter than the market folk. (Reading House, minute 7)
- [did, hide, secret] My footprints are probably still in the dust by the Reading House. (Reading House, minute 7)
- [heard, if_asked] I spent minute 7 at the Copper Kettle Cafe, with witnesses. (Copper Kettle Cafe, minute 7)
- cover story: {"id": "npc_01_cover", "claim": "I was at the Copper Kettle Cafe all along; I never went near the Reading House.", "supporting_facts": ["npc_01_alibi_claim"]}

### Omar
```
{
 "name": "Omar",
 "age": 60,
 "role": "coach driver",
 "traits": [
  "earnest",
  "chatty"
 ],
 "speech_style": "warm but rambling",
 "backstory": "Inherited their trade from a relative in Littleford.",
 "goals": [
  "help the town",
  "stay out of other people's business"
 ],
 "relationships": {
  "npc_01": "employer"
 },
 "attitude_to_player": "wary of strangers"
}
```
Memory:
- [witnessed, volunteer] I spent that stretch of the day at the Copper Kettle Cafe, plain as that. (Copper Kettle Cafe, minute 7)
- [heard, if_asked] I was near the Reading House and heard raised voices that stopped suddenly. (Reading House, minute 7)
- [heard, hide, secret] They secretly hid a stack of overdue library books at home. (Copper Kettle Cafe, recently)

### Mira
```
{
 "name": "Mira",
 "age": 26,
 "role": "fishmonger",
 "traits": [
  "guarded",
  "chatty"
 ],
 "speech_style": "warm but rambling",
 "backstory": "Inherited their trade from a relative in Littleford.",
 "goals": [
  "prove someone a wrongdoer wrong",
  "stay out of other people's business"
 ],
 "relationships": {
  "npc_01": "employer"
 },
 "attitude_to_player": "polite but guarded"
}
```
Memory:
- [witnessed, volunteer] I was at the Riverside Market around that time, ask anyone. (Riverside Market, minute 7)
- [heard, if_asked] I passed the Reading House and noticed something felt wrong, though I cannot say what. (Reading House, minute 7)

### Gus
```
{
 "name": "Gus",
 "age": 23,
 "role": "tea-house keeper",
 "traits": [
  "impatient",
  "observant"
 ],
 "speech_style": "short, direct sentences",
 "backstory": "Came to Littleford a few years ago and stayed for the quiet.",
 "goals": [
  "stay out of other people's business",
  "help the town"
 ],
 "relationships": {
  "npc_01": "friend"
 },
 "attitude_to_player": "wary of strangers"
}
```
Memory:
- [witnessed, volunteer] I spent that stretch of the day at the Town Parking Lot, plain as that. (Town Parking Lot, minute 7)
- [heard, if_asked] I was near the Reading House and heard raised voices that stopped suddenly. (Reading House, minute 7)

### Piotr
```
{
 "name": "Piotr",
 "age": 27,
 "role": "librarian",
 "traits": [
  "sly",
  "stubborn"
 ],
 "speech_style": "warm but rambling",
 "backstory": "Inherited their trade from a relative in Littleford.",
 "goals": [
  "stay out of other people's business",
  "prove someone a wrongdoer wrong"
 ],
 "relationships": {
  "npc_01": "employer"
 },
 "attitude_to_player": "polite but guarded"
}
```
Memory:
- [witnessed, volunteer] I spent that stretch of the day at the Town Parking Lot, plain as that. (Town Parking Lot, minute 7)
- [heard, if_asked] I was near the Reading House and heard raised voices that stopped suddenly. (Reading House, minute 7)
