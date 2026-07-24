"""Pytest setup: put the Asymptote modules (repo root) on sys.path."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
