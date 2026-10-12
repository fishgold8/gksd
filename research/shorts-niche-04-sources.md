# Ниша #4. Откуда брать скриншоты и переписки: Roblox и видеоигры

Дата: 2026-10-12. Дополнение к `shorts-niche-04-caldruki.md`.
Проверка: названия сообществ, API и инструментов подтверждены веб-поиском; цифры участников взяты из агрегатора GummySearch и могут отставать. Из среды сами сайты недоступны, живые ссылки не проверялись.

## 0. Четыре потока исходников

| Поток | Кто так делает | Доля на старте | Доля после 50 тыс подписчиков |
|---|---|---|---|
| 1. Публичные площадки (Reddit, Steam, магазины приложений, комментарии YouTube, X, Discord) | все | 70% | 30% |
| 2. Присланное зрителями (Discord, форма, DM) | Caldruki | 0% | 40% |
| 3. Собственные скриншоты (вымышленные анонимные чаты) | Daydih («custom made screenshots») | 20% | 20% |
| 4. Партнёры (мем-паблики, владельцы Discord-серверов, мелкие авторы) | мем-сети | 10% | 10% |

Поток 2 появляется только после аудитории. Первые 2–3 месяца живёте на потоках 1 и 3.

## 1. Roblox: конкретные источники

### 1.1 Reddit
- **r/GoCommitDie** (~611 тыс). Описание сабреддита: «screenshots of odd Roblox conversations, cursed Roblox images, Roblox-related Engrish». Это главный источник переписок из игры. Смотреть top за день и неделю, флейры cursed и satire.
- **r/bloxymemes** (~80 тыс), «the ultimate Roblox meme hub». Картинки-мемы, меньше переписок.
- **r/roblox** (основной, крупный): жалобы на баны, скрины поддержки, «меня взломал брат».
- **r/RobloxAvatars**: аватары на оценку, материал для рубрики «roast my avatar».
- **r/robloxgamedev** и **devforum.roblox.com**: драмы разработчиков («мою игру скопировали»), просьбы детей «сделайте мне игру за 50 Robux».
- **r/RobloxHelp**: саппорт-кринж, скрины переписок с поддержкой Roblox.
Доступ: вручную через браузер (old.reddit.com удобнее для скринов). Программно: публичные `.json`-эндпоинты в 2026 году ненадёжны (сообщения о массовых 403 с мая 2026), официальный OAuth API бесплатно даёт ~100 запросов/мин на приложение. Для поиска по ключевым словам в истории: Arctic Shift, PullPush (проверяйте доступность).

### 1.2 Отзывы в магазинах приложений
Roblox в Google Play и App Store имеет десятки миллионов оценок, текстовые отзывы пишут дети: «5 звёзд, но мама забрала телефон», «верните мой Robux», угрозы разработчикам. Это не занято никем в формате озвучки.
Инструменты: `google-play-scraper` (Python, pip, без ключей; сортировки newest, rating, helpfulness; отдаёт не все отзывы, но тысячи), для iOS `app-store-scraper`. Отдельно отзывы на мобильные игры рядом с Roblox: Brawl Stars, Clash Royale, Toca Boca, Minecraft PE.

