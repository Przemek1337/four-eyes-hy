import ast
from pathlib import Path

from foureyes.core.control import registry
from foureyes.policy.catalog import CATALOG_IDS, SINK_IDS

SRC = Path(__file__).resolve().parents[1] / "src"


def test_core_never_imports_the_harness():
    offenders = []
    for path in (SRC / "foureyes").rglob("*.py"):
        if path.name == "cli.py":  # the launcher is the one place that wires a harness in
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            if any(m == "harness" or m.startswith("harness.") for m in mods):
                offenders.append(str(path))
    assert not offenders, offenders


def test_every_catalog_control_has_an_implementation_except_sinks():
    import foureyes.controls  # noqa: F401
    missing = [c for c in CATALOG_IDS if c not in SINK_IDS and c not in registry()]
    assert missing == []
    assert {"route.invariant", "source.stage"} <= set(registry())  # hidden baseline stages exist in code


def test_core_has_no_kyc_vocabulary_in_code():
    banned = ("kyc", "nordwind", "sanctions")
    hits = []
    for path in (SRC / "foureyes").rglob("*.py"):
        if path.name == "cli.py":  # the launcher wires the demo harness in
            continue
        text = path.read_text(encoding="utf-8").lower()
        hits += [(path.name, word) for word in banned if word in text]
    assert hits == [], hits
