"""
Database synchronization module with Kaggle (kaggle_sync.py).

This module enables automated or manual synchronization of the local SQLite database
with a cloud private dataset on Kaggle. It compares file sizes and modification dates
to make a smart decision regarding the sync direction.
"""

import os
import shutil
import datetime
from scraper.utils import load_env

# Load environment variables from .env BEFORE importing Kaggle SDK libraries
# to prevent them from initializing with empty/invalid tokens.
load_env()

from kagglesdk import KaggleClient
from kagglesdk.datasets.types.dataset_api_service import ApiGetDatasetRequest, ApiListDatasetFilesRequest
import kagglehub


def check_and_setup_kaggle_auth(silent=False):
    """
    Checks if Kaggle credentials are set and compatible with the current Python version.
    If missing or incompatible, attempts to import kaggle.json from root,
    or prompt the user interactively (if stdin is a tty).
    """
    import sys
    import json
    from scraper.utils import write_env, load_env
    
    # 1. Determine compatibility requirements
    py_version = sys.version_info
    is_legacy_python = py_version.major < 3 or (py_version.major == 3 and py_version.minor < 10)
    
    # Reload environment to ensure we have the latest variables from .env
    load_env()
    
    def check_env_auth():
        usr = os.environ.get("KAGGLE_USERNAME")
        key = os.environ.get("KAGGLE_KEY")
        token = os.environ.get("KAGGLE_API_TOKEN")
        
        is_token_new = bool(token and token.startswith("KGAT_"))
        is_key_new = bool(key and key.startswith("KGAT_"))
        is_new_cred = is_token_new or is_key_new
        
        has_credentials = bool((usr and key) or token)
        
        if not has_credentials:
            return False, "missing"
            
        if is_legacy_python:
            is_legacy_key = bool(key and not key.startswith("KGAT_") and len(key) == 32)
            if usr and is_legacy_key:
                return True, "legacy"
            else:
                return False, "incompatible_new_on_legacy_python"
        else:
            if is_new_cred:
                return True, "new"
            else:
                return True, "legacy"

    # Verify existing environment
    is_ok, auth_type = check_env_auth()
    if is_ok:
        return True
        
    # 2. Try to read kaggle.json from the root directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kaggle_json_path = os.path.join(root_dir, "kaggle.json")
    
    if os.path.exists(kaggle_json_path):
        if not silent:
            print(f"[*] Found kaggle.json at {kaggle_json_path}. Importing...")
        try:
            with open(kaggle_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            username = data.get("username", "").strip()
            key = data.get("key", "").strip()
            
            if username and key:
                write_env({
                    "KAGGLE_USERNAME": username,
                    "KAGGLE_KEY": key,
                    "KAGGLE_API_TOKEN": key
                })
                if not silent:
                    print("[+] Successfully imported credentials from kaggle.json to .env")
                
                # Delete the temporary file
                try:
                    os.remove(kaggle_json_path)
                    if not silent:
                        print("[+] Deleted temporary kaggle.json")
                except Exception as ex:
                    if not silent:
                        print(f"[!] Warning: Could not delete kaggle.json: {ex}")
                        
                # Re-verify after import
                is_ok, auth_type = check_env_auth()
                if is_ok:
                    return True
            else:
                if not silent:
                    print("[!] Error: kaggle.json is missing 'username' or 'key'.")
        except Exception as e:
            if not silent:
                print(f"[!] Error reading kaggle.json: {e}")

    # 3. If credentials are still invalid/missing, prompt the user if we are in an interactive session
    if sys.stdin.isatty():
        print("\n" + "=" * 60)
        print(f"{'KAGGLE CREDENTIALS SETUP':^60}")
        print("=" * 60)
        print(f"Python version detected: {sys.version.split()[0]}")
        
        if is_legacy_python:
            if auth_type == "incompatible_new_on_legacy_python":
                print("[WARNING] Your .env contains a new token (starts with KGAT_)")
                print("but your Python version is < 3.10, which cannot upload files using it.")
            else:
                print("[WARNING] Kaggle credentials are missing or incomplete in your .env.")
            print("Please provide legacy credentials (Username and 32-character hex API Key).")
            print("You can get them from Kaggle -> Account -> 'Create New API Token'.")
            print("-" * 60)
            username = input("Enter Kaggle Username: ").strip()
            key = input("Enter Kaggle API Key (32-hex): ").strip()
            
            if username and key:
                write_env({
                    "KAGGLE_USERNAME": username,
                    "KAGGLE_KEY": key,
                    "KAGGLE_API_TOKEN": key
                })
                print("[+] Credentials successfully saved to .env")
                return True
            else:
                print("[!] Error: Username and Key cannot be empty.")
                return False
        else:
            print("Your Python version supports both legacy and new Kaggle credentials.")
            print("Choose credential type to enter:")
            print("1. New API Token (starts with 'KGAT_')")
            print("2. Legacy Credentials (Username + API Key)")
            choice = input("Enter choice (1-2): ").strip()
            
            if choice == "1":
                token = input("Enter Kaggle API Token (KGAT_...): ").strip()
                if token:
                    write_env({
                        "KAGGLE_API_TOKEN": token
                    })
                    print("[+] Token successfully saved to .env")
                    return True
            elif choice == "2":
                username = input("Enter Kaggle Username: ").strip()
                key = input("Enter Kaggle API Key: ").strip()
                if username and key:
                    write_env({
                        "KAGGLE_USERNAME": username,
                        "KAGGLE_KEY": key,
                        "KAGGLE_API_TOKEN": key
                    })
                    print("[+] Credentials successfully saved to .env")
                    return True
            print("[!] Error: Invalid selection or empty input.")
            return False
    else:
        if not silent:
            print("[!] Error: Kaggle credentials are missing or incompatible, and terminal is not interactive.")
            if is_legacy_python:
                print("    Please set KAGGLE_USERNAME and KAGGLE_KEY (32-hex legacy key) in your .env file.")
            else:
                print("    Please set KAGGLE_API_TOKEN (new KGAT_ token) or legacy variables in your .env file.")
        return False


def get_sync_status(db_path, dataset_handle="oleximakee/youtube-news-automation"):
    """
    Collects metadata from the local database and the cloud dataset without downloading the file.
    Returns structured data for statistics rendering.
    """
    load_env()
    
    # Status results dictionary
    status = {
        "local_exists": False,
        "local_size": None,
        "local_mtime": None,
        "cloud_exists": False,
        "cloud_size": None,
        "cloud_mtime": None,
        "recommendation": "Not determined",
        "direction": "none",
        "error": None
    }
    
    # 1. Local file verification
    if os.path.exists(db_path):
        status["local_exists"] = True
        status["local_size"] = os.path.getsize(db_path)
        mtime_epoch = os.path.getmtime(db_path)
        # Convert local epoch time to naive UTC datetime for comparison with Kaggle
        status["local_mtime"] = datetime.datetime.fromtimestamp(mtime_epoch, tz=datetime.timezone.utc).replace(tzinfo=None)

    # 2. Token verification
    if not check_and_setup_kaggle_auth(silent=True):
        status["error"] = "Kaggle credentials not configured properly for this Python version"
        status["recommendation"] = "Set API token / Credentials"
        return status

    # 3. Cloud dataset verification
    try:
        client = KaggleClient()
        owner, slug = dataset_handle.split("/", 1)
        
        # Fetch dataset metadata
        req_dataset = ApiGetDatasetRequest()
        req_dataset.owner_slug = owner
        req_dataset.dataset_slug = slug
        dataset_info = client.datasets.dataset_api_client.get_dataset(req_dataset)
        
        status["cloud_exists"] = True
        status["cloud_mtime"] = dataset_info.last_updated
        status["cloud_size"] = dataset_info.total_bytes # Default fallback value
        
        # Search for the specific database file inside the dataset to get a precise size
        try:
            req_files = ApiListDatasetFilesRequest()
            req_files.owner_slug = owner
            req_files.dataset_slug = slug
            files_response = client.datasets.dataset_api_client.list_dataset_files(req_files)
            
            db_filename = os.path.basename(db_path)
            for f in files_response.dataset_files:
                if f.name == db_filename:
                    status["cloud_size"] = f.total_bytes
                    if f.creation_date:
                        status["cloud_mtime"] = f.creation_date
                    break
        except Exception:
            # Fall back to the total dataset size if file listing fails
            pass
            
    except Exception as e:
        # 403 Forbidden or 404 generally mean the dataset does not exist or access is denied
        status["cloud_exists"] = False
        status["error_detail"] = str(e)

    # 4. Determine recommendation
    if not status["cloud_exists"]:
        if status["local_exists"]:
            status["recommendation"] = "Create Kaggle dataset and upload local database"
            status["direction"] = "upload"
        else:
            status["recommendation"] = "Create a local database first (run scraper)"
            status["direction"] = "none"
    elif not status["local_exists"]:
        status["recommendation"] = "Download database from Kaggle to local machine"
        status["direction"] = "download"
    else:
        # Compare update times (UTC naive datetimes)
        # Apply a 2-second tolerance threshold to avoid micro-adjustments
        time_diff = (status["cloud_mtime"] - status["local_mtime"]).total_seconds()
        
        if time_diff > 2:
            status["recommendation"] = f"Download from Cloud (Cloud is newer by {format_time_diff(time_diff)})"
            status["direction"] = "download"
        elif time_diff < -2:
            status["recommendation"] = f"Upload to Cloud (Local file is newer by {format_time_diff(-time_diff)})"
            status["direction"] = "upload"
        else:
            status["recommendation"] = "Databases are fully synchronized"
            status["direction"] = "sync"
            
    return status


def format_time_diff(seconds):
    """Formats time difference for display."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{int(hours)}h {int(mins)}m"


def sync_db_with_kaggle(db_path, dataset_handle="oleximakee/youtube-news-automation", direction="smart", silent=False):
    """
    Executes synchronization based on direction:
    - smart: comparison based on modification times
    - upload: force upload local file to Kaggle
    - download: force download cloud file to local
    """
    load_env()
    
    if not check_and_setup_kaggle_auth(silent=silent):
        if not silent:
            print("[!] Error: Kaggle authentication credentials are not configured properly.")
        return False
        
    if direction == "smart":
        status = get_sync_status(db_path, dataset_handle)
        if status["direction"] == "none":
            if not silent:
                print(f"[i] Sync unavailable: {status['recommendation']}")
            return False
        elif status["direction"] == "sync":
            if not silent:
                print("[+] Sync not required: databases match.")
            return True
        direction = status["direction"]
        
    if direction == "download":
        return _download_db(db_path, dataset_handle, silent)
    elif direction == "upload":
        return _upload_db(db_path, dataset_handle, silent)
    else:
        if not silent:
            print(f"[!] Error: Unknown sync direction '{direction}'")
        return False


def _download_db(db_path, dataset_handle, silent=False):
    try:
        if not silent:
            print(f"[*] Downloading database from Kaggle ({dataset_handle})...")
            
        # Download dataset via kagglehub
        download_dir = kagglehub.dataset_download(dataset_handle, force_download=True)
        
        db_filename = os.path.basename(db_path)
        downloaded_file = os.path.join(download_dir, db_filename)
        
        # If the exact filename was not found, search for any file ending with .db
        if not os.path.exists(downloaded_file):
            db_files = [f for f in os.listdir(download_dir) if f.endswith(".db")]
            if db_files:
                downloaded_file = os.path.join(download_dir, db_files[0])
            else:
                if not silent:
                    print("[!] Error: No database file (.db) found in the downloaded dataset.")
                return False
                
        # Create output directory for local database if missing
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Copy file to the destination
        shutil.copy2(downloaded_file, db_path)
        
        # Set local modification time to match the cloud version last updated time
        _align_local_mtime_with_cloud(db_path, dataset_handle)
        
        if not silent:
            print(f"[+] Database successfully downloaded and saved to '{db_path}'.")
        return True
    except Exception as e:
        if not silent:
            print(f"[!] Error downloading database: {e}")
        return False


def _upload_db(db_path, dataset_handle, silent=False):
    if not os.path.exists(db_path):
        if not silent:
            print(f"[!] Error: Local file '{db_path}' does not exist to upload.")
        return False

    db_dir = os.path.dirname(db_path)
    temp_dir = os.path.join(db_dir, "_kaggle_upload_temp")
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Copy only the database file to the temporary directory
        db_filename = os.path.basename(db_path)
        shutil.copy2(db_path, os.path.join(temp_dir, db_filename))
        
        if not silent:
            print(f"[*] Uploading database to Kaggle ({dataset_handle})...")
            
        # Upload to Kaggle. kagglehub automatically creates a private dataset
        # if it doesn't exist, or uploads a new version if it does.
        kagglehub.dataset_upload(
            handle=dataset_handle,
            local_dataset_dir=temp_dir,
            version_notes=f"Automated database update: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Set local modification time to match the cloud version last updated time
        _align_local_mtime_with_cloud(db_path, dataset_handle)
        
        if not silent:
            print("[+] Database successfully updated on Kaggle.")
        return True
    except Exception as e:
        if not silent:
            print(f"[!] Error uploading database: {e}")
        return False
    finally:
        # Clean up temporary folder
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


def _align_local_mtime_with_cloud(db_path, dataset_handle):
    """
    Fetches the actual modification time on Kaggle and sets the local file's
    mtime attributes to match. Prevents repeated false-positive comparisons.
    """
    try:
        client = KaggleClient()
        owner, slug = dataset_handle.split("/", 1)
        req = ApiGetDatasetRequest()
        req.owner_slug = owner
        req.dataset_slug = slug
        dataset_info = client.datasets.dataset_api_client.get_dataset(req)
        cloud_mtime = dataset_info.last_updated
        
        # Attempt to get a more precise file modification timestamp
        try:
            req_files = ApiListDatasetFilesRequest()
            req_files.owner_slug = owner
            req_files.dataset_slug = slug
            files_response = client.datasets.dataset_api_client.list_dataset_files(req_files)
            db_filename = os.path.basename(db_path)
            for f in files_response.dataset_files:
                if f.name == db_filename and f.creation_date:
                    cloud_mtime = f.creation_date
                    break
        except Exception:
            pass
            
        if cloud_mtime:
            # Convert naive UTC datetime to local timestamp
            cloud_mtime_local = cloud_mtime.replace(tzinfo=datetime.timezone.utc).astimezone(None)
            epoch_time = cloud_mtime_local.timestamp()
            os.utime(db_path, (epoch_time, epoch_time))
    except Exception:
        # Non-critical if timestamp synchronization fails
        pass
