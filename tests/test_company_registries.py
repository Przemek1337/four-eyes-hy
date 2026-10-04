import base64

import httpx
import pytest

from harness.company_registries.companies_house_registry_lookup import CompaniesHouseRegistryLookup
from harness.company_registries.krs_registry_lookup import KrsRegistryLookup
from harness.company_registries.registry_lookup_port import lookup_result
from harness.demo_documents import REGISTRY_EXTRACTS_DIR

LIVE_KRS = {"odpis": {"naglowekA": {"numerKRS": "0000000123"},
                      "dane": {"dzial1": {"danePodmiotu": {"nazwa": "EXAMPLE SPÓŁKA AKCYJNA", "formaPrawna": "SPÓŁKA AKCYJNA",
                                                           "identyfikatory": {"nip": "1111111111"}}}}}}


def no_network(req):
    raise AssertionError(f"unexpected network call to {req.url}")


def http(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_krs_file_record_is_the_fictional_nordwind():
    out = lookup_result(KrsRegistryLookup(REGISTRY_EXTRACTS_DIR, client=http(no_network)), "0099000001")
    assert out["status"] == "found" and out["source"] == "file"
    assert out["company"] == {"legalName": "NORDWIND SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ", "legalStructure": "sp_zoo",
                              "country": "PL", "registryStatus": "registered", "registryNumber": "0099000001",
                              "nip": "0000000000"}


def test_krs_fixture_masks_personal_data_like_the_api():
    member = KrsRegistryLookup(REGISTRY_EXTRACTS_DIR).lookup("0099000001")["odpis"]["dane"]["dzial2"]["reprezentacja"]["sklad"][0]
    assert member["identyfikator"]["pesel"] == "4**********" and member["nazwisko"]["nazwiskoICzlon"].endswith("*")


def test_invalid_and_unknown_numbers_are_results_not_exceptions():
    krs = KrsRegistryLookup(REGISTRY_EXTRACTS_DIR, client=http(no_network))
    assert lookup_result(krs, "12AB")["status"] == "invalid_number"
    assert lookup_result(krs, "0099000099")["status"] == "not_found"


def test_krs_live_request_and_errors():
    seen = {}

    def ok(req):
        seen["url"] = str(req.url)
        return httpx.Response(200, json=LIVE_KRS)

    out = lookup_result(KrsRegistryLookup(REGISTRY_EXTRACTS_DIR, live=True, client=http(ok)), "0000000123")
    assert seen["url"] == "https://api-krs.ms.gov.pl/api/krs/OdpisAktualny/0000000123?rejestr=P&format=json"
    assert out["source"] == "live" and out["company"]["legalStructure"] == "sa"
    assert lookup_result(KrsRegistryLookup(REGISTRY_EXTRACTS_DIR, live=True,
                                           client=http(lambda r: httpx.Response(404))), "0000000123")["status"] == "not_found"

    def refused(req):
        raise httpx.ConnectError("refused", request=req)

    assert lookup_result(KrsRegistryLookup(REGISTRY_EXTRACTS_DIR, live=True, client=http(refused)),
                         "0000000123")["status"] == "unavailable"


def test_live_failure_never_falls_back_to_the_file():
    krs = KrsRegistryLookup(REGISTRY_EXTRACTS_DIR, live=True, client=http(lambda r: httpx.Response(503)))
    assert lookup_result(krs, "0099000001")["status"] == "unavailable"


def test_companies_house_file_and_live_with_basic_auth():
    out = lookup_result(CompaniesHouseRegistryLookup(REGISTRY_EXTRACTS_DIR, client=http(no_network)), "99000001")
    assert out["company"] == {"legalName": "THAMES FREIGHT LTD", "legalStructure": "ltd", "country": "GB",
                              "registryStatus": "active", "registryNumber": "99000001"}
    seen = {}

    def ok(req):
        seen.update(url=str(req.url), auth=req.headers["authorization"])
        return httpx.Response(200, json={"company_name": "X LTD", "company_number": "12345678", "company_status": "active",
                                         "type": "ltd"})

    live = CompaniesHouseRegistryLookup(REGISTRY_EXTRACTS_DIR, api_key="key-123", client=http(ok))
    assert lookup_result(live, "12345678")["source"] == "live"
    assert seen["url"] == "https://api.company-information.service.gov.uk/company/12345678"
    assert seen["auth"] == "Basic " + base64.b64encode(b"key-123:").decode()
    assert lookup_result(live, "bad")["status"] == "invalid_number"


def test_live_mode_comes_from_the_environment(monkeypatch):
    monkeypatch.delenv("KRS_LIVE", raising=False)
    monkeypatch.delenv("CH_API_KEY", raising=False)
    assert KrsRegistryLookup.from_env(REGISTRY_EXTRACTS_DIR).live is False
    assert CompaniesHouseRegistryLookup.from_env(REGISTRY_EXTRACTS_DIR).live is False
    monkeypatch.setenv("KRS_LIVE", "1")
    monkeypatch.setenv("CH_API_KEY", "k")
    assert KrsRegistryLookup.from_env(REGISTRY_EXTRACTS_DIR).live is True
    assert CompaniesHouseRegistryLookup.from_env(REGISTRY_EXTRACTS_DIR).live is True
