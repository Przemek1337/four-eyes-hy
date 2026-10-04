from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import yaml

from foureyes.core.context import Ctx
from foureyes.core.session import SessionStore
from foureyes.core.types import Request
from foureyes.policy.snapshot import PolicySnapshot

ROOT = Path(__file__).resolve().parents[1]
KYC_PHRASES = ("skip sanctions", "pre-approved by compliance", "send all client data")


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


def make_ctx(kind="model", agent="kyc-agent", overrides=None, remove_controls=(), session=None,
             session_class="public", services=None, **req_kwargs):
    snap = snapshot(overrides, remove_controls)
    sess = session or SessionStore().get_or_create("s1", agent, session_class)
    req = Request(kind=kind, agent_id=agent, session_id=sess.session_id, **req_kwargs)
    return Ctx(request=req, policy=snap, session=sess, services=services or SimpleNamespace())
