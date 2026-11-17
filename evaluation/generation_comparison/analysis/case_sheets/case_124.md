# Case 124

**Title:** The Stolen silver money bowl  
**Town:** Coldharbor

> A theft of brass pocket watch disrupts the quiet routine of the town.

## Places
- Elder Park (park) — A green square with benches and a tired old tree. Connects to: Old Library
- Old Library (library) — A quiet hall where whispers feel loud. Connects to: Elder Park, Little Cafe
- Little Cafe (cafe) — Warm light and the clink of cups. Connects to: Old Library, Elder Park, Saffron Market
- Saffron Market (market) — A busy square of stalls and shouting vendors. Connects to: Little Cafe, Elder Park

## Hidden truth
- Crime: theft of **silver money bowl** at Elder Park, minutes 5–7
- Culprit: **Lena**
- Method: Traded it with a box of tea and came back for it.
- Motive: Cover a loss they were blamed for.
- How: Lena traded it with a box of tea and came back for it at the Elder Park at minute 6 — the silver money bowl is gone.
- Why: They did it to cover a loss they were blamed for.

### Timeline
- minute 3: Dario at Old Library — Was seen going about their day.
- minute 5: Lena at Old Library — prepares covert equipment
- minute 6: Lena at Elder Park — commits theft using traded it with a box of tea and came back for it
- minute 6: Hana at Little Cafe — working at counter
- minute 6: Piotr at Old Library — Was seen going about their day.
- minute 7: Elsie at Saffron Market — notices hurried footsteps

### Red herrings
- Hana: They secretly spreads a rumour about the herbalist.

## Clues
- at Elder Park, examine: At the Elder Park, a physical trace: theft trace.  
  → points to: Lena: "I traded it with a box of tea and came back for it at the Elder Park during minute 6."
- at Little Cafe, npc_reveal (revealed by Elsie): Elsie saw Hana at the Little Cafe at minute 6, and a ledger agrees.  
  → points to: Hana: "I spent that stretch of the day at the Little Cafe, plain as that."
- at Saffron Market, npc_reveal (revealed by Hana): Hana saw Elsie at the Saffron Market at minute 6, and a ledger agrees.  
  → points to: Elsie: "I was at the Saffron Market around that time, ask anyone."
- at Old Library, npc_reveal (revealed by Hana): Hana saw Dario at the Old Library at minute 6, and a ledger agrees.  
  → points to: Dario: "I spent that stretch of the day at the Old Library, plain as that."
- at Old Library, npc_reveal (revealed by Hana): Hana saw Piotr at the Old Library at minute 6, and a ledger agrees.  
  → points to: Piotr: "I was at the Old Library around that time, ask anyone."
- at Old Library, npc_reveal (revealed by Hana): Hana recalls a document detail: hidden record.  
  → points to: Lena: "I traded it with a box of tea and came back for it at the Elder Park during minute 6."

## Characters

### Lena
```
{
 "name": "Lena",
 "age": 32,
 "role": "librarian",
 "traits": [
  "sly",
  "guarded"
 ],
 "speech_style": "quiet, rarely finishes thoughts",
 "backstory": "Came to Coldharbor a few years ago and stayed for the quiet.",
 "goals": [
  "keep the truth about cover a loss they were blamed for hidden",
  "protect their reputation"
 ],
 "relationships": {
  "npc_02": "rival"
 },
 "attitude_to_player": "polite but guarded"
}
```
Memory:
- [did, lie, secret] I traded it with a box of tea and came back for it at the Elder Park during minute 6. (Elder Park, minute 6)
- [did, hide, secret] What I did, I did to cover a loss they were blamed for. (Elder Park, minute 6)
- [did, hide, secret] I dropped a button from my coat near the Elder Park. (Elder Park, minute 6)
- [heard, if_asked] I spent minute 6 at the Old Library, with witnesses. (Old Library, minute 6)
- cover story: {"id": "npc_01_cover", "claim": "I was at the Old Library all along; I never went near the Elder Park.", "supporting_facts": ["npc_01_alibi_claim"]}

### Hana
```
{
 "name": "Hana",
 "age": 54,
 "role": "coach driver",
 "traits": [
  "observant",
  "earnest"
 ],
 "speech_style": "warm but rambling",
 "backstory": "Known in Coldharbor for always being early.",
 "goals": [
  "stay out of other people's business",
  "protect their reputation"
 ],
 "relationships": {
  "npc_01": "sibling"
 },
 "attitude_to_player": "tired and a little short-tempered"
}
```
Memory:
- [witnessed, volunteer] I spent that stretch of the day at the Little Cafe, plain as that. (Little Cafe, minute 6)
- [heard, if_asked] I passed the Elder Park and noticed something felt wrong, though I cannot say what. (Elder Park, minute 6)
- [heard, if_asked] I remember that sees:nobody unusual. (Little Cafe, that day)
- [heard, hide, secret] They secretly pockets a little coin from the tea house. (Old Library, recently)

### Elsie
```
{
 "name": "Elsie",
 "age": 62,
 "role": "baker",
 "traits": [
  "chatty",
  "impatient"
 ],
 "speech_style": "quiet, rarely finishes thoughts",
 "backstory": "Grew up in Coldharbor and never left.",
 "goals": [
  "prove someone a wrongdoer wrong",
  "help the town"
 ],
 "relationships": {
  "npc_01": "owes a favour to"
 },
 "attitude_to_player": "tired and a little short-tempered"
}
```
Memory:
- [witnessed, volunteer] I was at the Saffron Market around that time, ask anyone. (Saffron Market, minute 6)
- [heard, if_asked] I saw someone hurry away from the Elder Park around that time, but I could not see their face. (Elder Park, minute 6)
- [heard, if_asked] I remember that confirms:npc 03 presence. (Saffron Market, that day)

### Dario
```
{
 "name": "Dario",
 "age": 33,
 "role": "herbalist",
 "traits": [
  "impatient",
  "earnest"
 ],
 "speech_style": "dry humour",
 "backstory": "Inherited their trade from a relative in Coldharbor.",
 "goals": [
  "keep their job",
  "stay out of other people's business"
 ],
 "relationships": {
  "npc_01": "employer"
 },
 "attitude_to_player": "wary of strangers"
}
```
Memory:
- [witnessed, volunteer] I spent that stretch of the day at the Old Library, plain as that. (Old Library, minute 6)
- [heard, if_asked] I saw someone hurry away from the Elder Park around that time, but I could not see their face. (Elder Park, minute 6)

### Piotr
```
{
 "name": "Piotr",
 "age": 47,
 "role": "night watchman",
 "traits": [
  "sly",
  "impatient"
 ],
 "speech_style": "formal and precise",
 "backstory": "Inherited their trade from a relative in Coldharbor.",
 "goals": [
  "prove someone a wrongdoer wrong",
  "stay out of other people's business"
 ],
 "relationships": {
  "npc_01": "friend"
 },
 "attitude_to_player": "tired and a little short-tempered"
}
```
Memory:
- [witnessed, volunteer] I was at the Old Library around that time, ask anyone. (Old Library, minute 6)
- [heard, if_asked] I saw someone hurry away from the Elder Park around that time, but I could not see their face. (Elder Park, minute 6)
