# Media library — instructions for the editing agent

Never read `data/index.jsonl`, `data/events.jsonl` or list `data/library/` directly.
Use `find.py`: one short line per result, so a search costs a few hundred tokens.

**Cheapest workflow for a voice-over line:**
1. `python find.py --events --person putin --text summit` — which events exist (one line per event: id, date, event, place, context).
2. `python find.py --event e8201 --action "shaking hands" --mood smiling` — clips from that event.

Or search clips directly (max 3 per event by default, near-duplicates hidden):
`python find.py --person putin --scene ceremony --action wreath --kind video --min-dur 4 --limit 5`

| flag | values |
|---|---|
| `--person X` (repeatable; `--with` is a synonym) | ids from `people.json`: putin, trump, zelensky, erdogan, xi, lavrov… |
| `--alone` | only one person in frame |
| `--scene` | solo, talk, meeting, speech, military, ceremony (wreaths, awards, anthem), walk, handshake, press, crowd, other |
| `--mood` | smiling, laughing, serious, tense, thoughtful, neutral |
| `--action "x"` | substring: "shaking hands", "wreath", "speaking", "signing", "listening"… |
| `--time` | day, evening, night, indoor |
| `--shot` | close, medium, wide |
| `--outfit` | suit, military, casual |
| `--kind` | video, photo |
| `--min-dur N` | clip at least N seconds |
| `--since/--until` | YYYY-MM-DD |
| `--text "word"` | substring in description/action (with `--events`: in event/place/context) |
| `--event ID` | only clips of one event (no per-event limit) |
| `--per-event N` | max clips per event, default 3 (0 = no limit) |
| `--json` | full record — only when needed |

Clip line: `path | duration | people | scene | shot | mood | action | time | description`.
`path` is relative to `data/library/`. Newest first. Every clip is one camera shot.
Source: Kremlin (CC BY 4.0) — credit "kremlin.ru" in the video.
