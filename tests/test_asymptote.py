"""Tests for the Asymptote complexity engine."""
import pytest

import asymptote
from agent_tool import ASYMPTOTE_TOOL, run_tool


def _one(source: str):
    """Analyze a single-function snippet and return its report."""
    reports = asymptote.analyze_source(source)
    assert len(reports) == 1
    return reports[0]


TIME_CASES = [
    ("def f(d, k):\n    return d.get(k)\n", "O(1)"),
    ("def f(xs):\n    t = 0\n    for x in xs:\n        t += x\n    return t\n", "O(n)"),
    (
        "def f(xs):\n    out = []\n    for a in xs:\n        for b in xs:\n"
        "            out.append((a, b))\n    return out\n",
        "O(n^2)",
    ),
    ("def f(xs):\n    return sorted(xs)\n", "O(n log n)"),
    ("def f(n):\n    return [i for i in range(n)]\n", "O(n)"),
    (
        "def f(n):\n    if n < 2:\n        return n\n"
        "    return f(n - 1) + f(n - 2)\n",
        "O(2^n)",
    ),
]


@pytest.mark.parametrize("source,expected", TIME_CASES)
def test_time_complexity(source, expected):
    assert _one(source).time == expected


def test_binary_search_is_log_n():
    src = (
        "def f(xs, t):\n"
        "    lo, hi = 0, len(xs) - 1\n"
        "    while lo <= hi:\n"
        "        mid = (lo + hi) // 2\n"
        "        if xs[mid] == t:\n"
        "            return mid\n"
        "        if xs[mid] < t:\n"
        "            lo = mid + 1\n"
        "        else:\n"
        "            hi = mid - 1\n"
        "    return -1\n"
    )
    assert _one(src).time == "O(log n)"


def test_comprehension_costs_space():
    assert _one("def f(n):\n    return [i * i for i in range(n)]\n").space == "O(n)"


def test_recursion_lowers_confidence_and_names_unknown():
    report = _one("def f(n):\n    if n < 2:\n        return n\n    return f(n - 1) + f(n - 2)\n")
    assert report.recursive is True
    assert report.confidence < 1.0
    assert any("recursion depth" in u for u in report.unknowns)


def test_cross_function_call_is_flagged_unknown():
    report = _one("def f(xs):\n    return helper(xs)\n")
    assert any("helper()" in u for u in report.unknowns)


def test_cost_algebra_labels():
    assert asymptote.Cost().label() == "O(1)"
    assert asymptote.Cost(degree=1).label() == "O(n)"
    assert asymptote.Cost(degree=1, logs=1).label() == "O(n log n)"
    assert asymptote.Cost(degree=3).label() == "O(n^3)"
    assert asymptote.Cost(exp=True).label() == "O(2^n)"


def test_nested_loops_multiply_degree():
    linear = asymptote.Cost(degree=1)
    assert linear.multiply(linear).degree == 2
    assert linear.dominate(asymptote.Cost(degree=2)).degree == 2


def test_run_tool_with_code_ok():
    result = run_tool(code="def f(xs):\n    return sorted(xs)\n")
    assert result["ok"] is True
    assert result["summary"]["functions_analyzed"] == 1
    assert result["results"]["<inline>"][0]["time"] == "O(n log n)"


def test_run_tool_requires_exactly_one_arg():
    assert run_tool()["ok"] is False
    assert run_tool(code="x=1", path="y.py")["ok"] is False


def test_run_tool_reports_syntax_error():
    result = run_tool(code="def broken(:\n")
    assert result["ok"] is False
    assert "Syntax error" in result["error"]


def test_tool_schema_shape():
    assert ASYMPTOTE_TOOL["name"] == "analyze_complexity"
    props = ASYMPTOTE_TOOL["input_schema"]["properties"]
    assert "code" in props and "path" in props


def test_methods_get_qualified_names():
    src = "class C:\n    def m(self, xs):\n        for x in xs:\n            print(x)\n"
    reports = asymptote.analyze_source(src)
    names = {r.name for r in reports}
    assert "C.m" in names
