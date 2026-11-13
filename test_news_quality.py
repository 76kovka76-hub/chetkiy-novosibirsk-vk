"""Text-only editorial gate tests, all offline."""
import unittest
import main
from news_quality import is_self_contained_news, mentions_missing_media, source_url


class NewsQualityTests(unittest.TestCase):
    def test_good_news_stands_alone(self):
        for headline in (
            "В Новосибирске перекроют дорогу на улице Ленина из-за ремонта",
            "В Краснодаре открыли новый мост через реку Кубань после ремонта",
            "София Молчанова из Екатеринбурга завоевала золото чемпионата России по плаванию",
            "В Новосибирске запустят автобус по обновлённому маршруту с понедельника",
            "АвтоВАЗ запустит производство новой модели Lada в Тольятти в 2027 году",
        ):
            with self.subTest(headline=headline):
                self.assertTrue(is_self_contained_news(headline))

    def test_media_dependent_copy_is_rejected(self):
        for headline in (
            "В Краснодаре появилось видео аварии на центральной улице города",
            "В Новосибирске показали фото обновлённого парка после ремонта",
            "В Новосибирске появились кадры с места дорожного происшествия",
            "В Екатеринбурге открыли парк, смотрите как он выглядит",
            "На автомобильной выставке показали снимки новой модели машины",
        ):
            with self.subTest(headline=headline):
                self.assertTrue(mentions_missing_media(headline))
                self.assertFalse(is_self_contained_news(headline))

    def test_unfinished_clickbait_is_rejected(self):
        for headline in (
            "Стало известно, какие улицы отремонтируют в Краснодаре",
            "В Новосибирске рассказали, что произойдёт с тарифами на воду",
            "Почему в Екатеринбурге выросли цены на новые автомобили",
            "В Новосибирске произошла авария — подробности читайте в материале",
            "Автомобильная компания представила новинку — вот что известно",
            "В Краснодаре откроют новую улицу для движения, но",
            "В Новосибирске открыли ещё одну дорогу...",
        ):
            with self.subTest(headline=headline):
                self.assertFalse(is_self_contained_news(headline))

    def test_valid_source_link(self):
        self.assertEqual(source_url("https://example.com/news/123"), "https://example.com/news/123")
        for url in ("javascript:alert(1)", "file:///etc/passwd", "", "https://example.com/a b"):
            self.assertIsNone(source_url(url))


if __name__ == "__main__":
    unittest.main()


class PublicationIntegrationTests(unittest.TestCase):
    def test_city_story_has_complete_text_and_source(self):
        item = {
            "title": "В Новосибирске открыли новый мост через реку после завершения ремонта",
            "link": "https://example.org/news/bridge",
        }
        draft = main.offline_draft(item, {"posts": [], "used_tags": []})
        self.assertTrue(draft["publish"])
        self.assertIn("Источник: https://example.org/news/bridge",
                      main.format_message(draft, {"used_tags": []}))

    def test_city_story_without_conclusion_is_skipped(self):
        item = {
            "title": "В Новосибирске рассказали, что будет с дорогами после ремонта",
            "link": "https://example.org/news/teaser",
        }
        self.assertFalse(main.offline_draft(item, {"posts": [], "used_tags": []})["publish"])

    def test_no_media_references_even_in_game_drafts(self):
        game = {
            "publish": True,
            "sentence": "📷 Народ, смотрите фото обновлённого парка!",
            "hashtags": ["#НовосибирскГород", "#НовосибирскСобытия", "#НовосибирскРайоны"],
        }
        self.assertIsNone(main.format_message(game, {"used_tags": []}))
