"""Скачивание публичного Telegram-канала через веб-превью t.me/s/<канал>.

Логин не нужен. Ограничение Telegram: видео больше ~20 МБ превью не отдаёт
(«Media is too big»). Такие записи сохраняются как kind=video_big со ссылкой
на пост; докачать их можно через mlib/scrape_api.py (Telethon).
Повторный запуск докачивает только новые посты.
"""
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
BG_URL = re.compile(r"background-image:url\('([^']+)'\)")


def short(channel):
    return re.sub(r"[^a-z]", "", channel.lower())[:3]


def _page(session, channel, before=None):
    url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
    for attempt in range(5):
        r = session.get(url, headers=UA, timeout=30)
        if r.status_code == 429:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    raise RuntimeError(f"Telegram ограничил запросы: {url}")


def parse_posts(soup):
    """Вернуть посты страницы: [{post_id, date, text, media:[{kind,url}]}]."""
    posts = []
    for msg in soup.select("div.tgme_widget_message[data-post]"):
        post_id = int(msg["data-post"].split("/")[-1])
        t = msg.select_one("a.tgme_widget_message_date time")
        text_el = msg.select_one("div.tgme_widget_message_text")
        media = []
        for el in msg.select("a.tgme_widget_message_photo_wrap, a.tgme_widget_message_video_player, "
                             "div.message_media_not_supported_wrap"):
            classes = el.get("class", [])
            if "tgme_widget_message_photo_wrap" in classes:
                m = BG_URL.search(el.get("style", ""))
                if m:
                    media.append({"kind": "photo", "url": m.group(1)})
            elif "tgme_widget_message_video_player" in classes:
                v = el.select_one("video")
                if v and v.get("src"):
                    media.append({"kind": "video", "url": v["src"]})
                else:
                    media.append({"kind": "video_big", "url": el.get("href", "")})
            elif not el.find_parent("a", class_="tgme_widget_message_video_player"):
                media.append({"kind": "video_big", "url": ""})
        posts.append({
            "post_id": post_id,
            "date": t["datetime"][:10] if t else "",
            "text": text_el.get_text("\n", strip=True) if text_el else "",
            "media": media,
        })
    return posts


def _download(session, url, dest):
    if dest.exists() and dest.stat().st_size:
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    with session.get(url, headers=UA, timeout=120, stream=True) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    tmp.rename(dest)


def scrape(cfg, con, channel, log=print):
    raw = Path(cfg["data_dir"]) / "raw" / channel
    raw.mkdir(parents=True, exist_ok=True)
    sid = short(channel)
    last = con.execute("SELECT MAX(post_id) FROM media WHERE channel=?", (channel,)).fetchone()[0] or 0
    oldest_done = con.execute("SELECT MIN(post_id) FROM media WHERE channel=?", (channel,)).fetchone()[0]
    session = requests.Session()
    before, seen, new = None, 0, 0
    while True:
        posts = parse_posts(_page(session, channel, before))
        if not posts:
            break
        stop = False
        for p in sorted(posts, key=lambda p: -p["post_id"]):
            if cfg["since_date"] and p["date"] and p["date"] < cfg["since_date"]:
                stop = True
                break
            if cfg["max_posts"] and seen >= cfg["max_posts"]:
                stop = True
                break
            seen += 1
            # уже скачанный непрерывный диапазон пропускаем
            if oldest_done is not None and oldest_done <= p["post_id"] <= last:
                continue
            for i, m in enumerate(p["media"], 1):
                mid = f"{sid}{p['post_id']}-{i}"
                if con.execute("SELECT 1 FROM media WHERE id=?", (mid,)).fetchone():
                    continue
                ext = {"photo": ".jpg", "video": ".mp4"}.get(m["kind"])
                path = ""
                if ext:
                    dest = raw / f"{p['post_id']}_{i}{ext}"
                    try:
                        _download(session, m["url"], dest)
                        path = str(dest)
                    except requests.RequestException as e:
                        log(f"  ! {mid}: {e}")
                        continue
                con.execute(
                    "INSERT INTO media(id,channel,post_id,idx,kind,raw_path,url,post_url,date,text) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (mid, channel, p["post_id"], i, m["kind"], path, m["url"],
                     f"https://t.me/{channel}/{p['post_id']}", p["date"], p["text"]))
                new += 1
            con.commit()
        min_id = min(p["post_id"] for p in posts)
        log(f"  {channel}: просмотрено {seen} постов, новых файлов {new}, дошли до #{min_id}")
        if stop or min_id <= 1 or min_id == before:
            break
        before = min_id
        time.sleep(1.0)
    return new
