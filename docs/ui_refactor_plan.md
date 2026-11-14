# UI Refactor Plan: "Fabula"

## Goal
Transform the minimal UI into a beautiful, interactive, and feedback-rich interface that supports both mouse and keyboard controls.

## Phase 1: UI Component Library
- Create `src/fabula/ui/components.py`.
- Implement `Button`, `Panel`, `TextContainer` (for scrollable dialogue/journal).
- Add support for mouse hover states and keyboard focus navigation.

## Phase 2: Map View Overhaul (Town Hub)
- Refactor `MapView` to use panels and buttons instead of raw circle clicking.
- Add visual indicators for current location and NPC presence.
- Create a clear interaction menu when a location is selected (e.g., Examine, Talk).

## Phase 3: Dialogue & Journal Deep Dive
- `DialogueView`: Separate NPC portrait/mood panel, text dialogue panel, and interaction choice buttons.
- `JournalView`: Scrollable list component for journal entries with a "back" button.

## Phase 4: Accusation & Feedback Polish
- `AccusationView`: Interactive selection panels (not obscure keybindings).
- Add "Status/Feedback" overlays (popups) for successful actions (e.g., "Found: Clue", "Nothing here").

## Technical Constraints
- Keep visual assets procedurally generated or basic primitives to ensure project portability and performance.
- Maintain simulation headless architecture (no coupling UI to simulation logic directly).
