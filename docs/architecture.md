# Architektura FourEyes

FourEyes to generyczny gateway sterowany polityką: stoi między dowolnym agentem lub harnessem a jego upstreamami (modele, serwery narzędzi MCP). Klasyfikuje dane, kieruje ruch, egzekwuje kontrole deterministyczne i AI, mierzy wszystko i zapisuje audyt. Rdzeń (`foureyes`) nigdy nie importuje harnessa (`harness`).

## Diagram

```
policy.yaml + signature feed ──(hot reload)──► PolicyStore ─► PolicySnapshot (immutable)
                                                                    │
harness / agent / app ──► GATEWAY ──► Pipeline(Control[]) ──► Dispatcher ──► Upstream
 (any, replaceable)          │            ▲ Timed decorator      │   ├─ ModelUpstream (local | external)
                             │            │                      │   ├─ McpUpstream  (tool proxy)
                             │       SessionLabels               │   └─ HttpUpstream (other harness/service)
                             │       (untrusted, high_risk,      ▼
                             │        data_class — sticky)   RoutingModel · Anonymizer · MeterStore
                             ▼
                      AuditSink(Redactor) ─► audit.jsonl ─► /metrics ─► Dashboard (Security · Management · Chat)
```

## Przepływ żądania

Przed wywołaniem (prompt do modelu lub wywołanie narzędzia):

1. `auth.agent_key`
2. `models.allowlist` (model) albo `authz.tools` + `authz.tool_schema` (narzędzie)
3. `authz.scope`
4. `data.classify` (klasa z etykiet sesji) + `data.classify_net` (podnosi, nigdy nie obniża)
5. Routing: niezmiennik wylicza dozwolonych providerów z klasy; jawny `external` przy klasie prywatnej daje BLOCK `PRIVATE_DATA_EXTERNAL_MODEL`; `model: auto` oddaje wybór `RoutingModel`
6. `budget.session`, `budget.spend` (szacunek na wybranym providerze; `fallback_local` tylko w kierunku `external -> local`)
7. `sig.feed`
8. `sem.prompt_injection` (AI, tylko prompty)
9. `flow.untrusted`
10. `sem.action_judge` (AI, tylko akcje `egress` i `critical`)
11. `dlp.*` w locie
12. `Anonymizer` (no-op) i wywołanie upstreamu
13. Decyzja i audyt

Po wywołaniu (odpowiedź modelu lub wynik narzędzia):

1. Etykiety i klasa ze źródła (`sources:`) podnoszą stan sesji.
2. `sig.feed` i `sem.prompt_injection` na dokumentach: powyżej progu sesja dostaje `high_risk` i alert, bez blokady.
3. `dlp.secrets`, `dlp.field_minimization`.
4. `output.safe` (linki i obrazki do obcych domen, HTML/JS, kanarek system promptu).
5. `budget.spend`: rozliczenie faktycznego kosztu.
6. Decyzja i audyt.

Zasada niezmienna: kontrole AI mogą tylko zaostrzyć decyzję deterministyczną. Cztery wyniki decyzji: `ALLOW`, `REDACT`, `APPROVAL`, `BLOCK`.

## Klasy danych i routing

- Klasy są uporządkowane: `public < personal_data < bank_secret`. `data_classes.allowed_upstream_types` mapuje klasę na dozwolone typy upstreamów; domyślnie `public -> [local, external]`, pozostałe `-> [local]`. Walidator odrzuca politykę, która dopuszcza `external` dla klasy prywatnej.
- Źródła (`sources:`) przypisują klasę i etykiety tożsamości upstreamu. Sesja dostaje klasę źródła i nigdy jej nie obniża; każde podniesienie to zdarzenie `class.raised`.
- `data.classify_net` wykrywa dane osobowe wklejone w treść (PESEL z sumą kontrolną, IBAN, paszport) i podnosi klasę.
- Nieznane źródło dostaje `default_class` (domyślnie `bank_secret`, fail-closed); jawny `channel:chat` jest `public`.
- Klasa prywatna: tylko `local`, router nie jest pytany. Klasa `public`: router wybiera `local` lub `external`. Jawny model `external` w sesji prywatnej: BLOCK (`routing.on_private_external_request: block`, alternatywa `reroute_local`).
- Router widzi tylko metadane (klasa, typ zadania, rozmiar, procent budżetu, dostępność), nigdy treści.
- Niezmienniki w kodzie (nieusuwalne przez YAML): `auth.agent_key`; sesja prywatna nigdy nie trafia do `external`; model lokalny niedostępny w sesji prywatnej daje BLOCK `LOCAL_UNAVAILABLE`, nigdy powrót na `external`.
- Redakcja logów dzieje się tylko w `AuditSink` (kontrola `log.redact`); redakcja w locie jest ograniczona do `dlp.redact_inflight`.

## Dodawanie przypadku użycia

Dodaj do `policy.yaml` agenta, jego narzędzia z tagami, jego źródła z klasami, limity i profil. Zmiany w kodzie nie są potrzebne. Pokazuje to `tests/test_generality.py` (agent płatności zdefiniowany wyłącznie w YAML).

## Korpus syntetyczny i macierz ataków

Testy na danych syntetycznych (generatory z seedem, 17 technik ukrywania instrukcji, macierz OWASP, korpus benign, testy własności) opisuje `docs/attack-corpus.md`. Raport z `make test` zawiera blok `corpus` (skuteczność, false blocks, znane luki), który pokazuje dashboard.
