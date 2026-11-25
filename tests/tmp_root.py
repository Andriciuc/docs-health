"""Puts every temp dir the tests create under one folder and deletes that folder when the run ends.

Importing this sets tempfile.tempdir, so plain tempfile.mkdtemp() calls in the tests need no cleanup
code of their own.
"""
import atexit, os, shutil, stat, sys, tempfile

ROOT = tempfile.mkdtemp(prefix="docs-health-tests-")
tempfile.tempdir = ROOT


def _force(func, path, _exc):
    """git writes read-only object files, which Windows refuses to delete."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _cleanup():
    kw = {"onexc": _force} if sys.version_info >= (3, 12) else {"onerror": _force}
    shutil.rmtree(ROOT, **kw)


atexit.register(_cleanup)
