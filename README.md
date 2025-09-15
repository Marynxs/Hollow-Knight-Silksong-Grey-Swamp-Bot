# HollowBot

A small automation bot that watches for black-screen transitions (room loading) and fires pre-programmed input sequences, create to farm rosaries in Grey-Swamp in Hollow Knight Silksong

## ⚠️ Disclaimers

- Run the bot as Administrator if the game ignores key presses. Keep the game window focused.

- It uses the tools so you need to have a lot of shell shards.

- In rare cases the character may die. In most tests the bot stops shortly after death or, at worst, keeps walking to the right without continuing the scripted sequence. When it happens stop the bot pressing Esc

## 🗡️ RECOMENDED TOOLS 

- Curveclaw
- Longpin

I didn't test the other ones. So feel free with you want 

## 🛠 RECOMENDED BUILDS

https://imgur.com/a/pMYZYpe

## 🎯 Intended In-Game Setup (Important)

Go to Grey Swamp, enter the tavern, and sit on the bench inside.

Start the bot (GUI → Start Bot or run from console).

Wait ~3 seconds while the bot arms itself.

The bot will run the full route and return to the tavern bench, then loop.

The GUI shows Cycle and Current action so you can monitor progress.

## 🧠 How It Works (Step by Step)

Central screen sampling (Monitor #1)
Every few milliseconds the bot grabs a SAMPLE_SIZE × SAMPLE_SIZE square in the center of the screen, converts to grayscale, and computes the dark pixel ratio.

Black-screen detection
If dark_ratio ≥ DARK_RATIO_LOAD, the frame is considered “black” (i.e., loading).

Debounced transitions
It looks for clear → black → clear with minimal durations to avoid flicker/false positives.

### How the movement works

Action 0 → Go out of the tavern

Action 1 → Walk to the area 

Action 2 → Fight and kill the mobs take the loot and go back

Action 3 → Go back to the tavern

Action 4 (Reset) → Returns to bench, resets counter, then schedules Action 0 and repeats.


## ⚙️ Configuration (in bot_core.py)
```
DARK_THRESHOLD     = 3      # pixel ≤ 3 (0..255) counts as dark
DARK_RATIO_LOAD    = 0.95   # ≥95% dark pixels => black screen
SAMPLE_SIZE        = 300    # central square size (px)
MIN_BLACK_DURATION = 0.05   # seconds (min “black” time)
MIN_CLEAR_DURATION = 0.10   # seconds (min “clear” time)
SCAN_INTERVAL_MS   = 10     # detector tick in ms (lower = faster, more CPU)
``` 
### Tuning tips

Missed very short loadings → lower SCAN_INTERVAL_MS to 5–7 ms, reduce SAMPLE_SIZE to 200–260, or lower MIN_BLACK_DURATION.

False positives on dark scenes → raise DARK_RATIO_LOAD (e.g., 0.98) and/or increase durations.

Multi-monitor → sampling uses monitors[1] (primary). Change index if needed.

## 🔧 Troubleshooting

No input in game → run as Administrator; ensure game window is focused.

Missed loadings → lower SCAN_INTERVAL_MS, reduce SAMPLE_SIZE, tweak DARK_* and MIN_*.

False positives on dark screens → raise DARK_RATIO_LOAD (e.g., 0.98) or increase durations.

Antivirus flags the EXE → It's normal just ignore it

Character dies → the bot usually stops shortly after death or (worst case) keeps walking right without continuing the sequence.

## 🙌 Credits
- Marynxs



