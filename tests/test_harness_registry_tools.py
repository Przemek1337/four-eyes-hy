from fastapi.testclient import TestClient

from harness.kyc.server import create_tool_app
from harness.kyc.tools import KycTools
from helpers import call, kyc_gateway


def test_tool_server_lists_both_registry_tools():
    app = TestClient(create_tool_app(KycTools()))
    tools = {t["name"]: t for t in app.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).json()["result"]["tools"]}
    assert tools["public_registry_lookup"]["inputSchema"]["required"] == ["krs_number"]
    assert tools["uk_registry_lookup"]["inputSchema"]["required"] == ["company_number"]


def test_registry_lookups_through_the_gateway_stay_public(tmp_path):
    gw = kyc_gateway(tmp_path)
    err, out = call(gw, "uk_registry_lookup", {"company_number": "99000001"}, session="r1")
    out = out["result"]
    assert not err and out["status"] == "found" and out["company"]["legalName"] == "THAMES FREIGHT LTD"
    err, out = call(gw, "public_registry_lookup", {"krs_number": "0099000001"}, session="r1")
    out = out["result"]
    assert not err and out["company"]["legalStructure"] == "sp_zoo"
    assert gw.services.sessions.get("r1").data_class == "public"


def test_unknown_number_is_a_normal_result(tmp_path):
    err, out = call(kyc_gateway(tmp_path), "public_registry_lookup", {"krs_number": "0099000099"}, session="r2")
    assert not err and out["result"]["status"] == "not_found"


def test_entities_get_answers_per_client():
    tools = KycTools()
    assert tools.entities_get("C1")["pesel"] == "44051401359"
    uk = tools.entities_get("C4")
    assert uk["legalName"] == "Thames Freight Ltd" and "pesel" not in uk


def test_entities_create_accepts_a_uk_ltd(tmp_path):
    err, out = call(kyc_gateway(tmp_path), "entities_create",
                    {"legalName": "THAMES FREIGHT LTD", "legalStructure": "ltd", "country": "GB"}, session="r3")
    assert not err and out["result"]["status"] == "DRAFT"
