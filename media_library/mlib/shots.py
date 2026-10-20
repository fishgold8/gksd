"""Нарезка видео на планы (склейки) и извлечение ключевых кадров. Локально, бесплатно."""
import json
import subprocess
from pathlib import Path


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", path],
        capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = (j.get("streams") or [{}])[0]
    return float(j.get("format", {}).get("duration") or 0), s.get("width"), s.get("height")


def detect(path, min_sec, max_sec):
    """Список (начало, конец) в секундах. Длинные планы режутся на куски max_sec."""
    from scenedetect import ContentDetector, detect as sd_detect

    scenes = [(a.get_seconds(), b.get_seconds()) for a, b in sd_detect(path, ContentDetector())]
    if not scenes:
        scenes = [(0.0, probe(path)[0])]
    res = []
    for a, b in scenes:
        if b - a < min_sec:
            continue
        while b - a > max_sec * 1.5:
            res.append((a, a + max_sec))
            a += max_sec
        res.append((a, b))
    return res


def keyframe(src, t, dest, width):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", src, "-frames:v", "1",
         "-vf", f"scale={width}:-2", "-q:v", "4", dest], check=True)


def process(cfg, con, log=print):
    kf_dir = Path(cfg["data_dir"]) / "keyframes"
    kf_dir.mkdir(parents=True, exist_ok=True)
    rows = con.execute("SELECT * FROM media WHERE stage='raw' AND raw_path!=''").fetchall()
    for r in rows:
        src = r["raw_path"]
        base = dict(media_id=r["id"], date=r["date"], post_url=r["post_url"])
        try:
            dur, w, h = probe(src)
            if r["kind"] == "photo":
                kf = kf_dir / f"{r['id']}.jpg"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf",
                                f"scale='min({cfg['keyframe_width']},iw)':-2", str(kf)], check=True)
                spans = [(None, None)]
            else:
                spans = detect(src, cfg["min_shot_sec"], cfg["max_shot_sec"])
        except (subprocess.CalledProcessError, ValueError) as e:
            log(f"  ! {r['id']}: {e}")
            continue
        for n, (a, b) in enumerate(spans, 1):
            sid = r["id"] if r["kind"] == "photo" else f"{r['id']}-s{n:02d}"
            if r["kind"] != "photo":
                kf = kf_dir / f"{sid}.jpg"
                keyframe(src, (a + b) / 2, str(kf), cfg["keyframe_width"])
            con.execute(
                "INSERT OR REPLACE INTO shots(id,media_id,kind,tc_in,tc_out,dur,keyframe,date,post_url) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (sid, base["media_id"], r["kind"], a, b, (b - a) if a is not None else None,
                 str(kf), base["date"], base["post_url"]))
        con.execute("UPDATE media SET stage='shots', duration=?, width=?, height=? WHERE id=?",
                    (dur, w, h, r["id"]))
        con.commit()
        log(f"  {r['id']}: {len(spans)} план(ов)")
