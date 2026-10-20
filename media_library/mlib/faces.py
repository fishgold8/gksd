"""Распознавание лиц на ключевых кадрах (InsightFace, локально, бесплатно).

Эталоны: people/<id>/*.jpg (3–10 чётких фото лица). Результат по каждому
плану: кто узнан, сколько всего лиц, размер самого крупного лица. Из размера
лица сразу получается крупность плана (close / medium / wide).
Если insightface не установлен, шаг пропускается и всё решает ИИ-подпись.
"""
from pathlib import Path

import numpy as np

from . import ROOT


def _app():
    from insightface.app import FaceAnalysis

    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    return app


def _refs(app):
    import cv2

    refs = {}
    for d in sorted((ROOT / "people").iterdir()):
        embs = []
        for f in sorted(d.glob("*.[jp][pn]g")):
            faces = app.get(cv2.imread(str(f)))
            if faces:
                big = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
                embs.append(big.normed_embedding)
        if embs:
            m = np.mean(embs, axis=0)
            refs[d.name] = m / np.linalg.norm(m)
    return refs


def shot_size(face_frac):
    if face_frac >= 0.22:
        return "close"
    if face_frac >= 0.08:
        return "medium"
    return "wide"


def process(cfg, con, log=print):
    try:
        import cv2  # noqa: F401
        app = _app()
    except Exception as e:  # нет insightface / моделей
        log(f"  распознавание лиц пропущено: {e}")
        con.execute("UPDATE media SET stage='faces' WHERE stage='shots'")
        con.commit()
        return
    import cv2

    refs = _refs(app)
    if not refs:
        log("  нет эталонных фото в people/<id>/ — узнавание имён пропущено")
    thr = cfg["face_match_threshold"]
    rows = con.execute("SELECT s.* FROM shots s JOIN media m ON m.id=s.media_id WHERE m.stage='shots'").fetchall()
    for s in rows:
        img = cv2.imread(s["keyframe"])
        if img is None:
            continue
        h = img.shape[0]
        faces = app.get(img)
        found = set()
        for f in faces:
            best = max(refs.items(), key=lambda kv: float(f.normed_embedding @ kv[1]), default=None)
            if best and float(f.normed_embedding @ best[1]) >= thr:
                found.add(best[0])
        frac = max(((f.bbox[3] - f.bbox[1]) / h for f in faces), default=0.0)
        people = "," + ",".join(sorted(found)) + "," if found else ""
        con.execute("UPDATE shots SET people=?, n_faces=?, face_px=?, shot=? WHERE id=?",
                    (people, len(faces), round(frac, 3), shot_size(frac) if faces else "wide", s["id"]))
    con.execute("UPDATE media SET stage='faces' WHERE stage='shots'")
    con.commit()
    log(f"  лица проверены на {len(rows)} кадрах")
