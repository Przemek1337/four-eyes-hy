# FourEyes Gateway — Design Spec

Data: 2026-10-03 · Status: do przeglądu · Źródła prawdy: `project_brief_plus_api.md` (brief v3), `CRITERIA_AI_Control_Layer.md`, `RULES_AI_Control_Layer.md`.
**Zmiany 2026-10-04:** modele decyzyjne (Granite Guardian, Basal), rejestry spółek i pliki demo — `2026-10-04-foureyes-decision-models-and-demo-design.md` (nadpisuje §3.1, §5, §6 i §12 w zakresie tam opisanym).
Ten dokument **uzupełnia i nadpisuje** brief v3 tam, gdzie to wskazano w sekcji 2. Wszystko, czego tu nie zmieniono, obowiązuje według briefu.

---

## 1. Cel i zakres

**Cel.** Zbudować generyczny gateway (proxy), który od wejścia przez siebie do wskazanego upstreamu (model, serwer MCP, dowolny harness HTTP) mierzy, kontroluje i loguje cały ruch agentów AI oraz skutecznie wychwytuje zagrożenia. Hackathon HackYeah, kategoria AI Control Layer.

**Oceniane (Wytyczne s.5, s.6, Regulamin pkt 11):** gateway, centralna polityka, kontrole deterministyczne i AI, budżety, feed sygnatur, raportowanie i audyt, test suite, architektura i wydajność. Wagi z Regulaminu: Robustness 30, Architecture & Performance 20, Reporting 20, Tests 20, Implementability 10.

**Nieoceniane:** agenci, aplikacje, narzędzia. Wszystko, co jest KYC, to **reference harness** (agent, portal, atrapy narzędzi MCP, dane demo), umieszczony poza rdzeniem.

**Zasada rdzenia.** Rdzeń nie zna żadnej domeny. Nowy use case (KYC, Treasury, risk validation, …) to nowy agent w polityce: jego klucz, narzędzia z tagami, źródła z klasami, limity. Kontrole wykrywają zagrożenia po **mechanizmie** (provenance, wzorce, schematy, budżety, sygnatury, bezpieczeństwo wyjścia), nie po domenie.

**Poza zakresem.** Anonimizacja danych dla modeli zewnętrznych (zostaje no-op z zapisem w audycie), produkcyjna integracja z Jev (tylko interfejs i atrapa), realne API banku.

## 2. Zmiany względem briefu v3

| # | Brief v3 | Ten spec |
|---|---|---|
| 1 | `dlp.redact` redaguje treść w pipeline (krok 9) | Redakcja **logów** w `AuditSink` (kontrola `log.redact`, typ `sink`). W locie redagują cztery zawężone zadania `dlp.*` (sekcja 6) |
| 2 | Routing: brak, `fallback_local` tylko z budżetów | Klasy danych, routing prywatne → lokalny, router (atrapa Jev) tylko w obrębie dozwolonych providerów, niezmiennik w kodzie |
| 3 | Anonimizacja: nieomówiona | `Anonymizer` no-op, audyt: `anonymization: not_applied` przy każdym wywołaniu `external` |
| 4 | `authz.client_scope`, `client_id`, `case_only` | `authz.scope` z `scope_key` w polityce |
| 5 | Karta zatwierdzenia z polami KYC | Karta generyczna: wszystkie prawdziwe parametry, scope, etykiety, reguła |
| 6 | `profile` i progi globalne | `agents.<id>.profile` i `agents.<id>.overrides` nadpisują wartości domyślne |
| 7 | `authz.tool_schema` zawsze BLOCK | `on_violation: block \| approval` per reguła schematu |
| 8 | „Playground" w dashboardzie | Zwykły **czat** dla sędziów (tryby Prompt i Document) |
| 9 | Agentic Top 10: ID do sprawdzenia | Zweryfikowane (sekcja 12) |
| 10 | Etap 2: Treasury jako osobne wdrożenie | Kolejny use case to **wyłącznie konfiguracja**; test „obcego agenta" w MVP |

## 3. Architektura

