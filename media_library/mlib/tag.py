"""Подписи планов: сначала бесплатные правила по тексту поста, потом ИИ по кадрам.

Экономия:
- в ИИ идут только планы, где найден нужный человек (по лицу или по тексту);
- кадры уменьшены до 512 px (~200–350 токенов каждый);
- один запрос на один пост: все кадры поста + его текст разом (до 12 кадров);
- ответ — строгий короткий JSON, без рассуждений (effort=low).
"""
import base64
import json
import re

from . import load_people

SCENES = ["solo", "talk", "meeting", "speech", "military", "walk", "handshake", "press", "crowd", "other"]
SHOTS = ["close", "medium", "wide"]
OUTFITS = ["suit", "military", "casual", "unknown"]
CHUNK = 12


def text_people(text, people):
    found = []
    for pid, p in people.items():
        if any(re.search(r"\b" + re.escape(a) + r"\b", text, re.I) for a in p["aliases"]):
            found.append(pid)
    return found


TEXT_SCENES = [
    ("speech", r"\b(address|speech|remarks|plenary|addressed|spoke at)\b"),
    ("military", r"\b(troops|military|soldiers|army|navy|defence ministry|command post|parade)\b"),
    ("press", r"\b(press conference|answers to (media|journalists)|news conference)\b"),
    ("meeting", r"\b(meeting (of|on|with the)|security council|session|government members)\b"),
    ("talks", r"\b(talks|met with|meeting with|telephone conversation|conversation with)\b"),
]


def text_scene(text):
    for scene, rx in TEXT_SCENES:
        if re.search(rx, text or "", re.I):
            return "talk" if scene == "talks" else scene
    return ""


def first_sentence(text, n=140):
    s = re.split(r"(?<=[.!?])\s", (text or "").strip(), maxsplit=1)[0]
    return s[:n]


def _schema(n):
    shot = {
        "type": "object",
        "properties": {
            "i": {"type": "integer"},
            "people": {"type": "array", "items": {"type": "string"}},
            "scene": {"type": "string", "enum": SCENES},
            "shot": {"type": "string", "enum": SHOTS},
            "outfit": {"type": "string", "enum": OUTFITS},
            "descr": {"type": "string"},
        },
        "required": ["i", "people", "scene", "shot", "outfit", "descr"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "place": {"type": "string"},
            "event": {"type": "string"},
            "shots": {"type": "array", "items": shot},
        },
        "required": ["place", "event", "shots"],
        "additionalProperties": False,
    }


PROMPT = """You label news footage frames for a video editor's stock library.
Known people (use these ids): {ids}. For anyone else clearly identifiable from the caption, use a short lowercase latin id (e.g. "pezeshkian"). Do not guess identities that neither the face nor the caption supports.
Post caption: \"\"\"{caption}\"\"\"
For each frame i=1..{n} return:
- people: ids of recognisable people visible in the frame (focus person: {focus}).
- scene: solo (focus person alone in frame) | talk (1-on-1 conversation) | meeting (table, several participants) | speech (podium/address/addressing audience) | military (uniform, soldiers, military setting) | walk | handshake | press (press conference/journalists) | crowd | other.
- shot: close | medium | wide.  outfit of focus person: suit | military | casual | unknown.
- descr: at most 12 English words, concrete, no names already in people.
Also: place (city/venue from caption, short, "" if unknown) and event (max 10 words)."""


def _vision(client, cfg, people, caption, frames, focus):
    content = []
    for k, path in enumerate(frames, 1):
        data = base64.standard_b64encode(open(path, "rb").read()).decode()
        content.append({"type": "text", "text": f"Frame {k}:"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
    content.append({"type": "text", "text": PROMPT.format(
        ids=", ".join(people), caption=caption[:1200], n=len(frames), focus=", ".join(focus))})
    resp = client.beta.messages.create(
        model=cfg["vision_model"],
        max_tokens=4000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": cfg["vision_effort"], "format": {"type": "json_schema", "schema": _schema(len(frames))}},
        messages=[{"role": "user", "content": content}],
    )
    if resp.stop_reason == "refusal":
        return None, resp.usage
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text), resp.usage


def process(cfg, con, log=print, use_vision=True):
    people = load_people()
    focus = cfg["focus_people"]
    client = None
    if use_vision:
        import anthropic
        client = anthropic.Anthropic()
    tokens_in = tokens_out = calls = 0
    medias = con.execute("SELECT * FROM media WHERE stage='faces'").fetchall()
    for m in medias:
        tp = text_people(m["text"] or "", people)
        event = first_sentence(m["text"])
        shots = con.execute("SELECT * FROM shots WHERE media_id=? ORDER BY tc_in", (m["id"],)).fetchall()
        faces_ran = any(s["n_faces"] is not None for s in shots)
        todo = []
        for s in shots:
            face_people = [p for p in (s["people"] or "").split(",") if p]
            if faces_ran:
                want = any(p in focus for p in face_people)
            else:
                want = any(p in focus for p in tp)
            # бесплатная разметка по правилам — она же запасная, если ИИ выключен
            ppl = face_people or (tp if want else [])
            scene = "solo" if ppl and s["n_faces"] == 1 else (text_scene(m["text"]) if ppl else "")
            con.execute("UPDATE shots SET people=?, scene=?, event=?, tagged_by='rules' WHERE id=?",
                        ("," + ",".join(ppl) + "," if ppl else "", scene, event, s["id"]))
            if want:
                todo.append(s)
        if client and todo:
            for i in range(0, len(todo), CHUNK):
                part = todo[i:i + CHUNK]
                try:
                    res, usage = _vision(client, cfg, people, m["text"] or "", [s["keyframe"] for s in part], focus)
                except Exception as e:
                    log(f"  ! {m['id']}: {type(e).__name__}: {e}")
                    con.commit()
                    return
                calls += 1
                tokens_in += usage.input_tokens
                tokens_out += usage.output_tokens
                if not res:
                    continue
                by_i = {r["i"]: r for r in res["shots"]}
                for k, s in enumerate(part, 1):
                    r = by_i.get(k)
                    if not r:
                        continue
                    ppl = sorted(set(r["people"]) | {p for p in (s["people"] or "").split(",") if p})
                    shot = s["shot"] if s["face_px"] is not None and s["shot"] else r["shot"]
                    con.execute(
                        "UPDATE shots SET people=?, scene=?, shot=?, outfit=?, descr=?, place=?, event=?, "
                        "tagged_by='vision' WHERE id=?",
                        ("," + ",".join(ppl) + ",", r["scene"], shot, r["outfit"], r["descr"][:100],
                         res["place"][:40], res["event"][:80] or event, s["id"]))
        con.execute("UPDATE media SET stage='tagged' WHERE id=?", (m["id"],))
        con.commit()
    if calls:
        log(f"  ИИ: {calls} запросов, {tokens_in} вх. / {tokens_out} вых. токенов")
