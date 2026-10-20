"""Разметка без ключа API: кадры собираются в пронумерованные листы, которые
подписывает Claude в рабочей сессии (или человек), а ответ загружается в базу.

  python run.py sheets          -> data/sheets/sheet_001.jpg + sheet_001.json
  (подписать: data/sheets/sheet_001.labels.jsonl, по строке на кадр)
  python run.py import-labels   -> метки в базу, tagged_by='manual'
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .tag import first_sentence, text_people
from . import load_people

PER_SHEET, COLS, CELL_W, CELL_H = 12, 4, 400, 260


def _font():
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(f).exists():
            return ImageFont.truetype(f, 28)
    return ImageFont.load_default()


def make(cfg, con, log=print):
    out = Path(cfg["data_dir"]) / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    people = load_people()
    focus = set(cfg["focus_people"])
    rows = con.execute(
        "SELECT s.id, s.keyframe, s.people, m.text FROM shots s JOIN media m ON m.id=s.media_id "
        "WHERE m.stage!='raw' AND s.tagged_by!='manual' ORDER BY m.date DESC, s.id").fetchall()
    # кандидаты: лицо узнано или человек упомянут в посте
    rows = [r for r in rows if focus & set(filter(None, r["people"].split(",")))
            or focus & set(text_people(r["text"] or "", people))]
    font = _font()
    # нумерация продолжает уже существующие листы, старые не перезаписываются
    n_sheets = len(list(out.glob("sheet_*[0-9].jpg")))
    first = n_sheets + 1
    for k in range(0, len(rows), PER_SHEET):
        part = rows[k:k + PER_SHEET]
        n_sheets += 1
        name = f"sheet_{n_sheets:03d}"
        sheet = Image.new("RGB", (COLS * CELL_W, -(-len(part) // COLS) * CELL_H), "white")
        draw = ImageDraw.Draw(sheet)
        manifest = []
        for i, r in enumerate(part):
            im = Image.open(r["keyframe"]).convert("RGB")
            im.thumbnail((CELL_W - 6, CELL_H - 6))
            x, y = (i % COLS) * CELL_W, (i // COLS) * CELL_H
            sheet.paste(im, (x + 3, y + 3))
            draw.rectangle([x + 3, y + 3, x + 46, y + 38], fill="black")
            draw.text((x + 8, y + 5), str(i + 1), fill="yellow", font=font)
            manifest.append({"n": i + 1, "id": r["id"], "faces": r["people"].strip(","),
                             "caption": first_sentence(r["text"], 160)})
        sheet.save(out / f"{name}.jpg", quality=85)
        (out / f"{name}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=0), encoding="utf-8")
    log(f"  {len(rows)} кадров -> листы {first}..{n_sheets} в {out}")


def import_labels(cfg, con, log=print):
    d = Path(cfg["data_dir"]) / "sheets"
    n = 0
    for f in sorted(d.glob("*.labels.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            ppl = sorted(set(r.get("people") or []))
            con.execute(
                "UPDATE shots SET people=?, scene=?, shot=?, outfit=?, descr=?, place=?, event=COALESCE(NULLIF(?, ''), event), "
                "mood=COALESCE(NULLIF(?, ''), mood), action=COALESCE(NULLIF(?, ''), action), "
                "partner=COALESCE(NULLIF(?, ''), partner), tagged_by='manual' WHERE id=?",
                ("," + ",".join(ppl) + "," if ppl else "", r.get("scene", ""), r.get("shot", ""),
                 r.get("outfit", ""), (r.get("descr") or "")[:100], (r.get("place") or "")[:40],
                 (r.get("event") or "")[:80], r.get("mood") or "", (r.get("action") or "")[:40],
                 (r.get("with") or "")[:40], r["id"]))
            n += 1
    con.commit()
    log(f"  загружено меток: {n}")
