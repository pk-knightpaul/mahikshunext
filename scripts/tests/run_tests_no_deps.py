#!/usr/bin/env python3
"""
Zero-dependency test runner for scripts/tests/*.py.

This exists so the test suite can be exercised in environments without
network access to `pip install pytest` (like this sandbox). It shims just
enough of pytest's API (pytest.raises, pytest.mark.parametrize, the
tmp_path and monkeypatch fixtures) to run the real test files unmodified.

In any environment with real internet access, prefer running the actual
pytest instead:
    pip install pytest -r scripts/requirements.txt
    python -m pytest scripts/tests/ -v
This script is a fallback, not a replacement.
"""
import importlib.util
import inspect
import os
import shutil
import sys
import tempfile
import traceback
import types

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(TESTS_DIR)
sys.path.insert(0, SCRIPTS_DIR)


# ---------- Minimal pytest shim ----------

class _RaisesContext:
    def __init__(self, exc_type):
        self.exc_type = exc_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, tb):
        if exc_type is None:
            raise AssertionError(f"Expected {self.exc_type.__name__} but no exception was raised")
        return issubclass(exc_type, self.exc_type)


class _Mark:
    @staticmethod
    def parametrize(argname, values):
        def decorator(fn):
            fn._parametrize = (argname, values)
            return fn
        return decorator


_pytest_shim = types.ModuleType("pytest")
_pytest_shim.raises = _RaisesContext
_pytest_shim.mark = _Mark()
sys.modules["pytest"] = _pytest_shim


# ---------- Fixture providers (mimics pytest's tmp_path / monkeypatch) ----------

class _MonkeyPatch:
    def __init__(self):
        self._undo = []

    def setattr(self, obj, name, value):
        old = getattr(obj, name)
        self._undo.append((obj, name, old))
        setattr(obj, name, value)

    def undo(self):
        for obj, name, old in reversed(self._undo):
            setattr(obj, name, old)


def _make_fixture_kwargs(sig, tmpdir_stack):
    kwargs = {}
    mp = None
    if "tmp_path" in sig.parameters:
        d = tempfile.mkdtemp()
        tmpdir_stack.append(d)
        import pathlib
        kwargs["tmp_path"] = pathlib.Path(d)
    if "monkeypatch" in sig.parameters:
        mp = _MonkeyPatch()
        kwargs["monkeypatch"] = mp
    return kwargs, mp


# ---------- Test discovery & execution ----------

def load_module(path):
    name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_test_function(fn):
    """Runs a single test function, handling @pytest.mark.parametrize and
    tmp_path/monkeypatch fixtures. Returns (passed: bool, error: str|None)."""
    tmpdirs = []
    try:
        sig = inspect.signature(fn)
        param_info = getattr(fn, "_parametrize", None)

        if param_info:
            argname, values = param_info
            for val in values:
                kwargs, mp = _make_fixture_kwargs(sig, tmpdirs)
                kwargs[argname] = val
                try:
                    fn(**kwargs)
                finally:
                    if mp:
                        mp.undo()
        else:
            kwargs, mp = _make_fixture_kwargs(sig, tmpdirs)
            try:
                fn(**kwargs)
            finally:
                if mp:
                    mp.undo()
        return True, None
    except Exception:
        return False, traceback.format_exc()
    finally:
        for d in tmpdirs:
            shutil.rmtree(d, ignore_errors=True)


def main():
    test_files = sorted(
        f for f in os.listdir(TESTS_DIR)
        if f.startswith("test_") and f.endswith(".py")
    )

    total = 0
    failed = 0
    failures = []

    for filename in test_files:
        path = os.path.join(TESTS_DIR, filename)
        module = load_module(path)
        test_fns = [
            (name, obj) for name, obj in vars(module).items()
            if name.startswith("test_") and callable(obj)
        ]
        print(f"\n{filename} ({len(test_fns)} tests)")

        for name, fn in test_fns:
            total += 1
            passed, error = run_test_function(fn)
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {name}")
            if not passed:
                failed += 1
                failures.append((filename, name, error))

    print(f"\n{'=' * 60}")
    print(f"{total} tests run, {total - failed} passed, {failed} failed")

    if failures:
        print("\nFailures:\n")
        for filename, name, error in failures:
            print(f"--- {filename}::{name} ---")
            print(error)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
