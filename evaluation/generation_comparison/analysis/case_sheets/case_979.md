# Case 979

**Title:** The Stolen silver locket from the Old Library  
**Town:** Brindlebay

> A silver locket has gone missing from the Old Library in Brindlebay this morning. Someone here knows more than they are saying.

## Places
- Old Library (library) — The air is thick with the scent of aged paper and musty books, while the gentle clink of pages turning creates a soothing melody that lulls even the most anxious into a calm state. Connects to: Lane House
- Lane House (residence) — A quaint little house nestled along a winding lane, its windows aglow with the warm glow of lamps inside. The front step is swept clean, and a freshly tended garden hints at the owner’s meticulous care. Connects to: Old Library
- Elder Park (park) — A verdant expanse where the ground is soft underfoot from countless footsteps over generations. Ancient willows whisper secrets to those who linger near, their branches casting dappled shadows across a path worn smooth by time. Connects to: Lane House

## Hidden truth
- Crime: theft of **silver locket** at Old Library, minutes 3–10
- Culprit: **Sana**
- Method: Method 2: slipped it into a coat pocket while the stall was busy.
- Motive: Motive 4: help a friend in secret trouble.
- How: the npc_baker slipped it into a coat pocket while the stall was busy at the loc_library at minute 9.
- Why: they did it to help a friend in secret trouble.

### Timeline
- minute 3: Piotr at Old Library — stayed at the loc_library for a few minutes.
- minute 4: Sana at Old Library — passed by the loc_library and noticed something wrong.
- minute 9: Lena at Elder Park — was seen near the loc_park.

### Red herrings
- Lena: I has been skipping their night watch rounds and hope no one finds out.
- Hana: I spreads a rumour about the herbalist and hope no one finds out.

## Clues
- at Old Library, examine: Something is out of place — signs of a rushed exit from the loc_library.  
  → points to: Piotr: "I was seen near the loc_library around that time, though I cannot say if it is relevant."; Sana: "I committed the theft of silver locket at the loc_library. the npc_baker slipped it into a coat pocket while the stall was busy at the loc_library at minute 9."
- at Elder Park, examine: A loose rumour that may or may not matter: someone thinks the npc_baker is involved in town business.  
  → points to: Lena: "People have been seen near this location."
- at Old Library, examine: A loose rumour that may or may not matter: people have been seen near this location.  
  → points to: Lena: "I was walking past and saw someone hurry away from the loc_library."
- at Old Library, examine: A loose rumour that may or may not matter: someone saw something wrong but didn't report it.  
  → points to: Lena: "I passed this way and heard raised voices inside the loc_library."

## Characters

### Sana
```
{
 "name": "Sana",
 "age": 46,
 "role": "baker",
 "traits": [
  "stubborn",
  "methodical"
 ],
 "speech_style": "formal and precise",
 "backstory": "Inherited their trade from a relative in Brindlebay.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "polite but guarded"
}
```
Memory:
- [did, hide, secret] I committed the theft of silver locket at the loc_library. the npc_baker slipped it into a coat pocket while the stall was busy at the loc_library at minute 9. (Old Library, minute 3)
- [witnessed, hide] left the loc_library with a hurried step and a rumpled coat. (Old Library, minute 9)
- [heard, hide] heard people discussing the silver locket and felt it was none of their business. (Elder Park, minute 3)
- [witnessed, hide] was seen near the loc_library. (Old Library, minute 3)
- [witnessed, hide] saw someone hurry away from the loc_library with a hurried look on their face. (Old Library, minute 4)
- cover story: {"id": "npc_baker_cover", "claim": "I was at the loc_park the whole time, never near the loc_library.", "supporting_facts": ["npc_baker_trace"]}

### Hana
```
{
 "name": "Hana",
 "age": 47,
 "role": "grocer",
 "traits": [
  "guarded",
  "kind"
 ],
 "speech_style": "warm but rambling",
 "backstory": "Known in Brindlebay for always being early.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "tired and a little short-tempered"
}
```
Memory:
- [did, if_asked] I was walking past the loc_library and heard raised voices behind closed doors. (Old Library, minute 7)
- [witnessed, if_asked] I heard someone arguing near the loc_library and left in a hurry. (Old Library, minute 7)

### Bess
```
{
 "name": "Bess",
 "age": 29,
 "role": "market shepherd",
 "traits": [
  "sly",
  "observant"
 ],
 "speech_style": "warm but rambling",
 "backstory": "Known in Brindlebay for always being early.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "curious about the player"
}
```
Memory:
- [heard, volunteer] People have been seen near this location. (Old Library, minute 5)
- [witnessed, volunteer] I was near the loc_library and heard raised voices. (Old Library, minute 10)
- [did, hide, secret] I has been skipping their rounds near this location and hope no one finds out. (Old Library, minute 7)

### Fenn
```
{
 "name": "Fenn",
 "age": 47,
 "role": "market vendor",
 "traits": [
  "jolly",
  "gloomy"
 ],
 "speech_style": "warm but rambling",
 "backstory": "Known in Brindlebay for always being early.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "friendly and eager to help"
}
```
Memory:
- [heard, volunteer] People have been seen near this location. (Old Library, minute 6)
- [witnessed, volunteer] I was passing and heard raised voices inside the loc_library. (Old Library, minute 9)

### Piotr
```
{
 "name": "Piotr",
 "age": 39,
 "role": "night watchman",
 "traits": [
  "nervous",
  "observant"
 ],
 "speech_style": "quick and peppered with questions",
 "backstory": "Runs their small business debts like a ledger.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "friendly and eager to help"
}
```
Memory:
- [did, volunteer] I was walking past the loc_library and noticed something felt wrong, though I cannot say what. (Old Library, minute 3)
- [witnessed, volunteer] I was seen near the loc_library around that time, though I cannot say if it is relevant. (Old Library, minute 10)

### Lena
```
{
 "name": "Lena",
 "age": 45,
 "role": "schoolteacher",
 "traits": [
  "stubborn",
  "kind"
 ],
 "speech_style": "short, direct sentences",
 "backstory": "Grewed from Dunmore and has been in Brindlebay for a few years.",
 "goals": [],
 "relationships": {},
 "attitude_to_player": "friendly and eager to help"
}
```
Memory:
- [heard, volunteer] People have been seen near this location. (Old Library, minute 6)
- [witnessed, volunteer] I was walking past and saw someone hurry away from the loc_library. (Old Library, minute 10)
- [witnessed, if_asked] I passed this way and heard raised voices inside the loc_library. (Old Library, minute 10)
