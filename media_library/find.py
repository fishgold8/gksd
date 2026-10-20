"""Поиск по медиатеке. Печатает по одной короткой строке на результат.

Экономный порядок для агента:
  python find.py --summary                          кто есть в базе и сколько
  python find.py --events --person putin --text summit   какие события есть (строка на событие)
  python find.py --event e8201 --action "shaking hands"  кадры одного события

Другие примеры:
  python find.py --person putin --scene ceremony --action wreath
  python find.py --person putin --mood smiling --action "shaking hands" --time day
  python find.py --person putin --with erdogan --kind video --min-dur 4

Строка кадра:   path | dur | people | scene | shot | mood | action | time | descr
Строка события: ev | date | event | place | context | people | clips
По умолчанию с одного события показывается не больше 3 кадров (--per-event).
Работает без БД: читает data/index.jsonl и data/events.jsonl.
"""
import argparse
import json
import os
import sys
from pathlib import Path

DATA = Path(os.environ.get("MLIB_DATA") or Path(__file__).resolve().parent / "data")


def load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--person", action="append", default=[], help="кто должен быть в кадре (можно несколько)")
    ap.add_argument("--with", dest="with_", action="append", default=[], help="синоним --person")
    ap.add_argument("--alone", action="store_true", help="только один человек в кадре")
    ap.add_argument("--scene")
    ap.add_argument("--shot")
    ap.add_argument("--outfit")
    ap.add_argument("--mood", help="smiling laughing serious tense thoughtful neutral")
    ap.add_argument("--action", help="подстрока: 'shaking hands', 'wreath', 'speaking'...")
    ap.add_argument("--time", help="day evening night indoor")
    ap.add_argument("--kind", choices=["video", "photo"])
    ap.add_argument("--min-dur", type=float)
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--text", help="подстрока в описании/действии (для --events: в событии/месте/контексте)")
    ap.add_argument("--event", help="id события из --events, например e8201")
    ap.add_argument("--events", action="store_true", help="список событий вместо кадров")
    ap.add_argument("--per-event", type=int, default=3, help="макс. кадров с одного события (0 = без лимита)")
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

    if a.events:
        for e in load("events.jsonl"):
            if need and not need <= set(e["people"]):
                continue
            if a.since and e["date"] < a.since or a.until and e["date"] > a.until:
                continue
            if text and text not in f"{e['event']} {e['place']} {e['context']}".lower():
                continue
            print(json.dumps(e, ensure_ascii=False) if a.json else " | ".join(str(x) for x in [
                e["ev"], e["date"], e["event"], e["place"], e["context"], ",".join(e["people"]),
                f"{e['clips']} clips ({e['video']} video)"]))
            n += 1
            if n >= a.limit:
                break
        if n == 0:
            print("ничего не найдено", file=sys.stderr)
        return

    seen = {}
    for r in load("index.jsonl"):
        if a.event and r["ev"] != a.event:
            continue
        if need and not need <= set(r["people"]):
            continue
        if a.alone and len(r["people"]) != 1:
            continue
        if a.scene and r["scene"] != a.scene:
            continue
        if a.shot and r["shot"] != a.shot:
            continue
        if a.outfit and r["outfit"] != a.outfit:
            continue
        if a.mood and r.get("mood") != a.mood:
            continue
        if a.time and r.get("time") != a.time:
            continue
        if a.action and a.action.lower() not in (r.get("action") or "").lower():
            continue
        if a.kind and (r["kind"] == "photo") != (a.kind == "photo"):
            continue
        if a.min_dur and (r["dur"] or 0) < a.min_dur:
            continue
        if a.since and r["date"] < a.since or a.until and r["date"] > a.until:
            continue
        if text and text not in f"{r['descr']} {r.get('descr_ru', '')} {r.get('action', '')} {r.get('with', '')}".lower():
            continue
        # не заваливать выдачу почти одинаковыми планами одного события
        if not a.event:
            key = (r["ev"], r["scene"], r.get("action"), r["shot"])
            if key in seen or (a.per_event and seen.get(r["ev"], 0) >= a.per_event):
                continue
            seen[key] = 1
            seen[r["ev"]] = seen.get(r["ev"], 0) + 1
        if a.json:
            print(json.dumps(r, ensure_ascii=False))
        else:
            print(" | ".join(str(x) for x in [
                r["path"], f"{r['dur']}s" if r["dur"] else "photo", ",".join(r["people"]),
                r["scene"], r["shot"], r.get("mood", ""), r.get("action", ""), r.get("time", ""), r["descr"]]))
        n += 1
        if n >= a.limit:
            break
    if n == 0:
        print("ничего не найдено", file=sys.stderr)


if __name__ == "__main__":
    main()
