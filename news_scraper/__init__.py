"""Compatibility namespace for the historical ``scraper`` package.

The distribution is named ``news-scraper`` and newer app code imports
``news_scraper.*``. The implementation package is still ``scraper``.
Expose the same package path so submodules resolve through the existing code.
"""
from scraper import *  # noqa: F401,F403
import scraper as _scraper

__path__ = _scraper.__path__