```
policy.yaml + signature feed ──(hot reload)──► PolicyStore ─► PolicySnapshot (immutable)
                                                                    │
harness / agent / app ──► GATEWAY ──► Pipeline(Control[]) ──► Dispatcher ──► Upstream
 (dowolny, podstawialny)     │            ▲ Timed decorator      │   ├─ ModelUpstream (local | external)
                             │            │                      │   ├─ McpUpstream  (proxy narzędzi)
                             │       SessionLabels               │   └─ HttpUpstream (inny harness/usługa)
                             │       (untrusted, high_risk,      ▼
                             │        data_class — lepkie)   RoutingModel · Anonymizer · MeterStore
                             ▼
                      AuditSink(Redactor) ─► audit.jsonl ─► /metrics ─► Dashboard (Security · Management · Chat)
```

### 3.1 Komponenty

| Komponent | Odpowiedzialność | Zależy od |
|---|---|---|
| `PolicyStore` | ładuje i waliduje YAML, hot reload, wystawia `PolicySnapshot`; błędny plik = zostaje poprzednia wersja | — |
| `Control` (interfejs) i `Pipeline` | kontrola to klasa `evaluate(ctx) → Verdict`; pipeline budowany ze snapshotu z rejestru kontroli | `PolicySnapshot` |
| `Timed` (dekorator) | span: czas i werdykt każdej kontroli | `Telemetry` |
| `SourceClassifier` | klasa źródła z `sources:` (tożsamość upstreamu → klasa, etykiety) | snapshot |
| `data.classify_net` | detektory (PESEL z sumą kontrolną, IBAN, `sensitive_terms` z sesji) tylko **podnoszą** klasę | rejestr `Detector` |
| `SessionLabels` | etykiety lepkie: `untrusted`, `high_risk`, `data_class = max(...)` | — |
| `RoutingModel` (interfejs) | wybiera providera z dozwolonego zbioru; widzi **tylko metadane** | `RuleBasedRouter` (domyślny), `OllamaRouter` (opcja), `JevRouter` (adapter, niewysłany) |
| `ProviderDispatcher` | **niezmiennik w kodzie**: dozwoleni providerzy = funkcja klasy sesji; wywołuje `Upstream` | `RoutingModel`, `Anonymizer`, `MeterStore` |
| `Upstream` (interfejs) | `ModelUpstream`, `McpUpstream`, `HttpUpstream` | adaptery formatu API |
| `Anonymizer` (interfejs) | implementacja no-op, zapisuje do audytu | — |
| `MeterStore` | budżety i zużycie (USD, sekundy compute, tokeny, kroki) | SQLite |
| `ApprovalService` | karty, hash SHA-256 parametrów, jednorazowość, TTL | — |
| `AuditSink` + `Redactor` | jedyne miejsce redakcji logów; zapis, eksport, `/metrics` | — |
| `Telemetry` | narzut gatewaya osobno od czasu upstreamu, p50/p95 per kontrola, bajty, tokeny, koszt | — |

### 3.2 Przepływ żądania

*Przed wywołaniem* (prompt do modelu lub wywołanie narzędzia):
1. `auth.agent_key`
2. `models.allowlist` (model) albo `authz.tools` + `authz.tool_schema` (narzędzie)
3. `authz.scope`
4. `data.classify` (klasa z etykiet sesji) + `data.classify_net` (podnosi, nigdy nie obniża)
5. **Routing**: niezmiennik wylicza dozwolonych providerów z klasy; jawny `external` przy klasie prywatnej → BLOCK `PRIVATE_DATA_EXTERNAL_MODEL`; `model: auto` → `RoutingModel` wybiera z dozwolonych
6. `budget.session`, `budget.spend` (szacunek na wybranym providerze; `fallback_local` tylko w kierunku `external → local`)
7. `sig.feed`
8. `sem.prompt_injection` (AI, tylko prompty)
9. `flow.untrusted`
10. `sem.action_judge` (AI, tylko akcje `egress` i `critical`)
11. `dlp.*` w locie (sekcja 6)
12. `Anonymizer` (no-op) + wywołanie upstreamu
13. Decyzja + audyt

