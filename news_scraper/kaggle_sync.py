"""
Модуль синхронізації бази даних з Kaggle (kaggle_sync.py).

Цей модуль дозволяє автоматично або примусово синхронізувати локальну базу даних SQLite
із хмарним приватним датасетом на Kaggle. Він порівнює розміри та дати змін файлів
і робить розумний вибір щодо напрямку синхронізації.
"""

import os
import shutil
import datetime
from kagglesdk import KaggleClient
from kagglesdk.datasets.types.dataset_api_service import ApiGetDatasetRequest, ApiListDatasetFilesRequest
import kagglehub
from news_scraper.utils import load_env

def get_sync_status(db_path, dataset_handle="oleximakee/youtube-news-automation"):
    """
    Збирає метадані локальної бази даних та хмарного датасету без скачування самого файлу.
    Повертає структуровані дані для відображення статистики.
    """
    load_env()
    
    # Результуючий словник зі статусом
    status = {
        "local_exists": False,
        "local_size": None,
        "local_mtime": None,
        "cloud_exists": False,
        "cloud_size": None,
        "cloud_mtime": None,
        "recommendation": "Не визначено",
        "direction": "none",
        "error": None
    }
    
    # 1. Перевірка локального файлу
    if os.path.exists(db_path):
        status["local_exists"] = True
        status["local_size"] = os.path.getsize(db_path)
        mtime_epoch = os.path.getmtime(db_path)
        # Перетворюємо локальний епох-час у naive UTC datetime для порівняння з Kaggle
        status["local_mtime"] = datetime.datetime.fromtimestamp(mtime_epoch, tz=datetime.timezone.utc).replace(tzinfo=None)

    # 2. Перевірка токена
    if not os.environ.get("KAGGLE_API_TOKEN"):
        status["error"] = "KAGGLE_API_TOKEN не знайдено в оточенні або у файлі .env"
        status["recommendation"] = "Встановіть API токен"
        return status

    # 3. Перевірка хмарного датасету
    try:
        client = KaggleClient()
        owner, slug = dataset_handle.split("/", 1)
        
        # Отримуємо загальні метадані датасету
        req_dataset = ApiGetDatasetRequest()
        req_dataset.owner_slug = owner
        req_dataset.dataset_slug = slug
        dataset_info = client.datasets.dataset_api_client.get_dataset(req_dataset)
        
        status["cloud_exists"] = True
        status["cloud_mtime"] = dataset_info.last_updated
        status["cloud_size"] = dataset_info.total_bytes # Значення за замовчуванням
        
        # Спробуємо знайти конкретний файл бази даних у датасеті, щоб отримати точніший розмір
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
            # Якщо виникла помилка при отриманні списку файлів, залишаємо загальний розмір датасету
            pass
            
    except Exception as e:
        # 403 Forbidden або 404 зазвичай означають, що датасет не створено або немає доступу
        status["cloud_exists"] = False
        status["error_detail"] = str(e)

    # 4. Формування рекомендації
    if not status["cloud_exists"]:
        if status["local_exists"]:
            status["recommendation"] = "Створити датасет на Kaggle та вивантажити локальну базу"
            status["direction"] = "upload"
        else:
            status["recommendation"] = "Створіть локальну базу даних (запустіть скрапінг)"
            status["direction"] = "none"
    elif not status["local_exists"]:
        status["recommendation"] = "Завантажити базу даних з Kaggle на локальний пристрій"
        status["direction"] = "download"
    else:
        # Порівнюємо час оновлення (UTC naive datetimes)
        # Допускаємо похибку у 2 секунди, щоб уникнути мікро-коригувань
        time_diff = (status["cloud_mtime"] - status["local_mtime"]).total_seconds()
        
        if time_diff > 2:
            status["recommendation"] = f"Завантажити з хмари (Хмара новіша на {format_time_diff(time_diff)})"
            status["direction"] = "download"
        elif time_diff < -2:
            status["recommendation"] = f"Оновити хмару (Локальний файл новіший на {format_time_diff(-time_diff)})"
            status["direction"] = "upload"
        else:
            status["recommendation"] = "Бази даних повністю синхронізовані"
            status["direction"] = "sync"
            
    return status

def format_time_diff(seconds):
    """Форматує різницю у часі для відображення."""
    if seconds < 60:
        return f"{int(seconds)}с"
    elif seconds < 3600:
        return f"{int(seconds // 60)}хв {int(seconds % 60)}с"
    else:
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        return f"{int(hours)}год {int(mins)}хв"

