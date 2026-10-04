"""The offline pack runs backend/rural.py inside the browser (Pyodide), so that file must stand alone:
standard library only, and the same answers without the rest of the project."""
import ast
import builtins
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "backend" / "rural.py"
STDLIB = {"__future__", "math", "re", "typing"}


def test_rural_py_imports_only_the_standard_library_at_module_level():
    tree = ast.parse(SRC.read_text(encoding="utf-8"))
    mods = set()
    for n in tree.body:
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods.add((n.module or "").split(".")[0])
    assert mods <= STDLIB, mods - STDLIB


def _standalone():
    """rural.py executed alone, with the project's own packages made unimportable (as in the browser)."""
    real = builtins.__import__

    def blocked(name, *a, **k):
        if name.split(".")[0] in {"analysis", "backend", "core"}:
            raise ImportError(name)
        return real(name, *a, **k)
    ns: dict = {"__name__": "rural_standalone"}
    builtins.__import__ = blocked
    try:
        exec(compile(SRC.read_text(encoding="utf-8"), "rural.py", "exec"), ns)
        return ns, blocked
    finally:
        builtins.__import__ = real


def test_standalone_answers_equal_the_server_side_answers():
    from backend import rural
    ns, blocked = _standalone()
    real = builtins.__import__
    builtins.__import__ = blocked
    try:
        off = ns["loan_cost"](50000, 5, "per100_month", 10, "interest_only", "en")
        text = "Pay Rs 10000 now, get Rs 20000 in 6 months, guaranteed. Bring 3 friends. Only today!"
        sc = ns["scheme_check"](text, lang="en")
        ent = ns["entitlements"]({"age": 40, "gender": "female", "land": "own", "work": "farmer", "poor": "yes"}, "hi")
        rd = ns["readiness"](["pm_kisan", "pmjjby"], ["aadhaar"], "en")
        inc = ns["income_plan"]([{"month": 10, "amount": 120000}, {"month": 4, "amount": 60000}], 8000, [], 0, 36, "en")
    finally:
        builtins.__import__ = real
    assert off == rural.loan_cost(50000, 5, "per100_month", 10, "interest_only", "en")
    assert sc["level"] == "red" and sc["implied_yearly_pct"] == 300.0                # figures read without the project's parser
    assert ent == rural.entitlements({"age": 40, "gender": "female", "land": "own", "work": "farmer", "poor": "yes"}, "hi")
    assert rd == rural.readiness(["pm_kisan", "pmjjby"], ["aadhaar"], "en")
    assert inc == rural.income_plan([{"month": 10, "amount": 120000}, {"month": 4, "amount": 60000}], 8000, [], 0, 36, "en")
