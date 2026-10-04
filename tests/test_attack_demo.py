"""The Playground's "Run test attack": nothing runs by itself, a run goes one request at a time in the background."""
import time

from harness.kyc.attack_demo import AttackDemo, Gateway, Run, run_all
from harness.kyc.runner import make_document_runner
from helpers import kyc_gateway


def wait_until_finished(gw, seconds=60):
    end = time.time() + seconds
    while time.time() < end:
        status = gw.client.get("/admin/demo/attack").json()
        if status["state"] != "running":
            return status
        time.sleep(0.05)
    raise AssertionError("the run did not finish")


def demo_gateway(tmp_path, pace=0.0):
    gw = kyc_gateway(tmp_path)
    gw.services.document_runner = make_document_runner(gw.client, gw.kyc, "k-kyc")
    gw.services.attack_demo = AttackDemo(gw.client, "k-kyc", pace=pace)
    return gw


def test_nothing_runs_until_the_button_is_pressed(tmp_path):
    gw = demo_gateway(tmp_path)
    assert gw.client.get("/admin/demo/attack").json()["state"] == "idle"
    assert gw.client.get("/metrics").json()["requests"] == 0  # a fresh gateway has no traffic and no threats


def test_without_a_harness_the_button_says_so(tmp_path):
    gw = kyc_gateway(tmp_path)
    assert gw.client.get("/admin/demo/attack").json()["state"] == "unavailable"
    r = gw.client.post("/admin/demo/attack")
    assert r.status_code == 501 and "demo harness" in r.json()["error"]["message"]


def test_a_run_sends_attacks_and_legitimate_requests_and_reports_what_it_did(tmp_path):
    gw = demo_gateway(tmp_path)
    assert gw.client.post("/admin/demo/attack").status_code == 202
    done = wait_until_finished(gw)
    s = done["summary"]
    assert done["state"] == "done" and done["error"] is None and done["sent"] == s["sent"] > 60
    assert s["attacks"] > 40 and s["attacks_stopped"] == s["attacks"], s["unexpected"]
    assert s["legit"] > 10 and s["legit_passed"] == s["legit"], s["unexpected"]
    decisions = gw.client.get("/metrics").json()["by_decision"]
    assert decisions["BLOCK"] > 20 and decisions["APPROVAL"] > 0           # the dashboard now has something to show


def test_a_second_press_while_running_is_refused(tmp_path):
    gw = demo_gateway(tmp_path, pace=0.02)
    assert gw.client.post("/admin/demo/attack").status_code == 202
    again = gw.client.post("/admin/demo/attack")
    assert again.status_code == 409 and again.json()["state"] == "running"
    wait_until_finished(gw)
    assert gw.client.post("/admin/demo/attack").status_code == 202           # allowed again once it finished
    wait_until_finished(gw)


def test_requests_leave_one_at_a_time_with_a_pause(tmp_path):
    gw = demo_gateway(tmp_path)
    stamps = []
    run = Run(pace=0.02, on_row=lambda row: stamps.append(time.perf_counter()))
    run_all(Gateway(gw.client, "k-kyc"), run)
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    assert len(stamps) > 60 and min(gaps) >= 0.018                            # never a burst
    assert run.summary()["attacks_stopped"] == run.summary()["attacks"]


def test_progress_is_visible_while_it_runs(tmp_path):
    gw = demo_gateway(tmp_path, pace=0.03)
    gw.client.post("/admin/demo/attack")
    seen = []
    end = time.time() + 30
    while time.time() < end and len(seen) < 3:
        s = gw.client.get("/admin/demo/attack").json()
        if s["state"] == "running" and s["current"]:
            seen.append((s["sent"], s["current"]["label"]))
        time.sleep(0.1)
    wait_until_finished(gw)
    assert len(seen) >= 3 and seen[-1][0] > seen[0][0]                        # the count climbs, the current attack changes
    assert len({label for _, label in seen}) > 1
