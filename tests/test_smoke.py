"""Skeleton smoke test — confirms auto_cell imports and that the editable
physical-ai-core dependency resolves in the same venv.
"""

import auto_cell
import physical_ai_core


def test_auto_cell_version():
    assert auto_cell.__version__ == "0.1.0"


def test_core_dependency_resolves():
    # The editable path source must place physical-ai-core in the same venv.
    assert physical_ai_core.__version__ == "0.1.0"
