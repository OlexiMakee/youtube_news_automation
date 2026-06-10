import unittest


class NewsScraperNamespaceTest(unittest.TestCase):
    def test_compatibility_namespace_exposes_scraper_modules(self):
        from news_scraper.db_client import DatabaseClient
        from news_scraper.postgres_sync import PostgresSyncClient
        from news_scraper.connectors import create_connector, list_connector_metadata

        self.assertIsNotNone(DatabaseClient)
        self.assertIsNotNone(PostgresSyncClient)
        self.assertTrue(callable(create_connector))
        self.assertTrue(callable(list_connector_metadata))


if __name__ == "__main__":
    unittest.main()
