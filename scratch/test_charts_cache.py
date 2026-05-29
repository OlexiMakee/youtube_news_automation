import os
import sys
import time
import unittest

# Add root dir to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import news_scraper.utils as utils
utils.load_env()

from app import create_app
from app.routes.charts import CHARTS_CACHE
from news_scraper.db_client import DatabaseClient

class TestChartsCache(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        
    def test_charts_cache_flow(self):
        print("[*] Testing charts API cache flow...")
        
        # Clear cache first
        CHARTS_CACHE.clear()
        
        # Measure first call (should hit the DB)
        start = time.time()
        res1 = self.client.get('/api/charts?channel_id=all&limit=10')
        duration1 = time.time() - start
        self.assertEqual(res1.status_code, 200)
        print(f"    First call (cache miss) duration: {duration1:.4f} seconds")
        
        # Verify cache is populated
        self.assertTrue(len(CHARTS_CACHE) > 0)
        
        # Measure second call (should hit the cache)
        start = time.time()
        res2 = self.client.get('/api/charts?channel_id=all&limit=10')
        duration2 = time.time() - start
        self.assertEqual(res2.status_code, 200)
        print(f"    Second call (cache hit) duration: {duration2:.4f} seconds")
        
        # The cache hit should be virtually instantaneous (< 0.05 seconds)
        self.assertTrue(duration2 < duration1)
        self.assertTrue(duration2 < 0.05)
        
        # Verify responses are identical
        self.assertEqual(res1.get_json(), res2.get_json())
        
        # Test invalidation: update database file modification time manually
        # by executing a dummy write or changing database state
        print("[*] Testing database modification invalidation...")
        db_client = DatabaseClient()
        conn = db_client.get_connection()
        cursor = conn.cursor()
        
        # Run a transaction to trigger DB file change
        cursor.execute("CREATE TABLE IF NOT EXISTS _test_dummy (id INTEGER PRIMARY KEY);")
        conn.commit()
        
        # Force modify file mtime to make sure SQLite and system see the update
        db_path = db_client.db_path
        os.utime(db_path, None)
        
        # Run a third call: should be a cache miss
        start = time.time()
        res3 = self.client.get('/api/charts?channel_id=all&limit=10')
        duration3 = time.time() - start
        self.assertEqual(res3.status_code, 200)
        print(f"    Third call (after DB write, cache miss) duration: {duration3:.4f} seconds")
        
        # Clean up
        cursor.execute("DROP TABLE IF EXISTS _test_dummy;")
        conn.commit()
        db_client.close_connection(conn)

if __name__ == '__main__':
    unittest.main()
