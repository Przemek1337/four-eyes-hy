# four-eyes-hy

FourEyes is a gateway for AI-agent traffic: every prompt, tool call and document passes through central, hot-reloadable policy (`policy.yaml`), deterministic and AI controls, budgets and an audit log.

Quickstart: `make install && make test && MODEL=mock make run`, then open `http://127.0.0.1:8080/ui/`.

## Policy

`policy.yaml` is commented line by line and reloads as soon as the file changes. Each control has a `mode` (`enforce`, `monitor`, `redact`).

## Decision models

Three AI controls ask narrow questions of local decision models named in `policy.yaml` (`decision_models:`):

| Control | Model | Question |
|---|---|---|
| `sem.prompt_injection` | Basal-1.0 1.5B | one yes/no question per named rule; score = highest P(yes) |
| `data.classify_net` | Basal-1.0 1.5B | which data class (public / personal_data / bank_secret); can only raise the class |
| `sem.action_judge` | Basal-1.0 1.5B | consistent / out_of_scope, from the task and the REAL call parameters only |

An unconfident answer (`confidence < min_confidence`) escalates data classification and action review. Document injection uses `documents.on_uncertain: monitor`: low confidence creates a separate audit alert, while `high_risk` requires a score of at least 0.7 or a known attack signature. Detector outages still flag documents. A content-reading control can never use an `external` model (the policy is rejected). Switch a model live by editing `model:` in `policy.yaml`.

The MVP uses one local Basal 1.5B server for all three controls. Build and start it on an NVIDIA GPU:

Docker Desktop with NVIDIA GPU support can build the UI, gateway and Basal together:

```sh
docker volume create foureyes-basal-cache
docker compose up -d --build --wait
```

Open `http://127.0.0.1:8080/ui/`. Compose waits for Basal before starting the gateway,
uses real decision models, and retains model weights and the gateway audit in volumes.
To rebuild and recreate running services, use `docker compose up -d --build --force-recreate --wait`.
The policy, signature feed and local test reports are mounted from the workspace.
Use `docker compose down` to stop the stack while retaining its data.

To run only the model server manually:

```sh
docker build -t foureyes-basal:1.0.1 -f scripts/models/Dockerfile.basal scripts/models
docker run -d --name foureyes-basal --gpus all -p 127.0.0.1:8000:8000 -v foureyes-basal-cache:/models foureyes-basal:1.0.1
```

The first start downloads the model. BF16 with `eager` avoids FP8 compilation and graph warmup on the laptop's Ada GPU. Run the scripted agent with real decision models using `MODEL=mock DECISION_MODELS=live make run`; `MODEL=mock make run` uses deterministic mocks throughout. In a Docker gateway set `BASAL_URL=http://host.docker.internal:8000`. The decision timeout is 10 seconds for this laptop MVP. `make eval-models` evaluates only models used by active controls.

The [live spike results and calibration correction](docs/superpowers/notes/2026-10-04-decision-models-spike.md) document the initial false positive and its fix: uncertainty no longer labels a clean document as an attack. Basal 1.5B still misses some injection examples; deterministic signatures and authorization controls remain necessary.

Granite Guardian remains an optional adapter and policy entry; the MVP does not start or contact it. To try it later, run its server on port 8001 and set `sem.prompt_injection.model: granite_guardian`. Its live prompt/logprobs verification is still pending.

Demo: `make demo-docs` (PDFs), `make calibrate-note` (borderline note on the live model), `MODEL=mock make run` or `make run`, then `make demo`. Drop a PDF into the Playground (`/admin/chat`, document mode) to send it through the gateway as a client document. `make eval-models` writes `reports/decision_models_eval.json` (accuracy per model, check and language; p50/p95 latency).

Without Python 3.11+ on the host, run the gateway in Docker: `docker run -d --name foureyes-demo -p 8080:8080 -v "$PWD":/src:ro -e MODEL=mock python:3.12-slim sh -c "cp -r /src /app && cd /app && pip install -q -e '.[dev,harness]' && exec python -m foureyes.cli serve --policy /src/policy.yaml --harness kyc --host 0.0.0.0"` (the policy file is read from the repo, so editing it reloads the gateway live).

Registries: files by default; `KRS_LIVE=1` for the public KRS API, `CH_API_KEY=<key>` for Companies House.

Playground uploads get their own client scope. For supported KRS and Companies House extracts, the document's company name and registry number appear in the reply and determine the registry lookup. Onboarding continues only if the registry record matches the document. An unknown company or unsupported extract is reviewed for manipulation without running onboarding; unavailable registry records require additional verification. In file mode, a missing fixture is explicitly reported as unverified, rather than a claim that the company does not exist.

## Honest limits

- Granite Guardian is trained and tested on English only; Polish documents are measured in `make eval-models`.
- The gateway knows agent keys, not people: one `agents:` entry per person/tool until human identity lands (remediation plan).

## Licenses

Granite Guardian 4.1 (Apache-2.0), Basal-1.0 (Apache-2.0), reportlab (BSD), pypdf (BSD-3), python-multipart (Apache-2.0).
