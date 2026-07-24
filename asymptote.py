"""Asymptote — static time & space complexity (Big-O) estimator.

Built by classHuman AI - a Generative Software Engineering firm.

WHAT THIS IS
------------
A *static, heuristic* estimator. It walks a Python AST and reasons about
loop nesting, recursion shape, and known-cost calls to produce a per-function
Big-O estimate for time and space — plus a confidence score and an explicit
list of unknowns.

WHAT THIS IS NOT
----------------
A proof. The exact asymptotic complexity of an arbitrary program is
undecidable (it reduces to the halting problem). Asymptote follows the
TACO Loop discipline: unknown data must increase decision discipline, not
model confidence. So it *states what it does not know* instead of guessing
past its evidence.

Core Product Law (TACO): Unknown data must increase decision discipline.
LAHA — Love All Humans Always.
"""
from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Cost:
    """A small algebra over Big-O terms in the input size n.

    degree : power of n from loop nesting / polynomial work (n^degree)
    logs   : number of log-n factors (e.g. from divide-and-conquer / sort)
    exp    : True if exponential (>= 2 branching recursive calls) -> 2^n
    fact   : True if factorial work detected -> n!
    """

    degree: int = 0
    logs: int = 0
    exp: bool = False
    fact: bool = False

    def rank(self) -> tuple:
        """Total order so the dominant of two costs can be chosen."""
        return (self.fact, self.exp, self.degree, self.logs)

    def dominate(self, other: "Cost") -> "Cost":
        """Sequential composition: the bigger term wins."""
        return self if self.rank() >= other.rank() else other

    def multiply(self, other: "Cost") -> "Cost":
        """Nested composition: work stacks (loop body inside a loop)."""
        return Cost(
            degree=self.degree + other.degree,
            logs=self.logs + other.logs,
            exp=self.exp or other.exp,
            fact=self.fact or other.fact,
        )

    def label(self) -> str:
        """Human-readable Big-O label for this cost term."""
        if self.fact:
            return "O(n!)"
        if self.exp:
            return "O(2^n)"
        if self.degree == 0 and self.logs == 0:
            return "O(1)"
        parts = []
        if self.degree == 1:
            parts.append("n")
        elif self.degree >= 2:
            parts.append(f"n^{self.degree}")
        if self.logs == 1:
            parts.append("log n")
        elif self.logs >= 2:
            parts.append(f"log^{self.logs} n")
        return "O(" + " ".join(parts) + ")"


CONSTANT = Cost()
LINEAR = Cost(degree=1)
LOGN = Cost(logs=1)
NLOGN = Cost(degree=1, logs=1)

# Calls whose cost is well known regardless of surrounding code.
KNOWN_CALL_COST = {
    "sorted": NLOGN,
    "sort": NLOGN,
    "min": LINEAR,
    "max": LINEAR,
    "sum": LINEAR,
    "any": LINEAR,
    "all": LINEAR,
}


@dataclass
class FunctionReport:
    """Estimate for a single function/method."""

    name: str
    line: int
    time: str = "O(1)"
    space: str = "O(1)"
    confidence: float = 1.0
    recursive: bool = False
    evidence: list = field(default_factory=list)
    unknowns: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "line": self.line,
            "time": self.time,
            "space": self.space,
            "confidence": round(self.confidence, 2),
            "recursive": self.recursive,
            "evidence": self.evidence,
            "unknowns": self.unknowns,
        }


def _calls_to(node: ast.AST, name: str) -> int:
    """Count direct calls to a bare function `name` within `node`."""
    count = 0
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            if child.func.id == name:
                count += 1
    return count


def _has_halving(node: ast.AST) -> bool:
    """Detect divide-and-conquer: floor-div by 2, /2, or midpoint slicing."""
    for child in ast.walk(node):
        if isinstance(child, ast.BinOp) and isinstance(child.op, (ast.FloorDiv, ast.Div)):
            rhs = child.right
            if isinstance(rhs, ast.Constant) and rhs.value == 2:
                return True
    return False


def _known_call_cost(node: ast.AST) -> Cost:
    """Dominant cost of any well-known calls (sorted, sort, sum, ...)."""
    best = CONSTANT
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            fname = None
            if isinstance(child.func, ast.Name):
                fname = child.func.id
            elif isinstance(child.func, ast.Attribute):
                fname = child.func.attr
            if fname in KNOWN_CALL_COST:
                best = best.dominate(KNOWN_CALL_COST[fname])
    return best


