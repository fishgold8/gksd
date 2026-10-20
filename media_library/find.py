"""Поиск по медиатеке. Печатает по одной короткой строке на файл.

  python find.py --person putin --scene speech --shot close --limit 5
  python find.py --person putin --with erdogan --kind video
  python find.py --person putin --outfit military --since 2025-01-01
  python find.py --person putin --mood smiling --action "shaking hands"
  python find.py --text "parade"          (ищет в описании, действии, событии и месте)
  python find.py --summary                (кто есть в базе и сколько)

Формат строки: path | dur | people | scene | shot | outfit | mood | date | descr
Работает без БД: читает data/index.jsonl, так что папку можно просто
скопировать на Google Диск.
"""
import argparse
import json
import os
import sys
from pathlib import Path

DATA = Path(os.environ.get("MLIB_DATA") or Path(__file__).resolve().parent / "data")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--person", action="append", default=[], help="кто должен быть в кадре (можно несколько)")
    ap.add_argument("--with", dest="with_", action="append", default=[], help="синоним --person")
    ap.add_argument("--alone", action="store_true", help="только один человек в кадре")
    ap.add_argument("--scene")
    ap.add_argument("--shot")
    ap.add_argument("--outfit")
    ap.add_argument("--mood", help="smiling laughing serious tense thoughtful neutral")
    ap.add_argument("--action", help="подстрока: 'shaking hands', 'speaking', 'walking'...")
    ap.add_argument("--kind", choices=["video", "photo"])
    ap.add_argument("--min-dur", type=float)
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--text")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--json", action="store_true", help="полные записи вместо коротких строк")
    a = ap.parse_args(argv)

    if a.summary:
        s = json.loads((DATA / "people_summary.json").read_text(encoding="utf-8"))
        for p, e in s.items():
            sc = " ".join(f"{k}:{v}" for k, v in sorted(e["scenes"].items(), key=lambda kv: -kv[1]))
            print(f"{p}: {e['total']} (video {e['video']}, photo {e['photo']}) | {sc}")
        return

    need = set(a.person + a.with_)
    text = a.text.lower() if a.text else None
    n = 0
    with open(DATA / "index.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if need and not need <= set(r["people"]):
                continue
            if a.alone and (len(r["people"]) != 1 or r["scene"] not in ("solo", "speech", "walk", "military")):
                continue
            if a.scene and r["scene"] != a.scene:
                continue
            if a.shot and r["shot"] != a.shot:
                continue
            if a.outfit and r["outfit"] != a.outfit:
                continue
            if a.mood and r.get("mood") != a.mood:
                continue
            if a.action and a.action.lower() not in (r.get("action") or "").lower():
                continue
            if a.kind and (r["kind"] == "photo") != (a.kind == "photo"):
                continue
            if a.min_dur and (r["dur"] or 0) < a.min_dur:
                continue
            if a.since and r["date"] < a.since or a.until and r["date"] > a.until:
                continue
            if text and text not in f"{r['descr']} {r['event']} {r['place']} {r.get('action', '')} {r.get('with', '')}".lower():
                continue
            if a.json:
                print(json.dumps(r, ensure_ascii=False))
            else:
                print(" | ".join(str(x) for x in [
                    r["path"], f"{r['dur']}s" if r["dur"] else "photo", ",".join(r["people"]),
                    r["scene"], r["shot"], r["outfit"], r.get("mood", ""), r["date"], r["descr"]]))
            n += 1
            if n >= a.limit:
                break
    if n == 0:
        print("ничего не найдено", file=sys.stderr)


if __name__ == "__main__":
    main()
