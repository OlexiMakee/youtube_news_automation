# Backward-compatible shim.
# app.services.memory_os is now a thin delegation layer.
# All source code lives in the portable memory_os/ package at the project root.
from memory_os import *  # noqa: F401, F403
from memory_os import __all__  # noqa: F401
