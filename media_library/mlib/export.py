"""Готовая библиотека: нарезанные клипы и фото с говорящими именами + индекс.

library/<человек>/<сцена>/<дата>_<люди>_<сцена>_<крупность>_<id>.mp4|jpg
index.jsonl — одна короткая строка на план (то, что читает агент).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

FIELDS = ["id", "ev", "path", "kind", "dur", "people", "scene", "shot", "outfit", "mood", "action", "with", "time",
          "date", "descr", "descr_ru"]


def slug(s, n=40):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:n]


def lib_name(s, focus):
    ppl = [p for p in s["people"].split(",") if p]
    main = next((p for p in focus if p in ppl), ppl[0] if ppl else "_unknown")
    rest = [p for p in ppl if p != main][:2]
    ext = ".jpg" if s["kind"] == "photo" else ".mp4"
    name = "_".join(x for x in [s["date"], main, *rest, s["scene"] or "x", s["shot"] or "x", s["id"]] if x)
    return Path(main) / (s["scene"] or "other") / (name + ext)


def cut(src, a, b, dest, crf):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-i", src, "-t", f"{b - a:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", str(dest)], check=True)


def ev_id(s):
    return "e" + s["media_id"].split("-")[0].lstrip("abcdefghijklmnopqrstuvwxyz")


def row(s):
    # событийные поля (event/place/context) лежат в events.jsonl, здесь только ссылка "ev"
    return {
        "id": s["id"], "ev": ev_id(s), "path": s["lib_path"], "kind": s["kind"],
        "dur": round(s["dur"], 1) if s["dur"] else None,
        "people": [p for p in s["people"].split(",") if p],
        "scene": s["scene"], "shot": s["shot"], "outfit": s["outfit"],
        "mood": s["mood"], "action": s["action"], "with": s["partner"], "time": s["daytime"],
        "date": s["date"], "descr": s["descr"], "descr_ru": s["descr_ru"],
    }


def _most_common(vals):
    vals = [v for v in vals if v]
    return max(set(vals), key=vals.count) if vals else ""


def process(cfg, con, log=print):
    lib = Path(cfg["data_dir"]) / "library"
    focus = cfg["focus_people"]
    rows = con.execute(
        "SELECT s.*, m.raw_path FROM shots s JOIN media m ON m.id=s.media_id "
        "WHERE m.stage='tagged' AND s.people!=''").fetchall()
    for s in rows:
        rel = lib_name(s, focus)
        dest = lib / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        old = s["lib_path"]
        if old and old != str(rel) and (lib / old).exists():
            (lib / old).rename(dest)
        elif not dest.exists():
            if s["kind"] == "photo":
                shutil.copy2(s["raw_path"], dest)
            else:
                cut(s["raw_path"], s["tc_in"], s["tc_out"], dest, cfg["clip_crf"])
        con.execute("UPDATE shots SET lib_path=? WHERE id=?", (str(rel), s["id"]))
    con.execute("UPDATE media SET stage='exported' WHERE stage='tagged'")
    con.commit()
    write_index(cfg, con)
    log(f"  в библиотеке обновлено {len(rows)} файлов")


def write_index(cfg, con):
    d = Path(cfg["data_dir"])
    shots = con.execute("SELECT * FROM shots WHERE lib_path IS NOT NULL ORDER BY date DESC, id").fetchall()
    with open(d / "index.jsonl", "w", encoding="utf-8") as f:
        for s in shots:
            f.write(json.dumps(row(s), ensure_ascii=False, separators=(",", ":")) + "\n")
    # события: одна строка на пост — дата, событие, место, контекст, люди, сколько клипов
    events = {}
    for s in shots:
        events.setdefault(ev_id(s), []).append(s)
    with open(d / "events.jsonl", "w", encoding="utf-8") as f:
        for ev, ss in sorted(events.items(), key=lambda kv: kv[1][0]["date"], reverse=True):
            ppl = sorted({p for x in ss for p in x["people"].split(",") if p})
            f.write(json.dumps({
                "ev": ev, "date": ss[0]["date"], "event": _most_common([x["event"] for x in ss])[:80],
                "place": _most_common([x["place"] for x in ss]), "context": _most_common([x["context"] for x in ss]),
                "people": ppl, "clips": len(ss), "video": sum(x["kind"] != "photo" for x in ss),
                "src": ss[0]["post_url"]}, ensure_ascii=False, separators=(",", ":")) + "\n")
    # сводка: кто есть и сколько материалов по каждой сцене — агент читает её первой
    summary = {}
    for s in shots:
        for p in [p for p in s["people"].split(",") if p]:
            e = summary.setdefault(p, {"total": 0, "video": 0, "photo": 0, "scenes": {}})
            e["total"] += 1
            e["video" if s["kind"] != "photo" else "photo"] += 1
            e["scenes"][s["scene"] or "other"] = e["scenes"].get(s["scene"] or "other", 0) + 1
    summary = dict(sorted(summary.items(), key=lambda kv: -kv[1]["total"]))
    (d / "people_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
