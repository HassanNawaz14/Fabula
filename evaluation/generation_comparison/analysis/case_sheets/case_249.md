# Case 249

**Title:** The Stolen Saffron Teapot  
**Town:** Elderwick

> A brass saffron teapot has gone missing from the Old Cottage, and it's up to you to uncover who did it.

## Places
- Copper Kettle Cafe (cafe) — Cozy nooks with warm lighting, where the scent of freshly brewed tea fills the air. Connects to: Quiet Residence
- Quiet Residence (residence) — A quaint little cottage nestled on a peaceful lane, its windows whispering tales of quiet evenings. Connects to: Copper Kettle Cafe, Elder Park
- Elder Park (park) — A verdant expanse where weathered benches invite the weary to rest, and ancient trees stand as silent guardians. Connects to: Quiet Residence

## Hidden truth
- Crime: theft of **brass saffron teapot** at Elder Park, minutes 2–8
- Culprit: **Sana**
- Method: Method 2: slipped it into a coat pocket while the owner was preoccupied at the loc_park.
- Motive: Motive 4: fund a fresh start elsewhere.
- How: the brass saffron teapot was slipped into a coat pocket while the owner was preoccupied at the loc_park at minute 7, by the npc_shepherd.
- Why: they did it to fund a fresh start elsewhere.

### Timeline
- minute 5: Ravi at Quiet Residence — sold a small loaf of bread for a little extra cash near the loc_residence.
- minute 7: Sana at Elder Park — was seen near the loc_park walking quickly and nervously.

### Red herrings
- none

## Clues
- at Elder Park, examine: Something is out of place — signs of a rushed exit from the loc_park.  
  → points to: Sana: "I committed the theft of brass saffron teapot at the loc_park. the brass saffron teapot was slipped into a coat pocket while the owner was preoccupied at the loc_park at minute 7, by the npc_shepherd."
- at Quiet Residence, examine: A hidden clue — a loose rumpled fabric under a display of fruit crates near the loc_residence.  
  → points to: nothing
- at Elder Park, examine: A loose rumpled fabric near a parked cart suggests someone was in a hurry to leave this area.  
  → points to: nothing
- at Quiet Residence, examine: A freshly swept step hints at a hurried exit from the loc_residence, possibly by the npc_shepherd.  
  → points to: nothing

## Characters

### Gus
```
{
 "name": "Gus",
 "age": 63,
 "role": "librarian",
 "traits": [
  "sly",
  "methodical"
 ],
 "speech_style": "warm but rambling",
 "backstory": "Known in Elderwick for always being early.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "friendly and eager to help"
}
```
Memory:
- [witnessed, volunteer] I was seen near the loc_residence at minute 7, acting nervous. (Quiet Residence, minute 7)
- [witnessed, volunteer] I was seen near the loc_cafe at minute 10, acting nervous. (Copper Kettle Cafe, minute 10)

### Hana
```
{
 "name": "Hana",
 "age": 29,
 "role": "market gossip",
 "traits": [
  "kind",
  "nervous"
 ],
 "speech_style": "warm but rambling",
 "backstory": "Known in Elderwick for always being early.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "curious about the player"
}
```
Memory:
- [did, volunteer] I passed the loc_park and noticed something felt wrong, though I cannot say what. (Elder Park, minute 9)
- [witnessed, volunteer] I was seen near the loc_residence at that time, though I insist it was only to check on a loose rumpled fabric. (Quiet Residence, minute 9)

### Ravi
```
{
 "name": "Ravi",
 "age": 57,
 "role": "market vendor",
 "traits": [
  "guarded",
  "jolly"
 ],
 "speech_style": "quick and peppered with questions",
 "backstory": "Known in Elderwick for always being early.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "tired and a little short-tempered"
}
```
Memory:
- [did, volunteer] I was seen near the loc_residence at minute 5, walking quickly away from that area. (Quiet Residence, minute 5)
- [did, volunteer] I passed by the loc_park and noticed something felt wrong about a loose rumpled fabric near a parked cart. (Elder Park, minute 6)

### Fenn
```
{
 "name": "Fenn",
 "age": 48,
 "role": "parking manager",
 "traits": [
  "gloomy",
  "observant"
 ],
 "speech_style": "formal and precise",
 "backstory": "Runs their small business debts like a ledger.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "friendly and eager to help"
}
```
Memory:
- [witnessed, volunteer] I was seen near the loc_park at minute 2, acting nervous. (Elder Park, minute 2)
- [did, hide] I left the loc_park in a hurry and hope no one finds out. (Elder Park, minute 2)
- [did, hide] I dropped a loose rumpled fabric near the loc_park and hope no one sees. (Elder Park, minute 5)
- [witnessed, volunteer] I was seen near the loc_cafe at minute 10, acting nervous. (Copper Kettle Cafe, minute 10)

### Sana
```
{
 "name": "Sana",
 "age": 42,
 "role": "herbalist",
 "traits": [
  "observant",
  "sly"
 ],
 "speech_style": "short sentences, direct",
 "backstory": "Grewled their way into a new job in Elderwick and has been hiding it ever since.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "friendly and eager to help"
}
```
Memory:
- [did, hide, secret] I committed the theft of brass saffron teapot at the loc_park. the brass saffron teapot was slipped into a coat pocket while the owner was preoccupied at the loc_park at minute 7, by the npc_shepherd. (Elder Park, minute 2)
- [witnessed, hide] was seen near the loc_park walking quickly and nervously. (Elder Park, minute 7)
- [did, volunteer] helped a lost child find their parents near the loc_residence. (Quiet Residence, minute 3)
- [witnessed, hide] was seen near the loc_park at night, acting secretive. (Elder Park, night)
- [heard, hide] argued with the npc_library_gentleman near the loc_residence and was asked to apologise. (Quiet Residence, minute 2)
- cover story: {"id": "cover_story_1", "claim": "I was at the loc_park the whole time, never near the loc_residence.", "supporting_facts": ["fact_1", "fact_2"]}
