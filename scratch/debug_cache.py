import os
import sys
import time

# Add root dir to sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import scraper.utils as utils
utils.load_env()

from app import create_app
from app.routes.charts import get_db_mtime, CHARTS_CACHE

app = create_app()
client = app.test_client()

print("--- DEBUGGING CHARTS CACHE ---")
mtime_start = get_db_mtime()
print(f"Start db mtime: {mtime_start}")

# First call
start = time.time()
res1 = client.get('/api/charts?channel_id=all&limit=10')
duration1 = time.time() - start
print(f"Call 1 duration: {duration1:.4f} seconds")

mtime_mid = get_db_mtime()
print(f"Mid db mtime: {mtime_mid}")
print(f"Is same mtime after read? {mtime_start == mtime_mid}")

# Let's inspect cache
print(f"Cache keys: {list(CHARTS_CACHE.keys())}")
if CHARTS_CACHE:
    for k, v in CHARTS_CACHE.items():
        print(f"  Key: {k}, cached_mtime: {v[1]}, age: {time.time() - v[2]:.4f}s")

# Second call
start = time.time()
res2 = client.get('/api/charts?channel_id=all&limit=10')
duration2 = time.time() - start
print(f"Call 2 duration: {duration2:.4f} seconds")

mtime_end = get_db_mtime()
print(f"End db mtime: {mtime_end}")
print(f"Is same mtime after call 2? {mtime_mid == mtime_end}")
