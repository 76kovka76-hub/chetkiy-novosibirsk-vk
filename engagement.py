"""Free interaction prompts used when there is no publishable Novosibirsk news."""
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from news_quality import mentions_missing_media

TZ = ZoneInfo("Asia/Novosibirsk")
MAX_GAMES_PER_DAY = 4
MIN_GAME_INTERVAL = timedelta(hours=3)
NO_REPEAT_DAYS = 7

# (stable id, text, topic tag, preferred hours in Novosibirsk; None = any daytime hour)
PROMPTS = [
    ("metro", "🚇 Народ, какая станция новосибирского метро у вас самая любимая?", "Метро", None),
    ("opera", "🎭 Пацаны, бывали в нашем оперном — какой спектакль запомнился?", "Оперный", None),
    ("akademgorodok", "🌲 Братва, кто любит гулять по Академгородку — делитесь маршрутами!", "Академгородок", None),
    ("zoo", "🐻 Народ, когда последний раз были в Новосибирском зоопарке?", "Зоопарк", None),
    ("krasny_prospekt", "🌆 Братва, кто недавно гулял по Красному проспекту — как вам атмосфера?", "КрасныйПроспект", None),
    ("embankment", "🔥 Пацаны, Михайловская набережная или Академгородок — где любимая движуха?", "Районы", None),
    ("districts_local", "🏘️ Народ, кто из Заельцовского, Ленинского, Калининского или Советского — отмечайтесь!", "Районы", None),
    ("lunch_photo", "🍲 Братва, кто что приготовил на обед — кидайте фотки в комменты!", "Обед", (11, 15)),
    ("lunch_taste", "🥘 Пацаны, что вкуснее на обед — домашняя еда или столовка, голосуйте в комментах!", "Еда", (11, 15)),
    ("lunch_receipt", "🍝 Народ, какое блюдо вы умеете готовить лучше всех — делитесь в комментах!", "Рецепты", (11, 15)),
    ("lunch_cafe", "🍜 Братва, где в Новосибирске самый чёткий обед за нормальные деньги?", "Кафе", (11, 15)),
    ("breakfast", "🥞 Родные, кто чем сегодня завтракал — колитесь в комментах!", "Завтрак", (8, 12)),
    ("morning_coffee", "☕ Народ, утро начинаем с чая или кофе — кто за что?", "Утро", (8, 12)),
    ("morning_mood", "🌞 Братва, кто уже на ногах — ставьте плюс в комментах!", "Утро", (8, 12)),
    ("evening_plan", "🌆 Пацаны, какие планы на вечер — диван или движуха?", "Вечер", (17, 23)),
    ("evening_movie", "🎬 Братва, что посмотреть вечером — советуйте годные фильмы в комментах!", "Кино", (17, 23)),
    ("evening_music", "🎧 Народ, какой трек сегодня на повторе — кидайте название!", "Музыка", (17, 23)),
    ("evening_walk", "🌃 Родные, где в Новосибирске приятнее всего гулять вечером?", "Прогулки", (17, 23)),
    ("evening_dinner", "🍕 Братва, что на ужин — пицца, домашняя еда или что-то ещё?", "Ужин", (17, 23)),
    ("evening_rest", "🛋️ Пацаны, как лучше отдыхать после работы — делитесь идеями!", "Отдых", (17, 23)),
    ("night_owls", "🌙 Народ, кто сегодня засиделся допоздна — отмечайтесь в комментах!", "Полуночники", (20, 23)),
    ("introductions", "🤝 Братва, время знакомиться — пишите, из какого района Новосибирска вы с нами!", "Знакомства", None),
    ("districts", "🏘️ Народ, какой район Новосибирска самый родной — голосуем в комментах!", "Районы", None),
    ("city_place", "🏙️ Пацаны, какое место в Новосибирске считаете самым красивым?", "Места", None),
    ("city_photo", "📸 Братва, у кого есть крутое фото Новосибирска — кидайте в комменты!", "Фото", None),
    ("city_secret", "🗺️ Родные, какое малоизвестное место Новосибирска посоветуете друзьям?", "Маршруты", None),
    ("favorite_street", "🚶 Братва, какая улица Новосибирска вам нравится больше всего?", "Улицы", None),
    ("city_bench", "🌳 Народ, где в городе лучше всего посидеть и отдохнуть?", "Отдых", None),
    ("ob", "🌊 Братва, где у Оби красивее всего гулять — кидайте любимые места!", "Обь", None),
    ("weather_mood", "🌤️ Братва, какую погоду любите больше — солнце, снег или дождик?", "Погода", None),
    ("weekend_ideas", "🎉 Народ, куда в Новосибирске сходить на выходных — кидайте идеи!", "Выходные", None),
    ("weekend_home", "🛏️ Братва, идеальный выходной — выспаться или отправиться гулять?", "Выходные", None),
    ("pets", "🐾 Пацаны, у кого дома есть пушистый бандит — показывайте питомцев!", "Питомцы", None),
    ("cats_dogs", "🐱 Народ, кто круче — коты или собаки, спорим в комментах!", "Питомцы", None),
    ("hobby", "🎨 Родные, у кого какое увлечение после работы — рассказывайте!", "Хобби", None),
    ("sports", "⚽ Братва, в какой спорт любите играть сами — пишите в комментах!", "Спорт", None),
    ("childhood", "🪁 Пацаны, во что играли во дворе в детстве — вспоминаем!", "Детство", None),
    ("music_city", "🎤 Народ, какую песню включили бы на весь Новосибирск?", "Музыка", None),
    ("favorite_food", "🍔 Братва, какое блюдо готовы есть хоть каждый день?", "Еда", None),
    ("cooking_challenge", "👨‍🍳 Пацаны, кто умеет приготовить борщ — признавайтесь в комментах!", "Рецепты", None),
    ("pizza", "🍕 Родные, пицца с ананасами — нормальная тема или мимо?", "Еда", None),
    ("tea", "🫖 Братва, чай с лимоном или с вареньем — ваш выбор?", "Чаепитие", None),
    ("shawarma", "🌯 Народ, где в Новосибирске берёте самую вкусную шаурму?", "Еда", None),
    ("transport", "🚌 Пацаны, на чём удобнее передвигаться по Новосибирску — автобус, авто или пешком?", "Транспорт", None),
    ("morning_drive", "🚗 Братва, за рулём предпочитаете музыку или полную тишину?", "Авто", None),
    ("funny_city", "😂 Народ, какая самая смешная история случалась с вами в Новосибирске?", "Истории", None),
    ("city_good", "❤️ Братва, за что вы больше всего любите Новосибирск?", "НашГород", None),
    ("city_change", "🛠️ Пацаны, что бы первым делом улучшили в Новосибирске?", "Идеи", None),
    ("neighbors", "🏡 Родные, вы знакомы со своими соседями — расскажите в комментах!", "Соседи", None),
    ("good_deed", "🙌 Народ, какое доброе дело вам запомнилось больше всего?", "Добро", None),
    ("favorite_number", "🔢 Пацаны, назовите число от 1 до 100 — проверим, какое популярнее!", "Игра", None),
    ("three_words", "💬 Братва, опишите Новосибирск тремя словами — погнали!", "Игра", None),
    ("emoji_game", "🎲 Родные, опишите настроение одним эмодзи — читаем комменты!", "Игра", None),
    ("two_choices", "⚡ Народ, гулять по центру или выбраться на природу — кто за что?", "Выбор", None),
    ("book", "📚 Братва, какую книгу точно стоит прочитать — советуйте в комментах!", "Книги", None),
    ("local_memory", "📷 Пацаны, какое место Новосибирска напоминает вам о детстве?", "Воспоминания", None),
    ("friends", "🤗 Народ, где в Новосибирске лучше встретиться с друзьями?", "Встречи", None),
    ("dream_visit", "✈️ Братва, куда мечтаете съездить из Новосибирска на выходные?", "Путешествия", None),
]


