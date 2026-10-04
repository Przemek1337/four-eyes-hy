from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from foureyes.detect.decision_model_data_class_detector import classify_data
from foureyes.policy.snapshot import PolicySnapshot
from foureyes.semantic.decision_model_action_judge import DecisionModelActionJudge
from foureyes.semantic.decision_model_client import UncertainDecision
from foureyes.semantic.decision_model_registry import DecisionModelRegistry
from foureyes.semantic.decision_model_types import TYPE_CAPABILITIES
from foureyes.semantic.rule_based_injection_scorer import assess_injection
from harness.demo_documents import DEMO_DOCUMENTS_DIR

CHECK_CAPABILITY = {"injection": "yes_no", "data_class": "choice", "action": "choice"}


def _models_for(snapshot, capability: str) -> list[str]:
    return [name for name, cfg in snapshot.decision_models().items()
            if cfg["type"] != "mock" and cfg.get("location") == "local" and capability in TYPE_CAPABILITIES[cfg["type"]]]


def _predict(check: str, client, name: str, item: dict, snapshot) -> tuple[str, float, bool]:
    if check == "injection":
        conf = snapshot.control_cfg("sem.prompt_injection")
        a = assess_injection(client, name, item["text"], conf)
        return ("yes" if a.score >= conf["documents"]["flag_above"] else "no"), a.latency_ms, a.uncertain
    if check == "data_class":
        a = classify_data(client, name, item["text"], snapshot.control_cfg("data.classify_net")["ai"], snapshot.class_order)
        return a.outcome, a.latency_ms, a.uncertain
    conf = snapshot.control_cfg("sem.action_judge")
    judge = DecisionModelActionJudge(client, name, conf)
    try:
        res = judge.judge(item["task"], item["tool"], item["args"], item.get("labels", []))
    except UncertainDecision as unsure:
        return "uncertain", unsure.assessment.latency_ms, True
    label = "out_of_scope" if not res.consistent and res.score >= conf.get("escalate_above", 0.7) else "consistent"
    return label, judge.last_assessment.latency_ms, False


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))], 2)


def _accuracy(rows: list[dict]) -> float | None:
    return round(sum(r["predicted"] == r["expected"] for r in rows) / len(rows), 3) if rows else None


def evaluate(registry, snapshot, items: list[dict], model_names: list[str] | None = None) -> dict:
    report: dict = {}
    for check, capability in CHECK_CAPABILITY.items():
        subset = [i for i in items if i["check"] == check]
        for name in model_names or _models_for(snapshot, capability):
            if capability not in TYPE_CAPABILITIES[snapshot.decision_model_cfg(name)["type"]]:
                continue
            client = registry.client(name, snapshot)
            rows = []
            for item in subset:
                try:
                    label, ms, unsure = _predict(check, client, name, item, snapshot)
                except Exception as exc:
                    label, ms, unsure = f"error: {exc}", 0.0, False
                rows.append({"id": item["id"], "lang": item["lang"], "expected": item["expected"], "predicted": label,
                             "latency_ms": round(ms, 2), "uncertain": unsure})
            langs = sorted({r["lang"] for r in rows})
            report.setdefault(name, {})[check] = {
                "n": len(rows), "accuracy": _accuracy(rows),
                "by_lang": {lang: _accuracy([r for r in rows if r["lang"] == lang]) for lang in langs},
                "uncertain": sum(r["uncertain"] for r in rows),
                "p50_ms": _percentile([r["latency_ms"] for r in rows], 0.5),
                "p95_ms": _percentile([r["latency_ms"] for r in rows], 0.95), "items": rows}
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="make eval-models")
    p.add_argument("--policy", default="policy.yaml")
    p.add_argument("--out", default="reports/decision_models_eval.json")
    args = p.parse_args(argv)
    path = Path(args.policy)
    snap = PolicySnapshot.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")), base_dir=path.parent)
    items = json.loads((DEMO_DOCUMENTS_DIR / "eval_set.json").read_text(encoding="utf-8"))
    report = evaluate(DecisionModelRegistry(), snap, items)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, checks in report.items():
        for check, r in checks.items():
            print(f"{name:18} {check:11} accuracy {r['accuracy']}  by_lang {r['by_lang']}  n {r['n']}  "
                  f"uncertain {r['uncertain']}  p50 {r['p50_ms']} ms  p95 {r['p95_ms']} ms")
    print(f"written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