def sync_db_with_kaggle(db_path, dataset_handle="oleximakee/youtube-news-automation", direction="smart", silent=False):
    """
    Виконує синхронізацію відповідно до обраного напрямку:
    - smart: вибір на основі порівняння часу зміни
    - upload: примусове вивантаження на Kaggle
    - download: примусове завантаження на локальну машину
    """
    load_env()
    
    if not os.environ.get("KAGGLE_API_TOKEN"):
        if not silent:
            print("[!] Помилка: KAGGLE_API_TOKEN не знайдено. Перевірте файл .env.")
        return False
        
    if direction == "smart":
        status = get_sync_status(db_path, dataset_handle)
        if status["direction"] == "none":
            if not silent:
                print(f"[i] Синхронізація неможлива: {status['recommendation']}")
            return False
        elif status["direction"] == "sync":
            if not silent:
                print("[+] Синхронізація не потрібна: бази даних збігаються.")
            return True
        direction = status["direction"]
        
    if direction == "download":
        return _download_db(db_path, dataset_handle, silent)
    elif direction == "upload":
        return _upload_db(db_path, dataset_handle, silent)
    else:
        if not silent:
            print(f"[!] Помилка: Невідомий напрямок синхронізації '{direction}'")
        return False

def _download_db(db_path, dataset_handle, silent=False):
    try:
        if not silent:
            print(f"[*] Скачування бази даних з Kaggle ({dataset_handle})...")
            
        # Завантажуємо датасет через kagglehub
        download_dir = kagglehub.dataset_download(dataset_handle, force_download=True)
        
        db_filename = os.path.basename(db_path)
        downloaded_file = os.path.join(download_dir, db_filename)
        
        # Якщо файл з точним ім'ям не знайдено, шукаємо будь-який файл .db
        if not os.path.exists(downloaded_file):
            db_files = [f for f in os.listdir(download_dir) if f.endswith(".db")]
            if db_files:
                downloaded_file = os.path.join(download_dir, db_files[0])
            else:
                if not silent:
                    print("[!] Помилка: У завантажених файлах не знайдено файлу бази даних (.db)")
                return False
                
        # Створюємо директорію для локальної бази, якщо її немає
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Копіюємо файл на локальний диск
        shutil.copy2(downloaded_file, db_path)
        
        # Синхронізуємо локальний mtime з часом оновлення на Kaggle
        _align_local_mtime_with_cloud(db_path, dataset_handle)
        
        if not silent:
            print(f"[+] Базу даних успішно завантажено та збережено у '{db_path}'.")
        return True
    except Exception as e:
        if not silent:
            print(f"[!] Помилка під час завантаження бази даних: {e}")
        return False

def _upload_db(db_path, dataset_handle, silent=False):
    if not os.path.exists(db_path):
        if not silent:
            print(f"[!] Помилка: Локальний файл '{db_path}' не існує для вивантаження.")
        return False

    db_dir = os.path.dirname(db_path)
    temp_dir = os.path.join(db_dir, "_kaggle_upload_temp")
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Копіюємо лише файл бази даних у тимчасову директорію
        db_filename = os.path.basename(db_path)
        shutil.copy2(db_path, os.path.join(temp_dir, db_filename))
        
        if not silent:
            print(f"[*] Вивантаження бази даних на Kaggle ({dataset_handle})...")
            
        # Вивантажуємо на Kaggle. Бібліотека kagglehub автоматично створить
        # приватний датасет, якщо його не існує, або оновить версію, якщо існує.
        kagglehub.dataset_upload(
            handle=dataset_handle,
            local_dataset_dir=temp_dir,
            version_notes=f"Автоматичне оновлення бази даних: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Синхронізуємо локальний mtime з новим часом оновлення на Kaggle
        _align_local_mtime_with_cloud(db_path, dataset_handle)
        
        if not silent:
            print("[+] Базу даних успішно оновлено на Kaggle.")
        return True
    except Exception as e:
        if not silent:
            print(f"[!] Помилка під час вивантаження бази даних: {e}")
        return False
    finally:
        # Очищуємо тимчасову папку
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

def _align_local_mtime_with_cloud(db_path, dataset_handle):
    """
    Запитує актуальний час зміни файлу на Kaggle і встановлює такий самий
    системний час зміни локального файлу. Це запобігає повторним помилковим
    спрацьовуванням порівняння часу.
    """
    try:
        client = KaggleClient()
        owner, slug = dataset_handle.split("/", 1)
        req = ApiGetDatasetRequest()
        req.owner_slug = owner
        req.dataset_slug = slug
        dataset_info = client.datasets.dataset_api_client.get_dataset(req)
        cloud_mtime = dataset_info.last_updated
        
        # Спробуємо отримати точніший час файлу
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
            # Конвертуємо naive UTC datetime у локальний timestamp
            cloud_mtime_local = cloud_mtime.replace(tzinfo=datetime.timezone.utc).astimezone(None)
            epoch_time = cloud_mtime_local.timestamp()
            os.utime(db_path, (epoch_time, epoch_time))
    except Exception:
        # Якщо не вдалося звести час — це не критично
        pass
