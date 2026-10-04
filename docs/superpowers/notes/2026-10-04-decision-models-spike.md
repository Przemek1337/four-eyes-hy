# Spike: jeden Basal dla MVP (2026-10-04)

Decyzja użytkownika: MVP ma używać jednego lokalnego modelu do wykrywania manipulacji,
klasyfikacji poufności i oceny operacji. Domyślna polityka kieruje wszystkie trzy kontrole
do Basala 1.5B. Granite pozostaje opcjonalnym adapterem; jego weryfikacja live jest nadal
nieukończona. Reguła `jailbreak` ma jawne kryterium zamiast `builtin`, więc Basal jej nie pomija.

## Uruchomione środowisko

| Element | Wynik |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB |
| Model | `Remek/basal-1.0-1.5B`, BF16, rewizja `81a74acc6e7f7604008697b2daa83b3652d85b68` |
| Silnik | rkinas/basal, tag `v1.0.1`; torch `2.11.0+cu128`, transformers `5.17.0` |
| Tryb | `eager --dtype bfloat16`, dwa porządki opcji i kalibracja serwera (domyślne) |
| Start z pobranymi wagami | log serwera: gotowy w 7 s |
| Pamięć GPU po demo | 3734 MiB łącznie z procesami systemowymi |
| API | `/health` działa; `/v1/systemone`: `noul` i `choice` działają |
| Gateway | `MODEL=mock DECISION_MODELS=live`, agent skryptowy, wszystkie trzy oceny AI z prawdziwego Basala |
| Adresy | Basal `127.0.0.1:8000`, gateway `127.0.0.1:8080`, kontener gatewaya używa `BASAL_URL=http://host.docker.internal:8000` |
| Testy offline | 413 passed |

Obraz buduje `scripts/models/Dockerfile.basal`. Kontenery: `foureyes-basal` i `foureyes-mvp`.
Wagi są w trwałym wolumenie `foureyes-basal-cache`. Aby wznowić po zatrzymaniu:

```sh
docker start foureyes-basal foureyes-mvp
```

Próba `fast-nocompile` przygotowywała grafy, zajmowała około 6874 MiB VRAM i nie osiągnęła
gotowości w 120-sekundowym oknie sprawdzenia. Zatrzymano ją na rzecz `eager`.
FP8 nie było testowane w tej sesji. Dokumentacja silnika wspomina o problemie kompilacji
FP8 na Ada: https://github.com/rkinas/basal/tree/v1.0.1.

## Pomiary i ograniczenia

Uruchomiono odpowiedniki `make calibrate-note`, `make eval-models` i `make demo` przez
moduły Pythona w Dockerze (host ma Python 3.9 i nie ma `make`).

| Kontrola | Liczba przykładów | Trafność wyniku polityki | Niepewne | p50 / p95 |
|---|---:|---:|---:|---|
| Manipulacja | 8 | 0.50 | 8 | 394.89 / 792.24 ms |
| Poufność | 4 | 0.75 | 1 | 112.25 / 114.67 ms |
| Operacja | 4 | 0.00 | 4 | 115.94 / 117.25 ms |

To mały zestaw demo, nie miara jakości ogólnej. Ewaluator liczy wynik kontroli po zastosowaniu
progu pewności, a nie wyłącznie surowy wybór modelu. Przy `min_confidence: 0.9` wszystkie
przykłady manipulacji podnoszą ryzyko, w tym czyste teksty. Cztery oceny operacji są
abstencjami (`uncertain`, prowadzącymi do APPROVAL), a nie czterema pewnymi błędnymi wyborami.
Przykład poufnego limitu klienta otrzymał `bank_secret` z pewnością 0.9958.

Kalibracja znalazła pierwszą kandydatkę z pewnością 0.6422; zapisano metadane Basala w
`src/harness/demo_documents/borderline_note.json` i odtworzono PDF-y.

Demo live: **4/5 PASS**. `injected_registry_extract`, `borderline_registry_extract`,
`uk_registry_extract` i `developer_without_access` przeszły. `clean_registry_extract`
nie przeszedł wyłącznie sprawdzenia „no high_risk”: niepewność modelu oznacza czysty dokument
jako ryzykowny. Status oczekiwania na zatwierdzenie i sprawdzenie rejestru były poprawne.
Nie obniżano progów w celu poprawienia wyniku demo. Kontrole deterministyczne nadal
egzekwują uprawnienia, zakres klienta, kolejność narzędzi, redakcję i lokalne przetwarzanie
danych prywatnych. MVP demonstruje cały przepływ z jednym modelem; jakość ocen wymaga
dalszej kalibracji przed użyciem poza demo.

Pełny raport lokalny: `reports/decision_models_eval.json`; pojedyncze odpowiedzi:
`reports/spike/basal_probe.json`. Domyślna ewaluacja kontaktuje tylko modele używane przez
aktywne kontrole, więc nie wymaga uruchomienia Granite.
