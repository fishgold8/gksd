# Media library — instructions for the editing agent

Do NOT read `data/index.jsonl` or list `data/library/` directly — it is thousands of lines.
Use `find.py`; it returns one short line per file.

1. See who is in the library and which scenes exist:
   `python find.py --summary`
2. Find footage (all flags optional and combinable):
   `python find.py --person putin --scene speech --shot close --kind video --min-dur 4 --limit 5`

| flag | values |
|---|---|
| `--person X` (repeatable; `--with` is a synonym) | ids from `people.json`: putin, trump, zelensky, erdogan, xi, lavrov… |
| `--alone` | only one person in frame |
| `--scene` | solo, talk, meeting, speech, military, ceremony (wreaths, awards, anthem), walk, handshake, press, crowd, other |
| `--mood` | smiling, laughing, serious, tense, thoughtful, neutral |
| `--action "x"` | substring of the action: "shaking hands", "laying wreath", "speaking", "signing"… |
| `--shot` | close, medium, wide |
| `--outfit` | suit, military, casual |
| `--kind` | video, photo |
| `--since/--until` | YYYY-MM-DD |
| `--text "word"` | substring in description / event / place |
| `--json` | full record (event, place, source link) — only when needed |

Output: `path | duration | people | scene | shot | outfit | mood | date | description`.
To match a voice-over line, combine person + action/mood, e.g. `--person putin --action wreath` or `--person putin --mood smiling --action "shaking hands"`.
`path` is relative to `data/library/`. Newest first. Every clip is already cut to one shot.
Source: Kremlin (CC BY 4.0) — credit "kremlin.ru" in the video.
