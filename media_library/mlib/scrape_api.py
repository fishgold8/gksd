"""Докачка больших видео (kind=video_big) через Telegram API (Telethon).

Нужны TG_API_ID и TG_API_HASH (my.telegram.org -> API development tools).
При первом запуске Telethon попросит номер телефона и код, затем сохранит
сессию в data/tg.session. Без этих переменных шаг просто пропускается.
"""
import os
from pathlib import Path


def fetch_big(cfg, con, log=print):
    api_id, api_hash = os.environ.get("TG_API_ID"), os.environ.get("TG_API_HASH")
    rows = con.execute("SELECT * FROM media WHERE kind='video_big' AND raw_path=''").fetchall()
    if not rows:
        return 0
    if not (api_id and api_hash):
        log(f"  {len(rows)} больших видео не скачано: задайте TG_API_ID и TG_API_HASH")
        return 0
    from telethon.sync import TelegramClient

    done = 0
    with TelegramClient(str(Path(cfg["data_dir"]) / "tg"), int(api_id), api_hash) as client:
        for r in rows:
            msg = client.get_messages(r["channel"], ids=r["post_id"])
            if msg is None:
                continue
            # в альбоме у каждого файла свой message id; idx считается по порядку видео
            group = [msg]
            if msg.grouped_id:
                near = client.get_messages(r["channel"], min_id=r["post_id"] - 10, max_id=r["post_id"] + 10)
                group = sorted([m for m in near if m.grouped_id == msg.grouped_id], key=lambda m: m.id)
            media = [m for m in group if m.video or m.photo]
            if r["idx"] - 1 >= len(media) or not media[r["idx"] - 1].video:
                continue
            dest = Path(cfg["data_dir"]) / "raw" / r["channel"] / f"{r['post_id']}_{r['idx']}.mp4"
            dest.parent.mkdir(parents=True, exist_ok=True)
            log(f"  скачиваю {r['id']} ...")
            client.download_media(media[r["idx"] - 1], file=str(dest))
            con.execute("UPDATE media SET kind='video', raw_path=? WHERE id=?", (str(dest), r["id"]))
            con.commit()
            done += 1
    return done
