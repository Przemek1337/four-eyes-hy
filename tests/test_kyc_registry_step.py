from harness.kyc.agent import run_kyc_agent
from helpers import kyc_gateway

RELAXED = {"profile": "relaxed"}


def run(gw, session, document_id, **kw):
    return run_kyc_agent(gw.client, key="k-kyc", session_id=session, document_id=document_id, **kw)


def test_clean_krs_pdf_checks_the_registry_then_completes(tmp_path):
    out = run(kyc_gateway(tmp_path, overrides=RELAXED), "k1", "nordwind-krs-clean", registry="krs",
              company_number="0099000001")
    assert [s["tool"] for s in out["steps"]] == ["entities_documents_read", "public_registry_lookup", "entities_create",
                                                 "entities_get", "sanctions_check", "entities_submit"]
    assert out["status"] == "complete"


def test_uk_company_uses_the_uk_registry_and_its_own_data(tmp_path):
    out = run(kyc_gateway(tmp_path, overrides=RELAXED), "k2", "thames-freight-clean", client_id="C4",
              registry="companies_house", company_number="99000001", task="KYC onboarding for Thames Freight Ltd")
    steps = {s["tool"]: s for s in out["steps"]}
    assert steps["uk_registry_lookup"]["outcome"] == "ALLOW"
    assert steps["entities_create"]["args"] == {"legalName": "THAMES FREIGHT LTD", "legalStructure": "ltd", "country": "GB"}
    assert out["status"] == "complete"


def test_unknown_registry_number_stops_for_additional_verification(tmp_path):
    out = run(kyc_gateway(tmp_path, overrides=RELAXED), "k3", "nordwind-krs-clean", registry="krs",
              company_number="0099000099")
    assert out["steps"][-1]["tool"] == "public_registry_lookup" and out["status"] == "additional_verification"


def test_without_a_registry_the_original_plan_is_unchanged(tmp_path):
    out = run(kyc_gateway(tmp_path, overrides=RELAXED), "k4", "nordwind-clean")
    assert [s["tool"] for s in out["steps"]] == ["entities_documents_read", "entities_create", "entities_get",
                                                 "sanctions_check", "entities_submit"]
    assert out["status"] == "complete"