def _comprehension_cost(node: ast.AST) -> Cost:
    """A comprehension is a loop; nested generators multiply."""
    best = CONSTANT
    for child in ast.walk(node):
        if isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            best = best.dominate(Cost(degree=max(1, len(child.generators))))
    return best


def _cost_of_stmt(stmt: ast.stmt) -> Cost:
    if isinstance(stmt, (ast.For, ast.AsyncFor)):
        return LINEAR.multiply(_cost_of_body(stmt.body)).dominate(LINEAR)
    if isinstance(stmt, ast.While):
        loop = LOGN if _has_halving(stmt) else LINEAR
        return loop.multiply(_cost_of_body(stmt.body)).dominate(loop)
    if isinstance(stmt, (ast.If, ast.With, ast.AsyncWith)):
        inner = _cost_of_body(stmt.body)
        if getattr(stmt, "orelse", None):
            inner = inner.dominate(_cost_of_body(stmt.orelse))
        return inner
    if isinstance(stmt, ast.Try):
        inner = _cost_of_body(stmt.body)
        for handler in stmt.handlers:
            inner = inner.dominate(_cost_of_body(handler.body))
        return inner.dominate(_cost_of_body(stmt.finalbody))
    return _known_call_cost(stmt).dominate(_comprehension_cost(stmt))


def _cost_of_body(stmts: list) -> Cost:
    total = CONSTANT
    for stmt in stmts:
        total = total.dominate(_cost_of_stmt(stmt))
    return total


_SAFE_BUILTINS = {
    "len", "range", "print", "int", "str", "float", "bool", "list", "dict",
    "set", "tuple", "enumerate", "zip", "isinstance", "type", "abs", "round",
    "sorted", "sum", "min", "max", "any", "all", "map", "filter", "open",
}
_GROWTH_METHODS = {"append", "add", "insert", "update", "extend"}


def _space_cost(func: ast.AST, recursive: bool, halving: bool) -> tuple:
    """Return (Cost, evidence-strings) for auxiliary space."""
    best = CONSTANT
    ev = []
    if recursive:
        term = LOGN if halving else LINEAR
        best = best.dominate(term)
        ev.append(f"recursion stack ~ {term.label()}")
    comp = _comprehension_cost(func)
    if comp.rank() > CONSTANT.rank():
        best = best.dominate(comp)
        ev.append(f"comprehension materializes {comp.label()}")
    in_loop = any(isinstance(n, (ast.For, ast.While)) for n in ast.walk(func))
    grows = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in _GROWTH_METHODS
        for n in ast.walk(func)
    )
    if in_loop and grows:
        best = best.dominate(LINEAR)
        ev.append("accumulator grows inside loop ~ O(n)")
    return best, ev


def _user_call_unknowns(func: ast.AST, own_name: str) -> list:
    """Cross-boundary calls whose cost Asymptote cannot see. Honesty first."""
    seen = []
    for child in ast.walk(func):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            name = child.func.id
            if name != own_name and name not in _SAFE_BUILTINS and name.islower():
                if name not in seen:
                    seen.append(name)
    return [f"calls {n}() - cost not analyzed across function boundary" for n in seen]


