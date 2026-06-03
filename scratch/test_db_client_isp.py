import os
import sys
import unittest
from pathlib import Path

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from scraper.db_client import (
    BaseStorage,
    IChannelRepository,
    IVideoRepository,
    ISyncCoordinator,
    DatabaseClient,
)


class TestDatabaseClientISP(unittest.TestCase):
    def test_db_client_inheritance(self):
        # Verify interfaces exist and BaseStorage inherits them
        self.assertTrue(issubclass(BaseStorage, IChannelRepository))
        self.assertTrue(issubclass(BaseStorage, IVideoRepository))
        self.assertTrue(issubclass(BaseStorage, ISyncCoordinator))

        # Verify DatabaseClient inherits them
        self.assertTrue(issubclass(DatabaseClient, BaseStorage))
        self.assertTrue(issubclass(DatabaseClient, IChannelRepository))
        self.assertTrue(issubclass(DatabaseClient, IVideoRepository))
        self.assertTrue(issubclass(DatabaseClient, ISyncCoordinator))

    def test_db_client_instance_implements_interfaces(self):
        client = DatabaseClient(db_path=":memory:")
        
        self.assertTrue(isinstance(client, BaseStorage))
        self.assertTrue(isinstance(client, IChannelRepository))
        self.assertTrue(isinstance(client, IVideoRepository))
        self.assertTrue(isinstance(client, ISyncCoordinator))


if __name__ == "__main__":
    unittest.main()
