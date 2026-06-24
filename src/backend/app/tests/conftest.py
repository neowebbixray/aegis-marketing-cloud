import sys

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip tests that rely on Unix-only features when running on Windows.

    The hook looks for the presence of the ``signal`` module name in the test
    function's code objects - a heuristic that catches tests using ``signal.SIGALRM``
    or ``os.kill``. Those tests are marked with a ``skip`` marker so the Windows
    CI runner does not error out.
    """
    if not sys.platform.startswith("win"):
        return
    skip_win = pytest.mark.skip(reason="Skipped on Windows - Unix-only feature")
    for item in items:
        # ``co_names`` lists global names referenced in the function body.
        if getattr(item.function, "__code__", None) and "signal" in item.function.__code__.co_names:
            item.add_marker(skip_win)
