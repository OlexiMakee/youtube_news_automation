"""
Memory OS — Portable Agent Memory Kernel
No Flask dependency. Stdlib only (+ optional lazy LLM adapter).
"""
from memory_os.core import MemoryOS
from memory_os.telemetry import TelemetryRecorder
from memory_os.versioner import PromptVersioner
from memory_os.context import ContextRegistry
from memory_os.optimizer import RouteOptimizer
from memory_os.toml_parser import parse_toml, load_toml_file
from memory_os.prompt_formatter import (
    wrap_in_xml,
    format_user_profile,
    markdown_table_to_html,
    compress_dialog,
    strip_whitespace_noise,
)
from memory_os.config import MemosConfig
from memory_os.validator import MemoryValidator
from memory_os.compactor import MemoryCompactor
from memory_os.lifecycle import LifecycleManager
from memory_os.search import MemorySearcher
from memory_os.interfaces import IMemosConfig, IMemoryStorage, ILlmProviderService
from memory_os.storage import FileSystemMemoryStorage
from memory_os.llm_service import DefaultLlmProviderService

__all__ = [
    "MemoryOS",
    "TelemetryRecorder",
    "PromptVersioner",
    "ContextRegistry",
    "RouteOptimizer",
    "parse_toml",
    "load_toml_file",
    "wrap_in_xml",
    "format_user_profile",
    "markdown_table_to_html",
    "compress_dialog",
    "strip_whitespace_noise",
    "MemosConfig",
    "MemoryValidator",
    "MemoryCompactor",
    "LifecycleManager",
    "MemorySearcher",
    "IMemosConfig",
    "IMemoryStorage",
    "ILlmProviderService",
    "FileSystemMemoryStorage",
    "DefaultLlmProviderService",
]
