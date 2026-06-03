"""Dynamic robots.txt and politeness engine for scraping connectors."""

from __future__ import annotations

import logging
import threading
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from urllib.request import Request, urlopen

logger = logging.getLogger("scraper.polite_engine")


class PoliteScraperEngine:
    """Thread-safe manager for domain robots.txt rules, dynamic delays, and backoffs."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, default_delay: float = 3.0, max_delay: float = 60.0):
        if self._initialized:
            return
        self.default_delay = default_delay
        self.max_delay = max_delay
        self.parsers: dict[str, RobotFileParser] = {}
        self.custom_delays: dict[str, float] = {}
        self.policy_lock = threading.Lock()
        self._initialized = True

    def _get_domain(self, url: str) -> str:
        """Extract scheme + domain from url."""
        parsed = urlparse(url)
        if not parsed.netloc:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}"

    def get_parser(self, url: str, timeout: int = 5) -> RobotFileParser | None:
        """Fetch and cache robots.txt parser for the domain."""
        domain = self._get_domain(url)
        if not domain:
            return None

        with self.policy_lock:
            if domain in self.parsers:
                return self.parsers[domain]

        # Fetch outside the lock to prevent blocking other threads
        robots_url = f"{domain}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        
        try:
            req = Request(robots_url, headers={"User-Agent": "NewsResearchAutomation/1.0"})
            with urlopen(req, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
                parser.parse(content.splitlines())
        except Exception as exc:
            logger.warning(f"Unable to fetch robots.txt from {robots_url}: {exc}. Using default politeness.")
            # Set empty rules
            parser.parse([])

        with self.policy_lock:
            self.parsers[domain] = parser
            return parser

    def get_crawl_delay(self, url: str, user_agent: str = "NewsResearchAutomation/1.0") -> float:
        """Determine optimal crawl delay in seconds for URL and User-Agent."""
        domain = self._get_domain(url)
        if not domain:
            return self.default_delay

        with self.policy_lock:
            if domain in self.custom_delays:
                return self.custom_delays[domain]

        parser = self.get_parser(url)
        delay = None
        if parser:
            try:
                delay = parser.crawl_delay(user_agent)
            except AttributeError:
                pass

        if delay is None:
            delay = self.default_delay
        else:
            delay = float(delay)

        with self.policy_lock:
            if domain not in self.custom_delays:
                self.custom_delays[domain] = delay
            return self.custom_delays[domain]

    def report_rate_limit(self, url: str):
        """Report a 429 Rate Limit error, doubling the crawl delay for the domain."""
        domain = self._get_domain(url)
        if not domain:
            return

        with self.policy_lock:
            current = self.custom_delays.get(domain, self.default_delay)
            new_delay = min(current * 2.0, self.max_delay)
            self.custom_delays[domain] = new_delay
            logger.info(f"Rate limit reported for {domain}. Increased delay to {new_delay}s.")

    def reset_delay(self, url: str):
        """Reset the crawl delay for the domain to default or robots.txt value."""
        domain = self._get_domain(url)
        if not domain:
            return

        with self.policy_lock:
            self.custom_delays.pop(domain, None)


PROVIDER_POLICIES = {
    "youtube": {
        "is_api_possible": True,
        "api_free_limit": 10000,
        "api_cost_per_req": 0.005,
        "scraper_cost_per_req": 0.0,
        "notes": "Official API gives 10,000 free quota units/day. Super-economical workflow uses official API. Custom scraper is Tier E and has high rate-limiting risks.",
    },
    "reddit": {
        "is_api_possible": True,
        "api_free_limit": 60,
        "api_cost_per_req": 0.00024,
        "scraper_cost_per_req": 0.0,
        "notes": "JSON feed is free up to 60 req/min. Switch to API requires client OAuth credentials.",
    },
    "github": {
        "is_api_possible": True,
        "api_free_limit": 5000,
        "api_cost_per_req": 0.0,
        "scraper_cost_per_req": 0.0,
        "notes": "GitHub API is completely free (60 req/hr unauth, 5000 req/hr auth). Recommends using official API.",
    },
    "scientific": {
        "is_api_possible": True,
        "api_free_limit": 10000,
        "api_cost_per_req": 0.0,
        "scraper_cost_per_req": 0.0,
        "notes": "arXiv API is completely free but requires a minimum 3.0s delay between requests.",
    },
    "rss": {
        "is_api_possible": False,
        "api_free_limit": 0,
        "api_cost_per_req": 0.0,
        "scraper_cost_per_req": 0.0,
        "notes": "RSS/Atom feeds are completely free, managed directly by the host website's policies.",
    }
}


# Add methods to the PoliteScraperEngine class by subclassing/extending or inline definition.
# Since it is a singleton, we can just define them inside the class.
# Let's add them at the bottom of the file as methods of PoliteScraperEngine.

def get_workflow_options(self, source_type: str, estimated_records: int = 100) -> list[dict[str, Any]]:
    """Calculate details for the five workflow modes based on provider policies and estimated records."""
    policy = PROVIDER_POLICIES.get(source_type, {
        "is_api_possible": False,
        "api_free_limit": 0,
        "api_cost_per_req": 0.0,
        "scraper_cost_per_req": 0.0,
        "notes": "Standard web feed. Free and polite by default."
    })
    
    req_count = max(1, int(estimated_records / 25))
    options = []
    
    delays = {
        "youtube": {
            "super_economical": 10.0,
            "moderately_economical": 5.0,
            "medium": 3.0,
            "fast": 1.0,
            "ultra_fast": 0.5,
        },
        "reddit": {
            "super_economical": 10.0,
            "moderately_economical": 5.0,
            "medium": 3.0,
            "fast": 1.0,
            "ultra_fast": 0.1,
        },
        "github": {
            "super_economical": 5.0,
            "moderately_economical": 2.0,
            "medium": 1.0,
            "fast": 0.1,
            "ultra_fast": 0.0,
        },
        "scientific": {
            "super_economical": 5.0,
            "moderately_economical": 4.0,
            "medium": 3.0,
            "fast": 2.0,
            "ultra_fast": 1.0,
        },
        "rss": {
            "super_economical": 5.0,
            "moderately_economical": 3.0,
            "medium": 2.0,
            "fast": 1.0,
            "ultra_fast": 0.0,
        }
    }.get(source_type, {
        "super_economical": 5.0,
        "moderately_economical": 3.0,
        "medium": 2.0,
        "fast": 1.0,
        "ultra_fast": 0.0,
    })
    
    modes = [
        ("super_economical", "Super Economical"),
        ("moderately_economical", "Moderately Economical"),
        ("medium", "Medium"),
        ("fast", "Fast"),
        ("ultra_fast", "Ultra Fast")
    ]
    
    for key, label in modes:
        delay = delays[key]
        cost = 0.0
        warning = None
        note = policy["notes"]
        
        if key == "super_economical" and policy["is_api_possible"]:
            cost = 0.0
            note = f"Free Tier API enabled. {policy['notes']}"
        elif key == "ultra_fast":
            warning = "High rate-limiting or temp block risk on target server."
            if source_type in ["reddit", "youtube"]:
                cost = req_count * policy.get("api_cost_per_req", 0.0)
        elif key == "fast":
            if source_type in ["reddit", "youtube"]:
                cost = req_count * policy.get("api_cost_per_req", 0.0) * 0.5
        else:
            cost = 0.0
            
        options.append({
            "workflow": key,
            "label": label,
            "delay_sec": delay,
            "cost_estimate": round(cost, 4),
            "is_api": policy["is_api_possible"] and (key in ["super_economical", "fast", "ultra_fast"]),
            "notes": note,
            "warning": warning
        })
        
    return options

def calculate_optimal_workflow(self, source_type: str, budget: float, estimated_records: int = 100) -> dict[str, Any]:
    """Determine the fastest workflow option that fits within the budget constraint."""
    options = self.get_workflow_options(source_type, estimated_records)
    speed_order = ["ultra_fast", "fast", "medium", "moderately_economical", "super_economical"]
    
    for workflow_name in speed_order:
        for opt in options:
            if opt["workflow"] == workflow_name and opt["cost_estimate"] <= budget:
                return opt
                
    for opt in options:
        if opt["workflow"] == "super_economical":
            return opt
            
    return options[2]

# Add these as instance methods to PoliteScraperEngine class
PoliteScraperEngine.get_workflow_options = get_workflow_options
PoliteScraperEngine.calculate_optimal_workflow = calculate_optimal_workflow

