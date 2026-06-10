"""
Script for sequential scraping of a list of UATV YouTube channels (scrape_multi.py).

This script iterates through a list of channels loaded from data/channels.txt,
checks and updates video history for each channel, and saves the results to a single database.
It supports virtual environment configuration, progress bars, pause menus, and state persistence.
It also supports CLI arguments for targeting custom channels and specific day ranges, or interactive prompting.
"""
import warnings
warnings.filterwarnings("ignore")

import os
import sys
import time
import argparse
import select
from datetime import date, timedelta

# Add the current directory to sys.path so that scraper imports work seamlessly
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import scraper.utils as utils

# Launch automatic virtual environment setup
utils.setup_and_run_venv(__file__)

from scraper.db_client import DatabaseClient
from scraper.scraper_engine import YouTubeScraperEngine
from scraper.config import ScraperConfig
from scraper.observer import CLIObserver
import scraper.cli_progress as cli_progress

# Maximum video limit per channel
LIMIT_PER_CHANNEL = 17000
SYNC_PROMPT_TIMEOUT_SECONDS = 10


CHANNELS_FILE_CANDIDATES = [
    os.path.join(root_dir, "channels_to_scrape.txt"),
    os.path.join(root_dir, "data", "channels.txt"),
]


def _read_channels_file(channels_path):
    """Reads a newline-delimited channel list while preserving order and removing duplicate channels."""
    channels = []
    seen = set()
    with open(channels_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            _, normalized_url = utils.normalize_url(line)
            dedupe_key = (normalized_url or line).rstrip("/").lower()
            if dedupe_key in seen:
                continue
            channels.append(line)
            seen.add(dedupe_key)
    return channels


def load_channels():
    """Loads priority channels from root channels_to_scrape.txt, then data/channels.txt, then defaults."""
    for channels_path in CHANNELS_FILE_CANDIDATES:
        if not os.path.exists(channels_path):
            continue
        try:
            channels = _read_channels_file(channels_path)
            if channels:
                print(f"[*] Loaded {len(channels)} channels from {os.path.relpath(channels_path, root_dir)}")
                return channels
        except Exception as e:
            print(f"[!] Warning: Could not read {channels_path}: {e}")

    # Fallback default channels
    return [
        "https://www.youtube.com/@UATVEspanol",
        "https://www.youtube.com/@UATVPortugu%C3%AAs",
        "https://www.youtube.com/@UATVpopolsku",
        "https://www.youtube.com/@UATVDeutsch",
        "https://www.youtube.com/@UATVmagyarul",
        "https://www.youtube.com/@UATVArabic",
        "@UATVFrançais",
        "https://www.youtube.com/@FREEDOM_TV",
        "https://www.youtube.com/@FREEDOM_LIVE",
        "https://www.youtube.com/@tsn",
        "https://www.youtube.com/@UNITED24media",
        "https://www.youtube.com/@FREEDOM_KAVKAZ",
        "https://www.youtube.com/@SiliconCurtain",
        "https://www.youtube.com/@AnnafromUkraine",
        "https://www.youtube.com/@JakeBroe",
        "https://www.youtube.com/@PaulJWarburg",
        "https://www.youtube.com/@CivDiv",
        "https://www.youtube.com/@ukraine_tbic",
        "https://www.youtube.com/@PrestonStewart",
        "https://www.youtube.com/@DylanBurnsLIVE",
        "https://www.youtube.com/@MalcolmNanceMedia",
        "https://www.youtube.com/@VladVexler",
        "https://www.youtube.com/@CombatVeteranReacts",
        "https://www.youtube.com/@anderspuck",
        "https://www.youtube.com/@ZeihanonGeopolitics",
        "https://www.youtube.com/@SabbaticalTommy",
        "https://www.youtube.com/@terrelljstarrofficial",
        "https://www.youtube.com/@nucking_futs_yuri/videos",
        "https://www.youtube.com/@TheSoupCentral/",
        "https://www.youtube.com/@arturrehi",
        "https://www.youtube.com/@DenysDavydov",
        "https://www.youtube.com/@PaulJWarburg",
        "https://www.youtube.com/@Professor-Gerdes/videos",
        "https://www.youtube.com/@SiliconCurtain/videos",
        "https://www.youtube.com/@GregTerryExperience",
        "https://www.youtube.com/@CaolanRobertsonReport",
        "https://www.youtube.com/@Harley-EOD",
        "https://www.youtube.com/@StarskyUA",
        "https://www.youtube.com/@AnnafromUkraine",
        "https://www.youtube.com/@Savage_Sage",
        "https://www.youtube.com/@BigMakBattleBlog",
        "https://www.youtube.com/@ricktheukrainian",
        "https://www.youtube.com/@PhilipIttner",
        "https://www.youtube.com/@jplindsley",
        "https://www.youtube.com/@UkraineMatters",
        "https://www.youtube.com/channel/UCJDIGW0ywWw9Kh9_vtwqxXA",
        "https://www.youtube.com/@PerunAU",
        "https://www.youtube.com/@TheWorstTraveller",
        "https://www.youtube.com/@INSIDERUSSIA"
    ]


def get_history_cutoff_yyyymmdd(days):
    """Calculates date back by a number of days and returns YYYYMMDD string."""
    return (date.today() - timedelta(days=days)).strftime("%Y%m%d")


def timed_yes_no_prompt(prompt, default=False, timeout=SYNC_PROMPT_TIMEOUT_SECONDS):
    """
    Ask a yes/no question with a countdown.
    Returns default when stdin is not interactive or the timer expires.
    """
    default_label = "Y/n" if default else "y/N"
    default_text = "yes" if default else "no"

    if not sys.stdin.isatty():
        print(f"{prompt} [{default_label}] non-interactive -> {default_text}")
        return default

    sys.stdout.write(f"{prompt} [{default_label}] ")
    sys.stdout.flush()
    answer = ""

    try:
        for remaining in range(timeout, 0, -1):
            sys.stdout.write(f"\r\033[K{prompt} [{default_label}] default {default_text} in {remaining}s: ")
            sys.stdout.flush()
            ready, _, _ = select.select([sys.stdin], [], [], 1)
            if ready:
                answer = sys.stdin.readline().strip().lower()
                break
        else:
            sys.stdout.write(f"\r\033[K{_format_timeout_message(prompt, default_text)}\n")
            sys.stdout.flush()
            return default
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        return default

    if not answer:
        return default
    return answer in {"y", "yes", "так", "т", "1"}


def _format_timeout_message(prompt, default_text):
    return f"{prompt} timeout -> {default_text}"


def make_auto_sync_callback(silent=False):
    """Creates a callback for auto-syncing DB with Neon Postgres (delta replication)."""
    def auto_sync(db_client):
        try:
            from scraper.postgres_sync import PostgresSyncClient
            pg_client = PostgresSyncClient()
            if pg_client.is_configured():
                if not silent:
                    print("\n[*] Running automated delta synchronization to Neon Postgres...")
                pg_client.sync_delta(db_client, silent=silent)
        except Exception as sync_err:
            if not silent:
                print(f"[!] Automated Postgres replication failed: {sync_err}")
    return auto_sync


def run_multi_scraping(channels_list, days, stop_on_known=True, single_channel_mode=False, no_prompt=False):
    """Main logic for sequential channel iteration."""
    db_path = os.path.join(root_dir, "data", "youtube_news.db")

    # 1. Kaggle Cloud database sync (timeout default: skip)
    run_kaggle = False
    if not no_prompt:
        db_size_mb = 0
        db_time_str = "N/A"
        if os.path.exists(db_path):
            db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
            db_time_str = time.ctime(os.path.getmtime(db_path))
        print(f"\n[*] Found local database: {db_path}")
        print(f"    - Size: {db_size_mb:.1f} MB")
        print(f"    - Last modified: {db_time_str}")
        run_kaggle = timed_yes_no_prompt(
            "[?] Run Kaggle cloud database synchronization (smart check)?",
            default=False
        )
    if not run_kaggle:
        print("[i] Skipping Kaggle cloud database sync.")

    if run_kaggle:
        try:
            from scraper.kaggle_sync import sync_db_with_kaggle
            print("[*] Checking for database updates in the cloud (Kaggle)...")
            sync_db_with_kaggle(db_path, direction="smart", silent=False)
        except Exception as e:
            print(f"[!] Warning: Could not sync database with Kaggle: {e}")
            time.sleep(1)

    db_client = DatabaseClient()
    db_client.init_db()

    # 2. Neon Postgres database sync (timeout default: sync)
    run_postgres = True
    pg_configured = False
    try:
        from scraper.postgres_sync import PostgresSyncClient
        pg_client = PostgresSyncClient()
        pg_configured = pg_client.is_configured()
    except Exception:
        pass

    if pg_configured:
        if not no_prompt:
            run_postgres = timed_yes_no_prompt(
                "[?] Run Neon Postgres delta synchronization (delta upload)?",
                default=True
            )
        if not run_postgres:
            print("[i] Skipping Neon Postgres delta sync.")

        if run_postgres:
            try:
                print("[*] Connecting to Neon Postgres and initializing tables...")
                pg_client.init_pg_db()
                print("[+] Neon Postgres ready.")
                pg_client.sync_delta(db_client, silent=False)
            except Exception as pg_init_err:
                print(f"[!] Warning: Neon Postgres initialization failed: {pg_init_err}")
                time.sleep(1)
    else:
        print("[i] Neon Postgres is not configured or missing dependency. Skipping delta replication.")

    utils.clear_screen()
    print("=" * 60)
    print(f"{'UATV CHANNELS SEQUENTIAL SCRAPER':^60}")
    print("=" * 60)
    print(f"[*] Channels to process:  {len(channels_list)}")
    print(f"[*] Video limit per channel: {LIMIT_PER_CHANNEL}")
    history_cutoff = get_history_cutoff_yyyymmdd(days)
    history_cutoff_label = f"{history_cutoff[:4]}-{history_cutoff[4:6]}-{history_cutoff[6:]}"
    print(f"[*] Saving videos from: {history_cutoff_label} (last {days} days)")
    print(f"[*] Stop on known duplicate: {stop_on_known}")
    print(f"[*] DB path: {db_client.db_path}")
    print("=" * 60)
    time.sleep(1.5)

    for idx, channel_input in enumerate(channels_list, 1):
        utils.clear_screen()
        print("=" * 60)
        print(f"Stage {idx} of {len(channels_list)}: {channel_input}")
        print("=" * 60)

        nickname, url = utils.normalize_url(channel_input)

        # Bind progress display and pause-trigger callbacks
        current_name = channel_handle or channel_name
        progress_prefix = f"[{idx}/{len(channels_list)} - {current_name}]"
        on_progress = cli_progress.make_progress_callback(history_cutoff, prefix=progress_prefix)
        on_pause = cli_progress.make_pause_callback(channel_id, start_time, db_client)

        from scraper.keypress import KeypressDetector
        detector = KeypressDetector(True)
        observer = CLIObserver(silent=False, keypress_detector=detector, on_pause_callback=lambda: on_pause(scraper))
        
        # Override the observer's on_progress to use the cli_progress callback
        observer.on_progress = lambda current_count, total_limit, last_added_time, **kwargs: on_progress(current_count, total_limit, last_added_time, **kwargs)

        config = ScraperConfig(default_limit=LIMIT_PER_CHANNEL)
        
        # Initialize scraper engine with the set limit and date constraint
        scraper = YouTubeScraperEngine(
            url,
            storage=db_client,
            config=config,
            observer=observer,
            date_after=history_cutoff,
            on_auto_sync=make_auto_sync_callback(silent=False) if pg_configured and run_postgres else None
        )

        print("[*] Checking connection and fetching channel metadata...")
        info = scraper.fetch_channel_info()
        if not info or not info["channel_id"]:
            print(f"[!] Error: Could not retrieve channel ID for '{channel_input}'. Skipping...")
            time.sleep(3)
            continue

        channel_id = info["channel_id"]
        channel_name = info["channel_name"]
        channel_handle = info["channel_handle"]

        print("-" * 60)
        print(f"Channel:      {channel_name} ({channel_handle or 'no handle'})")
        print(f"Channel ID:   {channel_id}")
        print("-" * 60)

        # Check current status of the channel in the database
        db_info = db_client.get_channel_video_info(channel_id)
        if db_info and db_info["video_count"] > 0:
            print(f"[i] Channel already exists in database. Cached videos: {db_info['video_count']}")
            print(f"    Published period: from {db_info['min_date']} to {db_info['max_date']}")
            print(f"[*] Checking/downloading videos since {history_cutoff_label}...")
            start_index = 1
        else:
            print(f"[i] New channel detected.")
            print(f"[*] Collecting video history since {history_cutoff_label}...")
            start_index = 1

        start_time = time.time()

        # Callbacks already bound above

        # Set the starting offset index in the scraper engine
        scraper.start_index = start_index

        # Run history collection process
        success = scraper.run_archive_scraping(
            stop_on_known=stop_on_known
        )

        # Display the final execution report for the channel
        cli_progress.print_final_report(scraper, channel_id, start_time, db_client, success=success)

        # Check if the user selected Exit (option 3) during a pause
        if scraper.aborted:
            print("\n[!] Scraping process interrupted by user. Aborting remaining channels.")
            break

        # A brief delay between channels to maintain stability
        if idx < len(channels_list):
            sys.stdout.write("\n")
            for sec in range(5, 0, -1):
                sys.stdout.write(f"\r\033[K[*] Channel processing finished. Transitioning to next channel in {sec} seconds...")
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write(f"\r\033[K[*] Transitioning to next channel...\n")
            sys.stdout.flush()

    print("\n" + "=" * 60)
    print("Process complete! Channels processed.")
    print("=" * 60)

    # Final Neon Postgres sync (timeout default: sync)
    try:
        from scraper.postgres_sync import PostgresSyncClient
        pg_client = PostgresSyncClient()
        if pg_client.is_configured():
            run_final_postgres = True
            if not no_prompt:
                run_final_postgres = timed_yes_no_prompt(
                    "\n[?] Run final Neon Postgres delta synchronization?",
                    default=True
                )
            if run_final_postgres:
                print("\n[*] Running final synchronization to Neon Postgres...")
                pg_client.sync_delta(db_client, silent=False)
            else:
                print("[i] Skipping final Neon Postgres sync.")
    except Exception as pg_final_err:
        print(f"[!] Warning: Final Neon Postgres sync failed: {pg_final_err}")

    # Final Kaggle backup (timeout default: skip)
    run_final_kaggle = False
    if not no_prompt:
        run_final_kaggle = timed_yes_no_prompt(
            "\n[?] Run final Kaggle cloud database synchronization?",
            default=False
        )
    if run_final_kaggle:
        try:
            from scraper.kaggle_sync import sync_db_with_kaggle
            db_path = os.path.join(root_dir, "data", "youtube_news.db")
            print("\n[*] Running final Kaggle synchronization...")
            sync_db_with_kaggle(db_path, direction="smart", silent=False)
        except Exception as e:
            print(f"[!] Warning: Final Kaggle sync failed: {e}")
    else:
        print("[i] Skipping final Kaggle sync.")


def run_interactive_menu(channels):
    """Runs interactive command line loop to select a channel and input day range."""
    print("\n" + "=" * 60)
    print(f"{'INTERACTIVE CHANNEL SCRAPING SELECTOR':^60}")
    print("=" * 60)
    for i, ch in enumerate(channels, 1):
        print(f"  {i:2d}. {ch}")
    print("=" * 60)

    # Select Channel
    while True:
        try:
            choice = input(f"Select channel (1-{len(channels)}) or enter URL/handle: ").strip()
            if not choice:
                continue
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(channels):
                    selected_channel = channels[idx - 1]
                    break
                else:
                    print(f"[!] Invalid index. Must be between 1 and {len(channels)}.")
            else:
                # Custom URL or handle
                selected_channel = choice
                break
        except KeyboardInterrupt:
            print("\n[!] Canceled.")
            sys.exit(0)

    # Select Days
    while True:
        try:
            days_input = input("Enter number of days back to scrape (default 7): ").strip()
            if not days_input:
                days = 7
                break
            if days_input.isdigit() and int(days_input) > 0:
                days = int(days_input)
                break
            else:
                print("[!] Invalid days. Please enter a positive integer.")
        except KeyboardInterrupt:
            print("\n[!] Canceled.")
            sys.exit(0)

    run_multi_scraping([selected_channel], days, stop_on_known=True, single_channel_mode=True, no_prompt=False)


def main():
    parser = argparse.ArgumentParser(description="YouTube news multi-channel sequential scraper.")
    parser.add_argument("-c", "--channel", help="Channel handle, URL, or 1-based index from data/channels.txt")
    parser.add_argument("-d", "--days", type=int, help="Number of days back to scrape")
    parser.add_argument("-i", "--interactive", action="store_true", help="Run interactive channel and days selector")
    parser.add_argument("--stop-on-known", type=str, choices=["true", "false"], default="true",
                        help="Stop scraping channel when a known video ID is encountered (default: true)")
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Bypass sync prompts using defaults: Kaggle skip, Postgres sync"
    )

    args = parser.parse_args()
    channels = load_channels()

    stop_known = args.stop_on_known == "true"

    try:
        if args.interactive:
            run_interactive_menu(channels)
        elif args.channel is not None:
            # Custom channel selection
            selected_channel = None
            if args.channel.isdigit():
                idx = int(args.channel)
                if 1 <= idx <= len(channels):
                    selected_channel = channels[idx - 1]
                else:
                    print(f"[!] Invalid index {args.channel}. Out of range (1-{len(channels)}).")
                    sys.exit(1)
            else:
                selected_channel = args.channel

            days = args.days if args.days is not None else 7
            run_multi_scraping([selected_channel], days, stop_on_known=stop_known, single_channel_mode=True, no_prompt=args.no_prompt)
        else:
            # Default run: 180 days (6 months) for all channels
            days = args.days if args.days is not None else 180
            run_multi_scraping(channels, days, stop_on_known=stop_known, no_prompt=args.no_prompt)
    except KeyboardInterrupt:
        print("\n\n[!] Process interrupted by user. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
