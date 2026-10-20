"""Сборка медиатеки. Каждый шаг можно перезапускать: делается только новое.

  python run.py all            скачать -> нарезать -> лица -> подписи -> библиотека
  python run.py scrape         только скачать новые посты
  python run.py big            докачать большие видео через Telegram API
  python run.py shots | faces | tag | export
  python run.py tag --no-vision   подписи только по тексту, без ИИ (бесплатно)
  python run.py sheets / import-labels   разметка листами без ключа API (см. mlib/sheets.py)
  python run.py stats
"""
import argparse

from mlib import db, export, faces, load_config, scrape_api, scrape_tg, sheets, shots, tag


def stats(con):
    for q, label in [
        ("SELECT kind, COUNT(*) FROM media GROUP BY kind", "исходники"),
        ("SELECT stage, COUNT(*) FROM media GROUP BY stage", "стадии"),
        ("SELECT tagged_by, COUNT(*) FROM shots GROUP BY tagged_by", "подписи"),
        ("SELECT scene, COUNT(*) FROM shots WHERE lib_path IS NOT NULL GROUP BY scene", "сцены в библиотеке"),
    ]:
        print(label + ":", ", ".join(f"{r[0] or '-'}={r[1]}" for r in con.execute(q)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["all", "scrape", "big", "shots", "faces", "tag", "sheets", "import-labels", "export", "stats"])
    ap.add_argument("--no-vision", action="store_true", help="не вызывать ИИ")
    a = ap.parse_args()
    cfg = load_config()
    con = db.connect(cfg)
    steps = ["scrape", "big", "shots", "faces", "tag", "export"] if a.step == "all" else [a.step]
    for st in steps:
        print(f"== {st}")
        if st == "scrape":
            for ch in cfg["channels"]:
                scrape_tg.scrape(cfg, con, ch)
        elif st == "big":
            scrape_api.fetch_big(cfg, con)
        elif st == "shots":
            shots.process(cfg, con)
        elif st == "faces":
            faces.process(cfg, con)
        elif st == "tag":
            tag.process(cfg, con, use_vision=not a.no_vision)
        elif st == "sheets":
            sheets.make(cfg, con)
        elif st == "import-labels":
            sheets.import_labels(cfg, con)
        elif st == "export":
            export.process(cfg, con)
        elif st == "stats":
            stats(con)
    if a.step == "all":
        stats(con)


if __name__ == "__main__":
    main()