### 1.3 Комментарии YouTube
Под роликами крупных Roblox-каналов (nobrainjames, Potemer, Lana's Life, Flamingo, KreekCraft) миллионы детских комментариев.
Инструмент: официальный YouTube Data API, метод `commentThreads.list`, стоимость 1 единица за страницу до 100 комментариев, квота 10 000 единиц в день бесплатно. Этого хватает на сотни тысяч комментариев ежедневно. Сортировать по лайкам, фильтровать по длине и ключевым словам.

### 1.4 X (Twitter)
- Ответы под официальным @Roblox и новостными аккаунтами сообщества (Bloxy News, RTC): дети требуют Robux, родители жалуются.
- Хэштеги #Roblox, #RobloxDown в дни сбоев: золотая жила реакций.
Доступ: вручную со скриншотами. API X платный (Basic около $200/мес), для старта не нужен.

### 1.5 Discord
Серверы Roblox-игр и трейдинговые серверы (Adopt Me, Blox Fruits, MM2). Искать через Disboard (тег roblox), top.gg, discord.me. Публичные каналы можно скринить, ники замазывать. Там же искать владельцев серверов для партнёрства (поток 4).

### 1.6 Прочее
- Комментарии TikTok под Roblox-видео: вручную.
- Группы Roblox (group wall): публичные стены групп, спам-войны, «вступи или бан».
- Fandom-вики по Roblox-играм: обсуждения пишут дети 9–12 лет.

### 1.7 Ограничения для Roblox
- Лица и реальные имена несовершеннолетних не показывать вообще. Замазывать ники даже там, где это аватар.
- Не ставить метку «для детей». Целиться в 16+ (ностальгия, родители, баны, драма разработчиков).

## 2. Видеоигры в целом: конкретные источники

### 2.1 Отзывы Steam (главный якорь)
Официальный эндпоинт без ключа: `https://store.steampowered.com/appreviews/<appid>?json=1`. Параметры: `filter` (recent/updated/all), `language=english`, `day_range` до 365, `review_type`, `purchase_type`, `num_per_page` до 100, `cursor` для пагинации. В ответе у каждого отзыва есть `votes_funny` и `votes_up`, сортируйте по `votes_funny` локально. Побочные источники: **r/SteamReviews** (~42 тыс, «the most humorous or informative user reviews posted on Steam»), подборка steam250.com/tag/funny, Know Your Meme «Steam User Reviews». Valve с 2024 года прячет шуточные отзывы ниже в выдаче магазина, поэтому API лучше ручного просмотра.

### 2.2 Reddit (игровые)
- Общие: r/gaming (десятки миллионов), r/gamingcirclejerk, r/Gamingmemes, r/pcmasterrace.
- По играм: r/MinecraftMemes, r/PhoenixSC, r/FortNiteBR, r/VALORANT, r/leagueoflegends, r/apexlegends, r/Overwatch. В каждом есть посты «посмотрите, что мне написали в чате».
- Текстовые универсальные: r/ihadastroke, r/comedynecrophilia, r/KidsAreFuckingStupid, r/texts, r/insaneparents (родители и игры).

### 2.3 Сообщения Xbox Live и PSN
Отдельного живого сабреддита или аккаунта не найдено, материал распылён по r/gaming, r/xbox, r/PS5 и старым YouTube-компиляциям. Самый надёжный путь: просить зрителей присылать свой hate mail. Это одна из лучших UGC-рубрик для геймерского канала.

### 2.4 Комментарии YouTube и Twitch
Комментарии под трейлерами и патчноутами (тот же YouTube Data API). Чат Twitch в клипах с драматичных моментов, скрины чата под банами стримеров (r/LivestreamFail как навигатор).

### 2.5 X: ответы под официальными аккаунтами игр
@FortniteGame, @PlayApex, @CallofDuty, @Minecraft, @RockstarGames: каждый патчноут собирает тысячи абсурдных ответов. Вручную, 20 минут в день.

### 2.6 Discord
Публичные игровые серверы через Disboard и top.gg, каналы #general и #memes. Отдельно: мод-чаты и логи банов.

### 2.7 Другие площадки
- Metacritic и Google Play: отзывы 0/10 с эссе на три абзаца.
- Nexus Mods: комментарии под модами, конфликты авторов.
- Steam Community Discussions: гневные треды «refund now».
- Know Your Meme: контекст и шаблоны, чтобы попадать в актуальные мемы.

## 3. Присланное зрителями (как у Caldruki)

- Discord-сервер с первого дня: канал #submit, правила в закрепе (обрезать ники, без личных данных, только английский, что присылать: Roblox-чаты, Steam-отзывы, hate mail, переписки с поддержкой).
- Запасной канал: Google Form и DM в TikTok/Instagram.
- Стимул: упоминание «sent by …» в ролике, еженедельная «best submission», роль на сервере.
- В описании каждого ролика одна строка: «Send your screenshots in Discord (link)».
- Модерация: проверять, что скрин не поддельный компромат на реального человека; удалять фамилии, лица, номера.
Ожидание: заметный поток начинается с 10–20 тыс подписчиков.

## 4. Собственные скриншоты (как у Daydih)

Инструменты: Mockly (iMessage, Discord, Instagram, X, WhatsApp, Tinder), TryMyPost (Discord и iMessage, экспорт PNG, без аккаунта), 10015.io iMessage generator, Faceless.so text generator.
Правила: только вымышленные ники и аватары, никаких реальных людей, компаний-«жертв» и брендов в роли злодеев; это комедийный сценарий, а не «реальный скрин». Плюс: это оригинальный контент, который снимает вопрос повторного использования. Доля не выше 20–30%, иначе канал читается как полностью синтетический.

## 5. Партнёры

- Мем-паблики Instagram/TikTok по Roblox и геймингу: обмен материалом за упоминание.
- Владельцы крупных Discord-серверов: право скринить сервер за рекламу сервера в ролике.
- Мелкие авторы того же формата (например I Like Bomb, Stupid Screenshots): обмен исходниками и шаутаутами, аудитории не пересекаются.

## 6. Политика и право

- Повторное использование контента: по сводкам 2026 года озвучка сама по себе не делает контент трансформативным, нужны собственные шутки, реплики между слайдами, монтаж. Отдельная политика «inauthentic content» бьёт по шаблонным сериям, поэтому меняйте структуру, персонажей и рубрики.
- Скриншоты публичных постов: замазывать ники, не показывать лица, особенно детей. Отзывы Steam и магазинов публичны, авторов скрывать так же.
- Музыка: по сводкам 2026 года лицензированные треки из встроенного пикера разрешены только в Shorts до 60 секунд; Short длиннее минуты с претензией Content ID блокируется. Caldruki делает в среднем 72 с, поэтому либо держите ролик в 60 с с музыкой из пикера, либо ставьте мем-звуки без Content ID (myinstants, Voicy, YouTube Audio Library). Проверить на первых роликах.

## 7. Таблица доступа

| Источник | Способ | Цена | Автоматизация |
|---|---|---|---|
| Steam отзывы | официальный `appreviews` JSON | бесплатно | да, скрипт |
| Google Play / App Store отзывы | google-play-scraper, app-store-scraper | бесплатно | да |
| Комментарии YouTube | YouTube Data API, 10 000 ед./день | бесплатно | да |
| Reddit | браузер; OAuth API ~100 зап./мин | бесплатно | частично |
| X | браузер | бесплатно | нет (API платный) |
| Discord | вступить в серверы | бесплатно | нет |
| TikTok комментарии | браузер | бесплатно | нет |
| Присланное зрителями | Discord, форма | бесплатно | нет |
| Собственные скрины | Mockly, TryMyPost | бесплатно | нет |

## 8. Ежедневная рутина сорсинга (40 минут)

1. r/GoCommitDie top/day, r/SteamReviews new: 10 мин.
2. Скрипт: отзывы Steam по 5 играм из топа продаж за неделю, сортировка по `votes_funny`: 5 мин.
3. Комментарии под 3 вирусными Roblox- или геймерскими роликами через API, топ по лайкам: 10 мин.
4. Ответы под 2–3 патчноутами в X: 10 мин.
5. Разбор #submit в Discord: 5 мин.
Раз в неделю: выгрузка свежих отзывов Roblox из Google Play, обход 2–3 Discord-серверов.
Норма: 40–60 годных скринов в день на 2 ролика по 8–10 слайдов плюс запас.

## 9. Скрипты-заготовки

Steam, без ключа:
```python
import requests, json
appid = 252490  # Rust; id берётся из URL страницы игры
url = f"https://store.steampowered.com/appreviews/{appid}"
params = {"json": 1, "language": "english", "filter": "all",
          "day_range": 30, "num_per_page": 100, "purchase_type": "all"}
r = requests.get(url, params=params, timeout=30).json()
reviews = sorted(r["reviews"], key=lambda x: x["votes_funny"], reverse=True)
for rv in reviews[:20]:
    print(rv["votes_funny"], rv["voted_up"], rv["review"][:200].replace("\n", " "))
```

Google Play, отзывы Roblox:
```python
from google_play_scraper import reviews, Sort
result, _ = reviews("com.roblox.client", lang="en", country="us",
                    sort=Sort.NEWEST, count=500)
for rv in result:
    if len(rv["content"]) > 40:
        print(rv["score"], rv["content"][:200])
```

YouTube комментарии (нужен бесплатный API-ключ Google Cloud):
```python
from googleapiclient.discovery import build
yt = build("youtube", "v3", developerKey="KEY")
res = yt.commentThreads().list(part="snippet", videoId="VIDEO_ID",
                               maxResults=100, order="relevance").execute()
for it in res["items"]:
    s = it["snippet"]["topLevelComment"]["snippet"]
    print(s["likeCount"], s["textDisplay"][:200])
```
