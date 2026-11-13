"""Чёткий Новосибирск: VK news autoposter, no AI key required, dry-run by default."""
import difflib
import hashlib
import html
import json
import logging
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from engagement import game_draft
from news_quality import is_self_contained_news, mentions_missing_media, source_url

TZ = ZoneInfo("Asia/Novosibirsk")
GROUP_ID = "243227021"
HISTORY_FILE = Path(__file__).with_name("history.json")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() in ("1", "yes", "true")
FEEDS = [
    ("Google Новости", "https://news.google.com/rss/search?q=" + urllib.parse.quote('"Новосибирск" when:2d') + "&hl=ru&gl=RU&ceid=RU:ru"),
    ("Google Новости — город", "https://news.google.com/rss/search?q=" + urllib.parse.quote('"в Новосибирске" when:2d') + "&hl=ru&gl=RU&ceid=RU:ru"),
]
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def slot(now):
    local = now.astimezone(TZ)
    return f"{local.date()}-{(local.hour * 60 + local.minute) // 48:02d}"


def history_load():
    if not HISTORY_FILE.exists():
        return {"posts": [], "used_links": [], "used_tags": [], "skipped_links": []}
    with HISTORY_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    return {key: data.get(key, []) for key in ("posts", "used_links", "used_tags", "skipped_links")}


def history_save(data):
    # Never truncate: full history prevents repeats across days.
    HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clean_text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", s or ""))).strip()


def url_key(url):
    p = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower().removeprefix("www."), p.path.rstrip("/"), "", ""))


def title_key(s):
    # Remove news provider suffix in syndicated headlines.
    s = re.sub(r"\s+-\s+[^-]{3,50}$", "", s or "").casefold()
    return " ".join(re.findall(r"[а-яёa-z0-9]+", s))


def title_duplicate(a, b):
    a, b = title_key(a), title_key(b)
    if not a or not b:
        return False
    if a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.83:
        return True
    x, y = set(a.split()), set(b.split())
    return len(x & y) / max(1, len(x | y)) >= 0.72 and min(len(x), len(y)) >= 4


def published_at(s):
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def read_feed(source, url):
    req = urllib.request.Request(url, headers={"User-Agent": "ChetkiyNovosibirsk/1.0 (RSS reader)"})
    with urllib.request.urlopen(req, timeout=18) as response:
        root = ET.fromstring(response.read(2_000_000))
    result = []
    for e in root.findall(".//item"):
        title, link = clean_text(e.findtext("title")), clean_text(e.findtext("link"))
        stamp = published_at(e.findtext("pubDate") or e.findtext("date"))
        if title and link and stamp:
            result.append({"source": source, "title": title, "link": link,
                           "description": clean_text(e.findtext("description"))[:400], "published": stamp})
    atom = {"a": "http://www.w3.org/2005/Atom"}
    for e in root.findall(".//a:entry", atom):
        el = e.find("a:link", atom)
        link = el.attrib.get("href", "") if el is not None else ""
        title = clean_text(e.findtext("a:title", "", atom))
        stamp = published_at(e.findtext("a:published", "", atom) or e.findtext("a:updated", "", atom))
        if title and link and stamp:
            result.append({"source": source, "title": title, "link": link,
                           "description": "", "published": stamp})
    return result


def candidates(history, now):
    used = set(history["used_links"]) | set(history["skipped_links"])
    titles = [p.get("title", "") for p in history["posts"]]
    found = []
    for name, feed in FEEDS:
        try:
            items = read_feed(name, feed)
            logging.info("RSS %s: %d материалов", name, len(items))
            for item in items:
                if not timedelta() <= now - item["published"] <= timedelta(hours=36):
                    continue
                if not re.search(r"новосибирск", (item["title"] + " " + item["description"]).casefold()):
                    continue
                if url_key(item["link"]) in used:
                    continue
                if any(title_duplicate(item["title"], t) for t in titles):
                    continue
                if any(title_duplicate(item["title"], other["title"]) for other in found):
                    continue
                found.append(item)
        except Exception as ex:
            logging.warning("Недоступный RSS %s: %s", name, ex)
    return sorted(found, key=lambda x: x["published"], reverse=True)


