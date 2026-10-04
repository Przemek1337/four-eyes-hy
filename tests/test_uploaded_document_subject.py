import base64
import io
import json

import httpx
import pytest
from reportlab.pdfgen import canvas

from harness.company_registries.krs_registry_lookup import KrsRegistryLookup
from harness.demo_documents import REGISTRY_EXTRACTS_DIR
from harness.kyc.document_subject import document_subject
from harness.kyc.runner import make_document_runner
from harness.kyc.tools import KycTools
from helpers import kyc_gateway

HEADER = """CENTRALNA INFORMACJA KRAJOWEGO REJESTRU SADOWEGO
Numer KRS: 0000624225
Dzial 1
Rubryka 1 - Dane podmiotu
1.Oznaczenie formy prawnej
SPOLKA Z OGRANICZONA ODPOWIEDZIALNOSCIA
2.Numer REGON/NIP
REGON: 123456789, NIP: 1234567890
3.Firma, pod ktora spolka dziala
HOLDING LODZ SPOLKA Z OGRANICZONA ODPOWIEDZIALNOSCIA
4.Dane o wczesniejszej rejestracji
------
"""
NAME = "HOLDING LODZ SPOLKA Z OGRANICZONA ODPOWIEDZIALNOSCIA"


def pdf(text):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for n, line in enumerate(text.splitlines()):
        c.drawString(20, 800 - n * 14, line)
    c.save()
    return buf.getvalue()


def upload(gw, text=HEADER):
    return gw.client.post('/admin/chat', json={"mode": "document", "text": "", "file": {
        "name": "odpis.pdf", "content_type": "application/pdf", "content_base64": base64.b64encode(pdf(text)).decode()}})


def playground(tmp_path, registry=None):
    tools = KycTools(registries={"krs": registry} if registry else None)
    gw = kyc_gateway(tmp_path, tools=tools)
    gw.services.document_runner = make_document_runner(gw.client, tools, 'k-kyc')
    return gw


def test_official_krs_header_preserves_polish_company_name():
    text = HEADER.replace("HOLDING LODZ SPOLKA", "HOLDING ŁÓDŹ SPÓŁKA")
    subject = document_subject(text)
    assert subject['legalName'] == "HOLDING ŁÓDŹ SPÓŁKA Z OGRANICZONA ODPOWIEDZIALNOSCIA"
    assert subject['registryNumber'] == '0000624225' and subject['legalStructure'] == 'sp_zoo'


def test_uploaded_pdf_checks_its_own_registry_number_and_stops_when_offline(tmp_path):
    gw = playground(tmp_path)
    response = upload(gw)
    assert response.status_code == 200
    out = response.json()
    assert [s['tool'] for s in out['steps']] == ['entities_documents_read', 'public_registry_lookup']
    assert out['steps'][1]['args'] == {'krs_number': '0000624225'}
    assert out['decision'] == 'APPROVAL' and out['message'] == 'additional_verification'
    assert NAME in out['reply'] and 'live registry was not queried' in out['reply']
    assert not gw.kyc.entities and 'Nordwind' not in json.dumps(out)
    sess = gw.services.sessions.get(out['session_id'])
    assert sess.scope['client_id'] != 'C1' and NAME in sess.task


def test_polish_company_name_can_be_sent_in_the_agent_task_header(tmp_path):
    gw = playground(tmp_path)
    response = gw.client.post('/admin/chat', json={'mode': 'document', 'text': HEADER.replace(
        'HOLDING LODZ SPOLKA', 'HOLDING ŁÓDŹ SPÓŁKA')})
    assert response.status_code == 200
    assert 'HOLDING ŁÓDŹ' in response.json()['reply']
    assert 'Nordwind' not in json.dumps(response.json())


@pytest.mark.parametrize('mismatch', [False, True])
def test_registry_match_controls_whether_actual_company_can_be_onboarded(tmp_path, mismatch):
    seen = []
    registry_name = 'UNRELATED COMPANY' if mismatch else NAME
    record = {'odpis': {'naglowekA': {'numerKRS': '0000624225'}, 'dane': {'dzial1': {'danePodmiotu': {
        'nazwa': registry_name, 'formaPrawna': 'SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ'}}}}}

    def lookup(req):
        seen.append(str(req.url))
        return httpx.Response(200, json=record)

    gw = playground(tmp_path, KrsRegistryLookup(REGISTRY_EXTRACTS_DIR, live=True,
                                              client=httpx.Client(transport=httpx.MockTransport(lookup))))
    out = upload(gw).json()
    assert '0000624225' in seen[0]
    assert 'Nordwind' not in json.dumps(out)
    if mismatch:
        assert not gw.kyc.entities and 'does not match' in out['reply']
        assert out['message'] == 'additional_verification'
    else:
        steps = {s['tool']: s for s in out['steps']}
        assert steps['entities_create']['args']['legalName'] == NAME
        assert steps['sanctions_check']['args'] == {'name': NAME}
        client_id = gw.services.sessions.get(out['session_id']).scope['client_id']
        assert gw.kyc.entities_get(client_id)['legalName'] == NAME
        assert 'pesel' not in gw.kyc.entities_get(client_id)
        assert out['message'] == 'awaiting_approval'


def test_unidentified_pdf_is_reviewed_without_demo_onboarding(tmp_path):
    gw = playground(tmp_path)
    out = upload(gw, 'An ordinary letter without a company identifier.').json()
    assert [s['tool'] for s in out['steps']] == ['entities_documents_read']
    assert out['message'] == 'additional_verification' and 'could not be identified' in out['reply']
    assert not gw.kyc.entities and 'Nordwind' not in json.dumps(out)


def test_upload_clients_and_documents_are_isolated():
    tools = KycTools()
    subject = document_subject(HEADER)
    first, client = tools.register_upload(HEADER, subject)
    second, other = tools.register_upload(HEADER.replace(NAME, 'SECOND COMPANY'), {**subject, 'legalName': 'SECOND COMPANY'})
    assert client != other and first != second
    assert tools.entities_get(other)['legalName'] == 'SECOND COMPANY'
    with pytest.raises(ValueError, match='another client'):
        tools.entities_documents_read(other, first)
    with pytest.raises(KeyError):
        tools.entities_get('unknown')
    with pytest.raises(ValueError, match='unknown document'):
        tools.entities_documents_read(client, 'missing')
