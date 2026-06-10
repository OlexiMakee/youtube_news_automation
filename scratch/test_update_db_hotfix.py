import unittest
from unittest.mock import MagicMock, patch

class TestUpdateDbHotfix(unittest.TestCase):
    @patch("update_db.YouTubeScraperEngine")
    @patch("update_db.cli_progress")
    @patch("update_db.db_client")
    def test_update_channel_via_scraping_no_progress_kwargs(self, mock_db, mock_cli, mock_engine_cls):
        # Setup mock
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        
        # Import the function to test
        import update_db
        
        # Run
        result = update_db.update_channel_via_scraping("test_channel", set(), True)
        
        # Verify run_archive_scraping was called with ONLY stop_on_known=True
        mock_engine.run_archive_scraping.assert_called_once_with(stop_on_known=True)

if __name__ == "__main__":
    unittest.main()