TOPICS = {
    "Дороги": ("дорог", "асфальт", "перекры", "движен", "пробк", "ремонт трасс", "объезд", "дтп", "авари"),
    "Транспорт": ("автобус", "трамва", "троллейбус", "маршрут", "электробус", "транспорт", "останов"),
    "ЖКХ": ("жкх", "коммун", "отоплен", "водоснаб", "отключ", "электроснаб", "тариф", "водопров"),
    "Город": ("благоустрой", "парк", "сквер", "площади", "набережн", "двор", "фонтан", "улиц"),
    "Цены": ("цен", "подорож", "подешев", "стоимост", "проезд", "тариф"),
    "Культура": ("фестивал", "концерт", "выстав", "театр", "музе", "праздник"),
    "Спорт": ("спортив", "матч", "побед", "хоккей", "футбол", "волейбол", "соревнован", "чемпионат", "плаван", "медал", "золото", "турнир"),
    "Образование": ("школ", "учител", "экзамен", "университет", "студент", "детсад"),
    "Происшествия": ("пожар", "полици", "спасател", "происшеств", "задержан", "преступлен"),
}
TAG_VARIANTS = {
    "Дороги": ("Дороги", "ЗаРулём", "Движение", "Объезды", "Ремонт", "ДорожнаяОбстановка"),
    "Транспорт": ("Транспорт", "Автобусы", "Маршруты", "Остановки", "ОбщественныйТранспорт"),
    "ЖКХ": ("ЖКХ", "Коммуналка", "Квитанции", "ГородскиеСети", "Услуги"),
    "Город": ("Город", "НашГород", "ГородскаяЖизнь", "Районы", "Благоустройство"),
    "Цены": ("Цены", "Кошелёк", "Расходы", "Тарифы", "Покупки"),
    "Культура": ("Афиша", "События", "Культура", "КудаСходить", "Досуг"),
    "Спорт": ("Спорт", "Команды", "Матчи", "НашиСпортсмены"),
    "Образование": ("Образование", "Школы", "Учёба", "Студенты"),
    "Происшествия": ("Происшествия", "Службы", "Безопасность", "Сводка"),
}
SENSITIVE = ("погиб", "смерт", "убит", "пострадав", "ребёнк", "детей", "взрыв", "суицид", "насили")
BANNED = ("?", "!", "фото", "видео", "шок", "не поверите", "ужас", "подробности", "смотрите")


def offline_draft(item, history):
    """Conservative RSS-title transformation: no invented facts or paid AI."""
    title = clean_text(item["title"])
    # RSS aggregators append the media outlet: "... | ОТВ - Новости".
    # Remove the full publisher label without removing a meaningful sentence.
    title = re.sub(r"\s+\|\s+[^|]{2,90}$", "", title).strip()
    title = re.sub(r"\s+-\s+[^-]{3,50}$", "", title)
    lower = title.casefold()
    # Only complete text-only news with a link to the original material.
    original_link = source_url(item.get("link", ""))
    if not original_link or not is_self_contained_news(title):
        return {"publish": False}
    if (not 35 <= len(title) <= 190 or any(x in lower for x in BANNED)
            or len(re.findall(r"[.!?](?:\s|$)", title)) > 1):
        return {"publish": False}
    # An oblast-wide headline is not automatically about the city.
    if re.search(r"новосибирск(?:ой|ая|ую)\s+област(?:и|ь)|новосибирском\s+районе", lower) and not re.search(r"в новосибирске|городе новосибирске|города новосибирска", lower):
        return {"publish": False}
    if not re.search(r"новосибирск", lower):
        return {"publish": False}
    if any(title_duplicate(title, p.get("title", "")) for p in history["posts"]):
        return {"publish": False}

    topic = next((topic for topic, words in TOPICS.items() if any(w in lower for w in words)), "Город")
    sensitive = any(word in lower for word in SENSITIVE)
    seed = int(hashlib.sha256(item["link"].encode("utf-8")).hexdigest()[:8], 16)
    if sensitive or topic == "Происшествия":
        prefix, emoji = "Народ", "⚠️"
    else:
        prefix = ("Братва", "Пацаны", "Родные", "Народ", "Городские")[seed % 5]
        emoji = {"Дороги": "🚧", "Транспорт": "🚌", "ЖКХ": "💸", "Город": "🏙️",
                 "Цены": "💰", "Культура": "🎭", "Спорт": "🏆", "Образование": "📚"}.get(topic, "📰")
    # Keep all original factual words. Only prepend a conversational opener.
    first_word = title.split(maxsplit=1)[0]
    prepositions = {"В", "На", "С", "О", "По", "К", "До", "За", "Из", "От", "Под", "При", "Без"}
    first = title[0].lower() + title[1:] if first_word in prepositions else title
    sentence = f"{emoji} {prefix}, {first.rstrip(' .!?…')}" + "."
    if len(sentence.split()) > 35 or len(sentence) > 290:
        return {"publish": False}

    # Keep three readable topic tags; reusing tags is better than adding IDs.
    options = TAG_VARIANTS.get(topic, TAG_VARIANTS["Город"])
    start = seed % len(options)
    tags = ["#Новосибирск" + options[(start + i) % len(options)] for i in range(3)]
    return {"publish": True, "sentence": sentence, "hashtags": tags,
            "source_url": original_link}

