import os
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from app.services.governance import _connect

KEY_FILE_NAME = "secrets_master.key"

def _resolve_master_key(root_dir: str) -> str:
    """Resolve encryption master key: 1) Env var 2) local file 3) auto-generate."""
    key = os.environ.get("SOURCES_ENCRYPTION_KEY")
    if key:
        return key.strip()
        
    key_path = Path(root_dir) / "data" / KEY_FILE_NAME
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()
        
    new_key = Fernet.generate_key().decode()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(new_key, encoding="utf-8")
    return new_key

def encrypt_secret(plaintext: str, key: str) -> str:
    """Encrypt a secret string using Fernet."""
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.encrypt(plaintext.encode("utf-8")).decode()

def decrypt_secret(ciphertext: str, key: str) -> str:
    """Decrypt a secret string using Fernet."""
    f = Fernet(key.encode() if isinstance(key, str) else key)
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

def store_credential(source_id: int, secret_value: str, root_dir: str) -> bool:
    """Store encrypted secret in source_credentials table."""
    if not secret_value:
        return False
    master_key = _resolve_master_key(root_dir)
    ciphertext = encrypt_secret(secret_value, master_key)
    
    conn = _connect(root_dir)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM source_credentials WHERE source_id = ?", (source_id,))
        cursor.execute(
            """
            INSERT INTO source_credentials (source_id, secret_ref, byok, rotation_status)
            VALUES (?, ?, ?, ?)
            """,
            (source_id, ciphertext, 1, "not_required")
        )
        conn.commit()

        from app.services.governance import add_audit_event
        add_audit_event(
            root_dir=root_dir,
            action="credential.stored",
            object_type="source",
            object_id=source_id,
            metadata={"byok": 1}
        )
        return True
    finally:
        conn.close()

def get_decrypted_credential(source_id: int, root_dir: str) -> Optional[str]:
    """Retrieve and decrypt secret for a source."""
    conn = _connect(root_dir)
    try:
        row = conn.execute(
            "SELECT secret_ref FROM source_credentials WHERE source_id = ?",
            (source_id,)
        ).fetchone()
        if not row:
            return None
        ciphertext = row["secret_ref"]
        master_key = _resolve_master_key(root_dir)
        return decrypt_secret(ciphertext, master_key)
    finally:
        conn.close()