*Po wywołaniu* (odpowiedź modelu lub wynik narzędzia):
1. Etykiety i klasa ze źródła (`sources:`) podnoszą stan sesji.
2. `sig.feed` i `sem.prompt_injection` na dokumentach: powyżej progu sesja `high_risk` + alert, bez blokady (brief 7d).
3. `dlp.secrets`, `dlp.field_minimization`.
4. `output.safe` (linki i obrazki do obcych domen, HTML/JS, kanarek system promptu).
5. `budget.spend`: rozliczenie faktycznego kosztu.
6. Decyzja + audyt.

**Zasada niezmienna:** kontrole AI mogą tylko zaostrzyć decyzję deterministyczną.

## 4. Klasy danych, źródła i routing

**Klasy** (uporządkowane): `public < personal_data < bank_secret`. `class_rules` w polityce mapuje klasę na dozwolone typy upstreamów modelowych; domyślnie `public → [local, external]`, pozostałe `→ [local]`.

**Źródła.** Compliance przypisuje klasę **tożsamości upstreamu** w `sources:` (np. system klientów zwraca `personal_data`, dokument klienta `bank_secret` + etykieta `untrusted`). Gdy agent czegoś dotknie, sesja dostaje klasę źródła i **nigdy jej nie obniża**. Każde podniesienie to zdarzenie `class.raised` (powód, źródło).

**Siatka bezpieczeństwa.** `data.classify_net` wykrywa dane osobowe w treści, która weszła bez etykiety (np. PESEL wklejony w polecenie) i podnosi klasę. Nie obniża jej.

**Nieznane źródło** = `default_class` (domyślnie `bank_secret`, fail-closed). Wyjątek: jawnie nazwany `channel:chat` = `public`.

**Routing.**
- Klasa prywatna → tylko `local`. Router nie jest pytany.
- Klasa `public` → router wybiera `local` lub `external` po koszcie, złożoności i budżecie.
- Jawny model `external` w sesji prywatnej → **BLOCK** (`route.private_external`, kod `PRIVATE_DATA_EXTERNAL_MODEL`). Przełącznik `routing.on_private_external_request: block | reroute_local`, **domyślnie `block`**. Przy `reroute_local` decyzja to ALLOW z polem audytu `rerouted_from`.
- `model: auto` oddaje wybór gatewayowi.

**Router widzi tylko metadane** (klasa, typ zadania, rozmiar, stan budżetu, dostępność providerów), nigdy treści. Powód: Jev jest zewnętrznym API (early access, bez otwartych wag), więc wysyłanie mu treści byłoby samo w sobie wyciekiem. Awaria routera → `local` (fail-closed).

