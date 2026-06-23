"""
Helper utilities module (utils.py).

This module contains general helper functions used by other parts of the application:
creating and executing an isolated virtual environment (venv), clearing the terminal,
formatting elapsed time, and normalizing YouTube channel links/handles.
"""

import os
import sys
import subprocess

# Suppress version deprecation warnings from yt-dlp package
os.environ["YT_DLP_NO_DEPRECATION_WARNING"] = "1"


def load_env(env_path=None):
    """
    Reads the .env file at the project root and injects the variables into os.environ.
    This avoids requiring external dependency packages (such as python-dotenv).
    
    Parameters:
        env_path (str, optional): Absolute path to the .env file.
    """
    if env_path is None:
        # Search for .env one level up from the current directory (project root)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(os.path.dirname(current_dir), ".env")
        
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    # Strip whitespace and quotes surrounding values
                    val = val.strip().strip("'\"")
                    os.environ[key.strip()] = val


def setup_and_run_venv(entry_script, required_libs=None):
    """
    Automatically creates a Python virtual environment (venv_auto folder) and installs
    the local news-scraper package in editable mode along with any specified dependencies.
    It then restarts the current script inside the virtual environment.
    This eliminates the need for the user to manually install packages via pip.

    Parameters:
        entry_script (str): Absolute path of the entry point script to restart (typically __file__).
        required_libs (list, optional): List of additional packages to install (e.g. ["pandas", "openpyxl"]).
    """
    if required_libs is None:
        required_libs = []

    # Determine venv directory path (relative to the entry script directory)
    script_dir = os.path.dirname(os.path.abspath(entry_script))
    venv_dir = os.path.join(script_dir, "venv_auto")
    
    # Select virtual environment python interpreter path based on OS platform
    if sys.platform == "win32":
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
    else:
        python_exe = os.path.join(venv_dir, "bin", "python")

    # If YOUTUBE_SCRAPER_VENV_ACTIVE is set to "1" or we are already running the venv python, return.
    if os.environ.get("YOUTUBE_SCRAPER_VENV_ACTIVE") == "1" or os.path.abspath(sys.executable) == os.path.abspath(python_exe):
        os.environ["YOUTUBE_SCRAPER_VENV_ACTIVE"] = "1"
        load_env()
        return

    # Construct the venv if the folder doesn't exist
    if not os.path.exists(venv_dir):
        print("[*] Bootstrapping: creating isolated virtual environment...")
        try:
            subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
        except subprocess.CalledProcessError:
            print("[!] Warning: Failed to create venv using default arguments (ensurepip might have failed).")
            print("[*] Attempting to create environment without pip...")
            subprocess.run([sys.executable, "-m", "venv", "--without-pip", venv_dir], check=True)
            
            # Fetch and run get-pip.py to install pip manually
            get_pip_path = os.path.join(venv_dir, "get-pip.py")
            print("[*] Downloading get-pip.py for manual pip installation...")
            try:
                import urllib.request
                urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip_path)
                print("[*] Installing pip in the virtual environment...")
                subprocess.run([python_exe, get_pip_path], check=True)
            except Exception as pip_err:
                print(f"[!] Pip installation failed: {pip_err}")
                raise pip_err
            finally:
                if os.path.exists(get_pip_path):
                    try:
                        os.remove(get_pip_path)
                    except Exception:
                        pass
    
    # Check if the scraper package, memory_os, standard dependencies, and extra libraries are installed
    libs_to_check = ["yt_dlp", "requests", "scraper", "memory_os"] + required_libs
    # Attempt to import each module
    libs_check_str = "; ".join(f"import {lib}" for lib in libs_to_check)
    check_deps = subprocess.run([python_exe, "-c", libs_check_str], capture_output=True)
    
    # If the import check fails (returncode != 0), perform installations
    if check_deps.returncode != 0:
        print("[*] Configuring environment and installing packages...")
        try:
            # Silently attempt to upgrade pip
            subprocess.run([python_exe, "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
            
        # If pyproject.toml exists in the entry script directory, install in editable mode
        if os.path.exists(os.path.join(script_dir, "pyproject.toml")):
            print("[*] Installing local scraper package in editable mode...")
            subprocess.run([python_exe, "-m", "pip", "install", "-e", script_dir], check=True)
            
        memory_os_dir = os.path.join(script_dir, "memory_os_local")
        if os.path.exists(os.path.join(memory_os_dir, "pyproject.toml")):
            print("[*] Installing local memory_os package in editable mode...")
            subprocess.run([python_exe, "-m", "pip", "install", "-e", memory_os_dir], check=True)
            
        # Install extra packages if requested
        if required_libs:
            print(f"[*] Installing additional packages: {', '.join(required_libs)}...")
            subprocess.run([python_exe, "-m", "pip", "install"] + required_libs, check=True)

    # Clone environment variables and set active flag
    env = os.environ.copy()
    env["YOUTUBE_SCRAPER_VENV_ACTIVE"] = "1"
    
    # Restart script with the venv python interpreter and terminate the parent process execution
    if sys.platform != "win32":
        try:
            os.execve(python_exe, [python_exe, entry_script] + sys.argv[1:], env)
        except Exception:
            pass
    sys.exit(subprocess.call([python_exe, entry_script] + sys.argv[1:], env=env))


def format_duration(seconds):
    """
    Formats seconds into a human-readable duration string (minutes and seconds).
    
    Parameters:
        seconds (float or int): Duration in seconds.
        
    Returns:
        str: String format like "Xm Ys", e.g., "2m 15s".
    """
    seconds_int = int(seconds)
    if seconds_int < 60:
        return f"{seconds_int}s"
    mins = seconds_int // 60
    secs = seconds_int % 60
    return f"{mins}m {secs}s"


def clear_screen():
    """
    Clears the terminal console window of previous contents.
    Executes 'cls' on Windows platforms and 'clear' on macOS/Linux.
    """
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title="YOUTUBE HISTORICAL SCRAPER (SQLITE)"):
    """
    Prints a formatted visual header frame with the specified title.

    Parameters:
        title (str): Title string to display in the header.
    """
    print("=" * 60)
    print(f"{title:^60}")
    print("=" * 60)


def normalize_url(user_input):
    """
    Normalizes different user input forms (channel handle, nickname, URL) into a standard format.
    Returns the channel handle and the direct link to the videos tab.

    Parameters:
        user_input (str): Raw user input string (e.g., "@UATVEnglish", "UATVEnglish", or channel URL).

    Returns:
        tuple: (nickname, url)
            - nickname: Channel handle starting with '@' (e.g. @UATVEnglish)
            - url: Normalized URL link (e.g., https://www.youtube.com/@UATVEnglish/videos)
    """
    user_input = user_input.strip()
    if not user_input:
        return None, None
        
    nickname = None
    url = user_input
    
    if user_input.startswith("@"):
        nickname = user_input
        url = f"https://www.youtube.com/{nickname}/videos"
    elif "youtube.com/" in user_input:
        if "/@" in user_input:
            parts = user_input.split("/@")
            if len(parts) > 1:
                nickname_part = parts[1].split("/")[0]
                nickname = f"@{nickname_part}"
        if not user_input.endswith("/videos"):
            if user_input.endswith("/"):
                url = user_input + "videos"
            else:
                url = user_input + "/videos"
    else:
        nickname = f"@{user_input}"
        url = f"https://www.youtube.com/{nickname}/videos"
        
    return nickname, url


def write_env(vars_dict, env_path=None):
    """
    Writes or updates environment variables in the .env file.
    Preserves other existing variables.
    
    Parameters:
        vars_dict (dict): Dictionary of environment variables to set/update.
        env_path (str, optional): Absolute path to the .env file.
    """
    if env_path is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(os.path.dirname(current_dir), ".env")
        
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    updated_lines = []
    keys_written = set()
    
    # Process existing lines in the .env file
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key, _ = stripped.split("=", 1)
            key = key.strip()
            if key in vars_dict:
                updated_lines.append(f"{key}={vars_dict[key]}\n")
                keys_written.add(key)
                continue
        updated_lines.append(line)
        
    # Append any keys that weren't present in the original file
    for key, val in vars_dict.items():
        if key not in keys_written:
            # Ensure the file ends with a newline before appending
            if updated_lines and not updated_lines[-1].endswith("\n"):
                updated_lines[-1] += "\n"
            updated_lines.append(f"{key}={val}\n")
            
    # Write the updated lines back to the .env file
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)
        
    # Inject variables directly into the current process's environment
    for key, val in vars_dict.items():
        os.environ[key] = str(val)

