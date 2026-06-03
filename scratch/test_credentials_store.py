import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.fernet import Fernet
from app.services.credentials import (
    _resolve_master_key,
    encrypt_secret,
    decrypt_secret,
    store_credential,
    get_decrypted_credential
)

class TestCredentialsStore(unittest.TestCase):

    def setUp(self):
        # Create temp folder for DB and secret files
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_sources.db"
        
        # Patch db_path_for_root in app.services.governance
        from app.services import governance
        self.original_db_path_for_root = governance.db_path_for_root
        governance.db_path_for_root = lambda root: self.db_path
        self.addCleanup(lambda: setattr(governance, "db_path_for_root", self.original_db_path_for_root))
        
        # Connect to trigger auto-initialization of governance tables
        conn = governance._connect(self.test_dir)
        try:
            # Create a test source record
            conn.execute("INSERT INTO sources (id, type, name, policy_tier, status) VALUES (1, 'youtube', 'Test Source', 'A', 'active')")
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_key_resolution_env(self):
        """Verify master key is read from the environment variable if present."""
        test_key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"SOURCES_ENCRYPTION_KEY": test_key}):
            resolved_key = _resolve_master_key(self.test_dir)
            self.assertEqual(resolved_key, test_key)

    def test_key_resolution_file(self):
        """Verify master key fallback to local file."""
        test_key = Fernet.generate_key().decode()
        key_file = Path(self.test_dir) / "data" / "secrets_master.key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(test_key, encoding="utf-8")
        
        with patch.dict(os.environ, {}):
            resolved_key = _resolve_master_key(self.test_dir)
            self.assertEqual(resolved_key, test_key)

    def test_key_resolution_generate(self):
        """Verify master key is auto-generated if both env and file are missing."""
        key_file = Path(self.test_dir) / "data" / "secrets_master.key"
        self.assertFalse(key_file.exists())
        
        with patch.dict(os.environ, {}):
            resolved_key = _resolve_master_key(self.test_dir)
            self.assertTrue(key_file.exists())
            self.assertEqual(resolved_key, key_file.read_text(encoding="utf-8").strip())

    def test_encrypt_decrypt(self):
        """Verify symmetry of encryption and decryption."""
        key = Fernet.generate_key().decode()
        secret = "super_secret_value_123"
        
        ciphertext = encrypt_secret(secret, key)
        self.assertNotEqual(ciphertext, secret)
        
        plaintext = decrypt_secret(ciphertext, key)
        self.assertEqual(plaintext, secret)

    def test_db_store_retrieve(self):
        """Verify credentials storing and retrieval from database."""
        secret = "my_api_key_12345"
        
        # Store
        success = store_credential(1, secret, self.test_dir)
        self.assertTrue(success)
        
        # Retrieve and decrypt
        decrypted = get_decrypted_credential(1, self.test_dir)
        self.assertEqual(decrypted, secret)