def format_message(draft, history):
    if not draft.get("publish"):
        return None
    sentence = re.sub(r"\s+", " ", str(draft.get("sentence", ""))).strip()
    tags = draft.get("hashtags")
    if not sentence or not isinstance(tags, list) or len(tags) != 3:
        return None
    if mentions_missing_media(sentence):
        return None
    if len(sentence.split()) > 35 or len(sentence) > 290 or "#" in sentence:
        return None
    if len(re.findall(r"[.!?…](?:\s|$)", sentence)) > 1:
        return None
    if any(not isinstance(t, str) or not re.fullmatch(r"#[А-Яа-яЁёA-Za-z]+", t)
           or "новосибирск" not in t.casefold() for t in tags):
        return None
    lowered = [x.casefold() for x in tags]
    if len(set(lowered)) != 3:
        return None
    message = sentence + "\n\n" + " ".join(tags)
    if "source_url" in draft:
        link = source_url(draft["source_url"])
        if not link:
            return None
        message += "\n\nИсточник: " + link
    return message


def post_vk(message, time_slot):
    token = os.getenv("NOVOSIBIRSK_VK_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Нужен Secret NOVOSIBIRSK_VK_TOKEN")
    random_id = int(hashlib.sha256((GROUP_ID + time_slot).encode()).hexdigest()[:8], 16)
    body = urllib.parse.urlencode({
        "owner_id": "-" + GROUP_ID, "from_group": "1", "message": message,
        "random_id": random_id, "access_token": token, "v": "5.199"}).encode()
    req = urllib.request.Request("https://api.vk.com/method/wall.post", data=body)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode())
    if "error" in data:
        raise RuntimeError("VK API: " + str(data["error"].get("error_msg", "unknown")))
    return data["response"]["post_id"]


def main():
    now = datetime.now(timezone.utc)
    time_slot = slot(now)
    h = history_load()
    if DRY_RUN and os.getenv("GITHUB_EVENT_NAME") == "schedule":
        logging.info("Тестовый режим: автоматические публикации отключены.")
        return
    if not DRY_RUN and not os.getenv("NOVOSIBIRSK_VK_TOKEN", "").strip():
        logging.warning("Не указан NOVOSIBIRSK_VK_TOKEN: реальный постинг отключён.")
        return
    if any(p.get("slot") == time_slot for p in h["posts"]):
        logging.info("Слот %s уже опубликован", time_slot)
        return
    if sum(str(p.get("slot", "")).startswith(time_slot[:10]) for p in h["posts"]) >= 30:
        logging.info("Достигнут лимит 30 за сутки")
        return
    feed_items = candidates(h, now)
    for item in feed_items[:8]:
        draft = offline_draft(item, h)
        message = format_message(draft, h)
        if not message:
            logging.info("Не прошёл проверку: %s", item["title"])
            if not DRY_RUN:
                h["skipped_links"].append(url_key(item["link"]))
            continue
        if DRY_RUN:
            logging.info("ТЕСТ — не публикуем. Источник %s: %s\n%s",
                         item["source"], item["link"], message)
            return
        post_id = post_vk(message, time_slot)
        h["posts"].append({"slot": time_slot, "post_id": post_id, "source": item["source"],
                           "title": item["title"], "link": item["link"],
                           "text": message.split("\n\n")[0], "published_at": now.isoformat()})
        h["used_links"].append(url_key(item["link"]))
        h["used_tags"].extend(message.split("\n\n")[1].split())
        history_save(h)
        logging.info("Опубликовано: %s", post_id)
        return
    # No publishable fresh news: engage subscribers with a short, non-repeating
    # question. Games share the same 30-post daily limit and 48-minute slots.
    game = game_draft(h, now)
    if game:
        message = format_message(game, h)
        if message:
            if DRY_RUN:
                logging.info("ТЕСТ — интерактивный пост, не публикуем:\n%s", message)
                return
            post_id = post_vk(message, time_slot)
            h["posts"].append({"slot": time_slot, "post_id": post_id,
                               "kind": "game", "game_key": game["game_key"],
                               "title": "Вопрос подписчикам", "text": game["sentence"],
                               "published_at": now.isoformat()})
            h["used_tags"].extend(message.split("\n\n")[1].split())
            history_save(h)
            logging.info("Опубликована игра: %s", post_id)
            return
    if not DRY_RUN:
        history_save(h)
    logging.info("Нет новых новостей и нет подходящего интерактивного поста для этого слота.")


if __name__ == "__main__":
    main()
