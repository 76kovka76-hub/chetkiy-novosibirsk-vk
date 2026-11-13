"""Conservative checks for RSS headlines used as text-only VK news.

These rules reject common media hooks, clickbait and incomplete fragments.
They are not a substitute for full semantic verification by an editor.
"""
import re
from urllib.parse import urlsplit

_MEDIA = re.compile(
    r"\b(?:видео|видеоролик\w*|видеозапис\w*|"
    r"фото|фотк\w*|фотографи\w*|фоторепортаж\w*|"
    r"кадры|кадров|кадрах|кадрами|снимки|снимков|снимках|снимок|"
    r"ролик\w*|галере\w*|картинк\w*|иллюстраци\w*|"
    r"трансляци\w*)\b",
    flags=re.IGNORECASE,
)
_MEDIA_CTA = re.compile(
    r"\b(?:смотрите|посмотрите|взгляните|листайте|показываем|"
    r"послушайте|слушайте|покажите|показывайте|гляньте|показано|показали\s+как)\b",
    flags=re.IGNORECASE,
)
_CLIFFHANGER = re.compile(
    r"\b(?:стало\s+известно|выяснилось|"
    r"вот\s+(?:что|как|почему|где)|"
    r"подробност\w*|читайте|узнайте|рассказываем|"
    r"в\s+(?:нашем\s+)?материале|по\s+ссылке|"
    r"продолжение\s+следует|все\s+детали|"
    r"всё\s+самое\s+интересное)\b",
    flags=re.IGNORECASE,
)
_UNANSWERED = re.compile(
    r"(?:^|[\s,:—-])(?:почему|зачем|сколько|когда|где|"
    r"какие|какой|какая|какое|как|куда|кто|что)\b",
    flags=re.IGNORECASE,
)
_UNFINISHED_END = re.compile(
    r"(?:\.\.\.|…|[,;:—-]|\b(?:но|и|или|что|как|из-за|"
    r"потому|для|на|в|по|от|до|с|о))\s*$",
    flags=re.IGNORECASE,
)
# Heuristic that the headline reports an actual action/result rather than a label.
_PREDICATE = re.compile(
    r"\b[а-яё]{3,}(?:ли|ла|ло|л|ют|ут|ят|ат|ет|ит|ёт|"
    r"ются|ется|ится|лся|лась|лись)\b",
    flags=re.IGNORECASE,
)


def mentions_missing_media(text: str) -> bool:
    value = (text or "").strip()
    return bool(_MEDIA.search(value) or _MEDIA_CTA.search(value))


def source_url(value: str) -> str | None:
    """Only allow a plain usable HTTP(S) URL from the RSS entry."""
    if not isinstance(value, str):
        return None
    url = value.strip()
    if not url or len(url) > 2048 or any(c.isspace() for c in url):
        return None
    try:
        parts = urlsplit(url)
        if (parts.scheme not in ("http", "https") or not parts.hostname
                or parts.username or parts.password):
            return None
    except ValueError:
        return None
    return url


def is_self_contained_news(title: str) -> bool:
    """Fail conservatively when a bare headline cannot stand as a text-only news item."""
    if not isinstance(title, str):
        return False
    text = re.sub(r"\s+", " ", title).strip().strip("«»\" ")
    words = re.findall(r"[а-яёa-z0-9]+", text, re.IGNORECASE)
    if not 45 <= len(text) <= 300 or len(words) < 7:
        return False
    if mentions_missing_media(text) or _CLIFFHANGER.search(text):
        return False
    if "?" in text or "!" in text or _UNFINISHED_END.search(text):
        return False
    if _UNANSWERED.search(text):
        return False
    # A bare list or teaser is not a news report.
    if not _PREDICATE.search(text):
        return False
    return True
