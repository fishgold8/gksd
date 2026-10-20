"""SQLite: одна таблица исходников (media) и одна таблица планов (shots).

Планы — это единица поиска: для фото один план, для видео — по одному на
каждую склейку. Все метки лежат в shots, чтобы поиск был одним SELECT.
"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS media (
    id        TEXT PRIMARY KEY,      -- kre12345-1
    channel   TEXT, post_id INTEGER, idx INTEGER,
    kind      TEXT,                  -- photo | video | video_big (не скачано)
    raw_path  TEXT, url TEXT, post_url TEXT,
    date      TEXT, text TEXT,
    duration  REAL, width INTEGER, height INTEGER,
    stage     TEXT DEFAULT 'raw'     -- raw -> shots -> faces -> tagged -> exported
);
CREATE TABLE IF NOT EXISTS shots (
    id        TEXT PRIMARY KEY,      -- kre12345-1-s03
    media_id  TEXT REFERENCES media(id),
    kind      TEXT,                  -- photo | video
    tc_in     REAL, tc_out REAL, dur REAL,
    keyframe  TEXT,
    people    TEXT DEFAULT '',       -- ',putin,erdogan,' (запятые по краям для LIKE)
    n_faces   INTEGER,
    face_px   REAL,                  -- доля высоты кадра у самого крупного лица
    scene     TEXT DEFAULT '',       -- solo talk meeting speech military walk handshake press crowd other
    shot      TEXT DEFAULT '',       -- close medium wide
    outfit    TEXT DEFAULT '',       -- suit military casual
    place     TEXT DEFAULT '',
    descr     TEXT DEFAULT '',       -- <= 12 слов
    mood      TEXT DEFAULT '',       -- smiling laughing serious tense thoughtful neutral
    action    TEXT DEFAULT '',       -- shaking hands, speaking at microphone, ...
    partner   TEXT DEFAULT '',       -- с кем взаимодействует главный человек
    date      TEXT, event TEXT, post_url TEXT,
    lib_path  TEXT,
    tagged_by TEXT DEFAULT ''        -- rules | vision
);
CREATE INDEX IF NOT EXISTS shots_scene ON shots(scene);
CREATE INDEX IF NOT EXISTS shots_date  ON shots(date);
"""


def connect(cfg):
    cfg["data_dir"].mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(cfg["data_dir"] / "index.db")
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    cols = {r[1] for r in con.execute("PRAGMA table_info(shots)")}
    for c in ("mood", "action", "partner"):
        if c not in cols:
            con.execute(f"ALTER TABLE shots ADD COLUMN {c} TEXT DEFAULT ''")
    return con