def game_draft(history, now):
    """Returns a new question or None; rate-limited, daytime-only, no recent repeats."""
    local = now.astimezone(TZ)
    if not 8 <= local.hour < 23:
        return None
    posts = history.get("posts", [])
    game_posts = [p for p in posts if p.get("kind") == "game"]
    today = str(local.date())
    if sum(p.get("slot", "").startswith(today) for p in game_posts) >= MAX_GAMES_PER_DAY:
        return None

    recent_keys = set()
    for p in game_posts:
        try:
            stamp = datetime.fromisoformat(p["published_at"])
            if stamp.tzinfo is None:
                continue
            age = now - stamp
            if timedelta() <= age < MIN_GAME_INTERVAL:
                return None
            if timedelta() <= age < timedelta(days=NO_REPEAT_DAYS):
                recent_keys.add(p.get("game_key"))
        except (ValueError, TypeError, KeyError):
            continue

    eligible = [p for p in PROMPTS
                if p[0] not in recent_keys
                and not mentions_missing_media(p[1])
                and (p[3] is None or p[3][0] <= local.hour < p[3][1])]
    if not eligible:
        return None
    # Prefer a timely meal/morning/evening question over a generic one.
    specialized = [p for p in eligible if p[3] is not None]
    options = specialized or eligible
    def order(p):
        return hashlib.sha256((today + "|" + p[0]).encode("utf-8")).hexdigest()
    key, sentence, topic, _ = min(options, key=order)

    # Reuse clear topic hashtags instead of appending dates or numeric IDs.
    tags = ["#Новосибирск" + suffix for suffix in (topic, "Общение", "Комменты")]
    return {"publish": True, "sentence": sentence, "hashtags": tags, "game_key": key}
