from __future__ import annotations

import copy
from pathlib import Path

import yaml

from foureyes.policy.snapshot import PolicySnapshot

ROOT = Path(__file__).resolve().parents[1]


def base_policy() -> dict:
    return yaml.safe_load((ROOT / "policy.yaml").read_text())


def deep_merge(a: dict, b: dict) -> dict:
    out = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def policy_with(overrides: dict | None = None, remove_controls=()) -> dict:
    raw = deep_merge(base_policy(), overrides or {})
    for cid in remove_controls:
        raw["controls"].pop(cid, None)
    return raw


def snapshot(overrides: dict | None = None, remove_controls=()) -> PolicySnapshot:
    return PolicySnapshot.from_dict(policy_with(overrides, remove_controls), base_dir=ROOT)