**Niezmienniki w kodzie** (nieusuwalne przez YAML, w duchu „kontroli bazowych" z briefu 7b):
- `auth.agent_key`,
- sesja prywatna nigdy nie trafia do upstreamu `external`; walidator odrzuca politykę, która dopuszcza `external` dla klasy prywatnej,
- model lokalny niedostępny w sesji prywatnej → BLOCK `LOCAL_UNAVAILABLE`, nigdy powrót na `external`.

## 5. Polityka (`policy.yaml`) — szkielet zmian

Reszta (providers, models, signatures, budgets) jak w briefie sekcja 7.

```yaml
version: 1
profile: strict                  # domyślny; agents.<id>.profile nadpisuje

data_classes:
  order: [public, personal_data, bank_secret]
  allowed_upstream_types: { public: [local, external], personal_data: [local], bank_secret: [local] }

sources:                         # tożsamość upstreamu → klasa i etykiety
  mcp:entities_get:            { class: personal_data }
  mcp:entities_documents_read: { class: bank_secret, labels: [untrusted], redact_fields: [] }
  mcp:public_registry_lookup:  { class: public }
  channel:chat:                { class: public }
  default_class: bank_secret

routing:
  on_private_external_request: block        # block | reroute_local
  router: { type: rule_based }              # rule_based | ollama | jev (adapter niewysłany)
  anonymization: { external: not_applied }  # wyłącznie notatka w audycie

agents:
  kyc-agent:
    key_ref: KYC_AGENT_KEY
    default_model: qwen2.5:7b
    tools: [entities_create, entities_get, entities_documents_read, entities_submit,
            sanctions_check, send_email, update_case_notes]
    scope: { key: client_id, mode: case_only }
    profile: relaxed                         # opcjonalnie; nadpisuje globalny
    overrides: { budget.session: { max_steps: 30 } }

tools:                                       # tagi i schematy, bez wiedzy o domenie w rdzeniu
  entities_submit: { tags: [critical], requires_before: [sanctions_check] }
  send_email:      { tags: [egress], allowed_domains: ["bank.internal"] }
  payments_execute:
    tags: [critical]
    schema: schemas/payments_execute.json    # JSON Schema: maximum, enum, format
    on_violation: { amount: approval, beneficiary: block }

dlp:                                         # redakcja i blokada w locie, per rodzaj wykrycia
  secrets:            { on_detect: redact }          # redact | block | monitor
  field_minimization: { on_detect: redact }          # pola z sources.*.redact_fields
  egress_sinks:       { on_detect: redact }          # treść do ujścia o niższej klasie
  pii_in_prompt:      { on_detect: raise_class }     # raise_class | redact | block

log_redaction:
  detectors: [secrets, iban, pesel, passport]
  mode: redact                                       # redact | monitor

controls:                                            # katalog: usunięcie wpisu = kontrola wyłączona
  auth.agent_key:       { mode: enforce }            # bazowa
  models.allowlist:     { mode: enforce }
  authz.tools:          { mode: enforce }
  authz.tool_schema:    { mode: enforce }
  authz.scope:          { mode: enforce }
  data.classify_net:    { mode: enforce }
  route.model:          { mode: enforce }
  flow.untrusted:       { mode: enforce }
  dlp.redact_inflight:  { mode: enforce }            # steruje sekcją dlp:
  log.redact:           { mode: redact, stage: sink }
  output.safe:          { mode: block }
  budget.session:       { mode: enforce }
  budget.spend:         { mode: enforce }
  sig.feed:             { mode: enforce }
  sem.prompt_injection: { prompts: { block_above: 0.8, log_above: 0.5 }, documents: { flag_above: 0.5 }, on_error: fail_closed }
  sem.action_judge:     { on: [egress, critical], escalate_above: 0.7, action: approval, model: qwen2.5:7b, on_error: approval }
```

**Walidacja atomowa:** błąd w dowolnym miejscu odrzuca całą politykę, zostaje poprzednia wersja, zdarzenie `policy.rejected`. Odrzucane są też: usunięcie lub `monitor` kontroli bazowej, dopuszczenie `external` dla klasy prywatnej, nieznana nazwa kontroli, literówka w `mode`.

## 6. Kontrole — zmiany względem briefu

Reszta tabeli z briefu sekcja 5 obowiązuje.

| ID | Zmiana |
|---|---|
| `dlp.redact` → **`dlp.redact_inflight`** | cztery zadania z własnym progiem: `secrets` (zawsze w locie), `field_minimization` (pola zbędne dla zadania, wycinane z wyniku narzędzia przed modelem), `egress_sinks` (treść do ujścia o niższej klasie niż sesja), `pii_in_prompt` (domyślnie `raise_class`). Dane, których zadanie wymaga (np. PESEL w KYC), **nie są redagowane**, tylko idą na model lokalny |
| **`log.redact`** (nowa, `stage: sink`) | redakcja w `AuditSink` przed zapisem, eksportem i dashboardem; usuwalna (Wytyczne s.6): po usunięciu audyt dostaje `redaction: off`, posture spada, eksport pokazuje ostrzeżenie |
| **`data.classify_net`** (nowa) | podnosi klasę; tagi OWASP: LLM02:2026 |
| **`route.model`** (nowa) | routing w obrębie dozwolonych; usunięcie = routing domyślny (lokalnie); niezmiennik w dispatcherze zostaje |
| `authz.client_scope` → **`authz.scope`** | `scope_key` z polityki |
| `authz.tool_schema` | `on_violation: block \| approval` per reguła |
| `output.safe` | wynik REDACT: usunięcie szkodliwego fragmentu (obcy link, obrazek, HTML/JS) i dostarczenie reszty odpowiedzi; kanarek system promptu nadal BLOCK |

**OWASP LLM02:2026** jest pokryte przez trzy mechanizmy: routing (prywatne nie opuszcza banku), `log.redact` i `dlp.redact_inflight`.

## 7. Decyzje

Cztery wyniki: **ALLOW, REDACT, APPROVAL, BLOCK**. Każda decyzja ma `decision_id`, regułę, powód, warstwę (det/AI), wersję polityki, tagi OWASP, latencję.

**Zatwierdzenie** dotyczy dokładnie jednego wywołania: hash SHA-256 kanonicznego JSON-a parametrów, jednorazowo, z TTL. Inne parametry → BLOCK `APPROVAL_MISMATCH`. Karta jest generyczna: agent, narzędzie, **wszystkie prawdziwe parametry**, scope, etykiety i klasa sesji, reguła, flaga i score sędziego AI, „Reason supplied by agent", hash, ważność.

**Fail-closed:**
- błędny YAML lub feed → zostaje poprzednia wersja,
- router nie odpowiada → `local`,
- detektor rzuca wyjątek → sesja dostaje najwyższą klasę,
- model kontroli AI nie odpowiada → `on_error`: BLOCK albo APPROVAL, nigdy cichy ALLOW,
- model lokalny niedostępny w sesji prywatnej → BLOCK `LOCAL_UNAVAILABLE`.

**Świadomy fail-open (głośno):** usunięcie kontroli niebazowej z `controls:` (brief 7b).

## 8. Audyt i telemetria

Pola z briefu sekcja 12 oraz: `data_class`, `class_raised_by`, `upstream`, `upstream_type`, `route {allowed, chosen, router, rerouted_from}`, `anonymization`, `redaction (on|off)`, `timings` (spany per kontrola i czas upstreamu), `policy_version`. Zdarzenia: `policy.reloaded`, `policy.rejected`, `control.removed`, `control.restored`, `class.raised`.

`/metrics`: decyzje per typ, p50/p95 per kontrola i per warstwa, **narzut gatewaya osobno od czasu upstreamu**, ruch wg klasy i typu upstreamu, `private→external` (musi być 0), koszt per agent/zespół/provider, sekundy compute, wersje polityki i feedu.

Audyt wspiera wzorce z AI Act Art. 12 (automatyczny zapis zdarzeń) i Art. 14 (nadzór człowieka: karta zatwierdzenia, możliwość ingerencji). Nie twierdzimy zgodności prawnej (sekcja 12).

## 9. Dashboard (UI po angielsku, zgodnie z briefem)

**Security view:** lista sesji z filtrami (agent, decyzja, klasa, reguła) i kolejką zatwierdzeń; odznaki `untrusted`, `high_risk` oraz klasy danych jako osobne osie; oś czasu z `class.raised`, trasą (providerzy, wybrany, router, `anonymization`), rozróżnieniem „fields removed before model" i „redacted in log"; „Why blocked" (decyzja, reguła, warstwa, tagi OWASP z rokiem, ID sygnatury, fragment dokumentu, score PromptGuard); generyczna karta zatwierdzenia; eksport JSONL i CSV z filtrami i ostrzeżeniem „Export contains redacted content only".

**Management view:** security posture z jawnym rozbiciem; pokrycie OWASP LLM Top 10 (2026) na żywo (enforced / monitor only / uncovered); panel kontroli (status, tryb, progi, zadziałania, p95); aktywna wersja polityki, diff, historia; wersja i status feedu sygnatur; licznik **private → external: 0** oraz ruch wg klasy i typu upstreamu; cztery wyniki decyzji i otwarte zatwierdzenia; koszty i budżety per agent i zespół (jedna waluta, USD, `display_currency` opcjonalnie; compute w sekundach); narzut gatewaya vs czas upstreamu (p50/p95); wynik test suite'u (pozytywne/negatywne, wg OWASP, „false blocks", „missed attacks").

**Czat dla sędziów:** zwykłe okno czatu (tryby Prompt i Document, gotowe przykłady); obok odpowiedzi decyzja, klasa, trasa, reguła, warstwa, tag OWASP, latencja. Działa jako zwykły agent w polityce, więc zmiana polityki działa na prompty sędziów.

**Poza MVP (Etap 3):** pułapka `export_all_clients`, automatyczne zamykanie sesji, replay, follow mode, mapa przepływu danych, attack mode.

## 10. Rozszerzalność (SOLID)

- **Open/Closed:** rejestry kontroli, detektorów, sygnatur, upstreamów i routerów (dekorator lub entry point). Nowa kontrola to nowa klasa plus wpis w `controls:`, bez edycji `Pipeline`.
- **Single Responsibility:** jedna kontrola = jedna odpowiedzialność; redakcja tylko w `AuditSink`; klasyfikacja, routing i anonimizacja to osobne komponenty.
- **Liskov / Interface Segregation:** małe interfejsy `Control`, `Upstream`, `RoutingModel`, `Anonymizer`, `Detector`; implementacje wymienne bez zmian wywołującego.
- **Dependency Inversion:** `ProviderDispatcher` zależy od interfejsów; atrapy (`MockUpstream`, `MockJudge`, `RuleBasedRouter`) używane w testach tym samym kodem co produkcyjne.
- **Wymuszenie testem:** rdzeń nie importuje niczego z `harness/`; test architektoniczny w CI.
- **Nowy use case** = nowy agent w polityce (klucz, narzędzia z tagami, źródła z klasami, limity, profil, nadpisania). Zero zmian w rdzeniu.

## 11. Testy

`make test`, atrapa modelu, bez GPU i internetu. Zawiera wszystko z briefu sekcja 12 (każda kontrola min. 1 test pozytywny i 1 negatywny, pakiet OWASP 2026, hot reload, usuwanie kontroli, eksport, posture, feed, sygnatury, `sem.action_judge`, kanały, `authz.tool_schema`, wiązanie zatwierdzeń, budżety, benchmark, raport) oraz:

- **Routing i klasy:** test własnościowy na losowych sekwencjach, że sesja prywatna nigdy nie trafia do `external`; klasa lepka; jawny `external` w sesji prywatnej → BLOCK, a po przełączeniu na `reroute_local` ALLOW z `rerouted_from`; nieznane źródło → `default_class`; walidator odrzuca politykę z `external` dla klasy prywatnej; router padł → `local`; model lokalny padł → BLOCK `LOCAL_UNAVAILABLE`.
- **`dlp`:** sekret w prompcie i wyniku narzędzia zredagowany w locie; zbędne pole z narzędzia wycięte; PESEL w prompcie podnosi klasę; każdy próg przełączany w YAML na żywo; audyt i eksport bez PESEL-u i IBAN-u.
- **`output.safe`:** obcy link usunięty, reszta odpowiedzi dostarczona (REDACT); kanarek → BLOCK.
- **Ogólność:** drugi, sztuczny agent z innymi narzędziami i limitami, zdefiniowany tylko w YAML (np. płatności z `maximum` w schemacie i `on_violation: approval`), chroniony tymi samymi kontrolami bez zmian w kodzie; dwa agenty naraz, hot reload limitów jednego nie zmienia decyzji drugiego.
- **Architektura:** rdzeń nie importuje `harness/`.

## 12. Zgodność i źródła (web search 2026-10-03)

- **OWASP LLM Top 10 (2026):** LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure, LLM03 Excessive Agency, LLM04 Supply Chain, LLM05 Data and Model Poisoning, LLM06 Unbounded Consumption, LLM07 Misinformation, LLM08 Hidden Context Exposure, LLM09 Vector and Embedding Weaknesses, LLM10 Improper Output Handling. Zgodne z briefem. Źródła: hackerdna.com/blog/owasp-llm-top-10, cybersecuritynews.com/owasp-genai-llm-top-10-2026.
- **OWASP Agentic Top 10 (2026, opublikowane 9.12.2025):** ASI01 Agent Goal Hijack, ASI02 Tool Misuse and Exploitation, ASI03 Identity and Privilege Abuse, ASI04 Agentic Supply Chain Vulnerabilities, ASI05 Unexpected Code Execution, ASI06 Memory and Context Poisoning, ASI07 Insecure Inter-Agent Communication, ASI08 Cascading Failures, ASI09 Human-Agent Trust Exploitation, ASI10 Rogue Agents. Źródła: cycode.com/blog/owasp-top-10-agentic-applications, giskard.ai/knowledge/owasp-top-10-for-agentic-application-2026. **Zamyka otwarte pytanie z briefu sekcja 14.**
- **EU AI Act:** według źródeł wtórnych (Sidley, HaystackID) Digital Omnibus (Rozporządzenie (UE) 2026/1744, w mocy od 27.07.2026) przesunął obowiązki dla systemów wysokiego ryzyka z Annex III na 2.12.2027. Art. 12 wymaga automatycznego logowania zdarzeń, Art. 14 nadzoru człowieka z możliwością ingerencji. **Do sprawdzenia w Dzienniku Urzędowym przed PDF-em.** KYC nie jest automatycznie systemem wysokiego ryzyka, więc mówimy o zgodności wzorców, nie o compliance.
- **Jev (TypeSafe AI):** zewnętrzne API w early access, bez otwartych wag, deklarowane 70–500 ms; stąd atrapa i zasada „router widzi tylko metadane".

## 13. Kolejność prac

1. Szkielet rdzenia: `PolicyStore`, rejestry, `Pipeline` z `Timed`, `AuditSink`, `Telemetry`.
2. Klasy, źródła, `SessionLabels`, `ProviderDispatcher` z niezmiennikiem i `RuleBasedRouter`.
3. Kontrole deterministyczne i `dlp`, `log.redact`.
4. Feed sygnatur.
5. Kontrole AI (atrapa, potem Ollama): `sem.prompt_injection`, `sem.action_judge`.
6. `ApprovalService` i karta zatwierdzenia.
7. Proxy MCP i reference harness (KYC) + sztuczny agent do testów ogólności.
8. Dashboard i czat.
9. Test suite, benchmark, raport, diagram, README.

**Etapy:** MVP = punkty 1–9 powyżej. Etap 2: kolejne use case'y jako same konfiguracje, mapa przepływu danych. Etap 3: jak w sekcji 9.

## 14. Otwarte pytania i ryzyka

1. **Format API gatewaya** (brief sekcja 14, nadal otwarte). Proponowany domyślny: OpenAI-compatible `/v1/chat/completions` (Ollama i większość harnessów go obsługuje), adapter Anthropic `/v1/messages` jako opcja. **Wymaga decyzji.**
2. **Ryzyko względem Wytycznych:** redakcja w locie jest zawężona do czterech zadań. Wytyczne s.1 i s.4 pkt 1 mówią o „inspect, redact, or block" i „Block vs Redact" bez definicji, więc obecne rozwiązanie spełnia je przez `dlp.*.on_detect`, ale domyślne zachowanie dla danych osobowych to routing, nie redakcja.
3. **Egress danych prywatnych** do ujść poza bank w sesji zaufanej (bez `untrusted`): brief mówi ALLOW + log. Czy klasa `personal_data`/`bank_secret` ma samoczynnie wymuszać APPROVAL? Domyślnie nie, bo wykracza poza ustalenia.
4. Waluta wyświetlania: USD (zgodnie z polityką).
5. Model routera nie został wskazany, więc `RuleBasedRouter` jest jedyną dostarczaną implementacją (`OllamaRouter` opcjonalnie, `JevRouter` tylko jako adapter).
