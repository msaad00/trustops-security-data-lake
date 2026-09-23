"""A synthetic third-party connector package that fails to import.

Stands in for a real published package with a bug (a missing dependency, a
syntax error surfaced at import time, etc.). Used to test that
``connector_runner.effective_registry`` isolates the failure: this module
must never take the rest of the registry down with it.
"""

from __future__ import annotations

raise ImportError("simulated missing dependency in a broken third-party connector package")