def estimate_function(func: ast.AST) -> FunctionReport:
    """Produce a time & space Big-O estimate for one function node."""
    report = FunctionReport(name=func.name, line=func.lineno)
    body_cost = _cost_of_body(func.body)
    self_calls = _calls_to(func, func.name)
    halving = _has_halving(func)
    report.recursive = self_calls > 0

    if report.recursive:
        if self_calls >= 2:
            rec = NLOGN if halving else Cost(exp=True)
            report.evidence.append(
                f"{self_calls} recursive calls" + (" with halving" if halving else "")
            )
        else:
            rec = LOGN if halving else LINEAR
            report.evidence.append("linear recursion" + (" with halving" if halving else ""))
        time_cost = rec.multiply(body_cost) if body_cost.rank() > CONSTANT.rank() else rec
    else:
        time_cost = body_cost

    if time_cost.degree >= 2:
        report.evidence.append(f"nested loops -> polynomial degree {time_cost.degree}")
    elif time_cost.degree == 1 and not report.recursive:
        report.evidence.append("single-level iteration over input")
    if _known_call_cost(func).logs > 0:
        report.evidence.append("sort / n-log-n call detected")

    space_cost, space_ev = _space_cost(func, report.recursive, halving)
    report.evidence.extend(space_ev)

    report.time = time_cost.label()
    report.space = space_cost.label()

    # Confidence: start certain, discount for what we cannot see (TACO discipline).
    confidence = 1.0
    report.unknowns = _user_call_unknowns(func, func.name)
    confidence -= 0.1 * len(report.unknowns)
    if report.recursive:
        confidence -= 0.3
        report.unknowns.append(
            "recursion depth depends on runtime data - estimate is a heuristic upper bound"
        )
    if time_cost.exp:
        report.unknowns.append("exponential shape assumes no memoization")
    report.confidence = max(0.2, round(confidence, 2))
    return report


def _iter_functions(node: ast.AST, prefix: str = ""):
    """Yield (qualified_name, function_node) for every def, methods included."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.ClassDef):
            yield from _iter_functions(child, prefix + child.name + ".")
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            report_node = child
            report_node._qualname = prefix + child.name  # type: ignore[attr-defined]
            yield prefix + child.name, child
            yield from _iter_functions(child, prefix + child.name + ".")


def analyze_source(source: str, path: str = "<string>") -> list:
    """Analyze source text; return a list of FunctionReport."""
    tree = ast.parse(source, filename=path)
    reports = []
    for qualname, func in _iter_functions(tree):
        report = estimate_function(func)
        report.name = qualname
        reports.append(report)
    return reports


def analyze_file(path: str) -> list:
    with open(path, "r", encoding="utf-8") as handle:
        return analyze_source(handle.read(), path)


def analyze_path(target: str) -> dict:
    """Analyze a file or a directory tree of .py files. Returns {path: reports}."""
    results = {}
    if os.path.isfile(target) and target.endswith(".py"):
        try:
            results[target] = analyze_file(target)
        except SyntaxError as exc:
            results[target] = [FunctionReport(name="<parse-error>", line=exc.lineno or 0,
                                              unknowns=[f"could not parse: {exc.msg}"], confidence=0.0)]
    elif os.path.isdir(target):
        for root, _dirs, files in os.walk(target):
            for name in files:
                if name.endswith(".py"):
                    full = os.path.join(root, name)
                    try:
                        results[full] = analyze_file(full)
                    except SyntaxError as exc:
                        results[full] = [FunctionReport(name="<parse-error>", line=exc.lineno or 0,
                                                        unknowns=[f"could not parse: {exc.msg}"],
                                                        confidence=0.0)]
    return results


def format_text(results: dict) -> str:
    """Render results as a human-readable Asymptote report."""
    lines = ["", "=" * 78, "  ASYMPTOTE - TIME & SPACE COMPLEXITY REPORT", "=" * 78]
    total = 0
    for path, reports in results.items():
        lines.append(f"\n{path}")
        if not reports:
            lines.append("  (no functions found)")
        for r in reports:
            total += 1
            flag = "~" if r.confidence < 0.6 else " "
            lines.append(
                f" {flag}L{r.line:<4} {r.name}: time {r.time} | space {r.space} "
                f"| confidence {r.confidence:.0%}"
            )
            for e in r.evidence:
                lines.append(f"        evidence: {e}")
            for u in r.unknowns:
                lines.append(f"        unknown : {u}")
    lines.append("\n" + "-" * 78)
    lines.append(f"Analyzed {total} function(s). '~' marks low-confidence estimates.")
    lines.append("Asymptote is a static heuristic, not a proof. Unknowns are stated, not hidden.")
    lines.append("=" * 78)
    return "\n".join(lines)


def main(argv: Optional[list] = None) -> int:
    import json

    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if not argv:
        print("Usage: python asymptote.py <file_or_dir> [--json]")
        return 1
    target = argv[0]
    if not os.path.exists(target):
        print(f"Path not found: {target}")
        return 1
    results = analyze_path(target)
    if as_json:
        payload = {p: [r.as_dict() for r in rs] for p, rs in results.items()}
        print(json.dumps(payload, indent=2))
    else:
        print(format_text(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
