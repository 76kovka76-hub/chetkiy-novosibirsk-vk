"""Send one actual Novosibirsk VK welcome post and record it to prevent duplicates."""
import logging
from datetime import datetime, timezone
from main import GROUP_ID, history_load, history_save, format_message, post_vk, slot

ONE_TIME_KEY = "novosibirsk_welcome_first_2026"
DRAFT = {
    "publish": True,
    "sentence": "❄️ Братва, «Чёткий Новосибирск» на связи — кто из какого района, пишите в комменты!",
    "hashtags": ["#НовосибирскНаСвязи", "#НовосибирскЗнакомимся", "#НовосибирскНашЧат"],
}


def main():
    now = datetime.now(timezone.utc)
    time_slot = slot(now)
    history = history_load()
    if any(p.get("game_key") == ONE_TIME_KEY for p in history["posts"]):
        logging.info("Приветственный пост уже опубликован. Повтора не будет.")
        return
    if any(p.get("slot") == time_slot for p in history["posts"]):
        logging.info("48-минутный слот уже занят — не публикуем второй пост.")
        return
    if sum(str(p.get("slot", "")).startswith(time_slot[:10]) for p in history["posts"]) >= 30:
        logging.info("Достигнут суточный предел в 30 постов.")
        return
    message = format_message(DRAFT, history)
    if not message:
        raise RuntimeError("Приветственный пост не прошёл форматную проверку или повторяются хэштеги")
    post_id = post_vk(message, "one-time-nsk-welcome-2026")
    history["posts"].append({
        "slot": time_slot,
        "post_id": post_id,
        "kind": "game",
        "game_key": ONE_TIME_KEY,
        "title": "Приветствие и знакомство",
        "text": DRAFT["sentence"],
        "published_at": now.isoformat()
    })
    history["used_tags"].extend(DRAFT["hashtags"])
    history_save(history)
    logging.info("ПЕРВЫЙ ПОСТ ВК ОПУБЛИКОВАН: https://vk.com/wall-%s_%s", GROUP_ID, post_id)


if __name__ == "__main__":
    main()
