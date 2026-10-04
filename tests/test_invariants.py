import random

import pytest

from helpers import call, chat, make_gateway

PESEL = "44051401359"
ACTIONS = ["clean", "pesel", "doc", "ext", "auto", "local", "entities_get"]


@pytest.mark.negative
@pytest.mark.owasp("LLM02:2026")
@pytest.mark.parametrize("seed", range(20))
def test_private_sessions_never_reach_the_external_upstream(tmp_path, seed):
    rng = random.Random(seed)
    (tmp_path / "g").mkdir()
    gw = make_gateway(tmp_path / "g")
    sid = f"inv{seed}"
    for _ in range(12):
        a = rng.choice(ACTIONS)
        if a == "clean":
            chat(gw, "hello", sid)
        elif a == "pesel":
            chat(gw, f"PESEL {PESEL}", sid)
        elif a == "doc":
            call(gw, "entities_documents_read", {"client_id": "C1"}, sid)
        elif a == "entities_get":
            call(gw, "entities_get", {"client_id": "C1"}, sid)
        elif a == "ext":
            chat(gw, "x" * rng.choice([5, 5000]), sid, model="ext-gpt-sim")
        elif a == "auto":
            chat(gw, "x" * rng.choice([5, 5000]), sid)
        else:
            chat(gw, "x", sid, model="basal-1.0-1.5B")
    lowest = gw.services.policy_store.current().class_order[0]
    classes = []
    for ev in gw.services.audit.events(session=sid, event="decision"):
        classes.append(ev["data_class"])
        if ev["kind"] == "model" and ev["decision"] in ("ALLOW", "REDACT") and ev["upstream_type"] == "external":
            assert ev["data_class"] == lowest  # external calls only happened while the session was still public
    assert classes == sorted(classes, key=gw.services.policy_store.current().class_order.index)  # class never fell
    assert gw.client.get("/metrics").json()["private_to_external"] == 0
