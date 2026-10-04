# four-eyes-hy

FourEyes is a gateway for AI-agent traffic: every prompt, tool call and document passes through central, hot-reloadable policy (`policy.yaml`), deterministic and AI controls, budgets and an audit log.

Quickstart: `make install && make test && MODEL=mock make run`, then open `http://127.0.0.1:8080/ui/`.

## Policy

`policy.yaml` is commented line by line and reloads as soon as the file changes. Each control has a `mode` (`enforce`, `monitor`, `redact`).

## Decision models

Three AI controls ask narrow questions of local decision models named in `policy.yaml` (`decision_models:`):

| Control | Model | Question |
|---|---|---|
| `sem.prompt_injection` | Granite Guardian 4.1 8B (vLLM) | one yes/no question per named rule; score = highest P(yes) |
| `data.classify_net` | Basal-1.0 4.5B | which data class (public / personal_data / bank_secret); can only raise the class |
| `sem.action_judge` | Basal-1.0 4.5B | consistent / out_of_scope, from the task and the REAL call parameters only |

An unconfident answer (`confidence < min_confidence`) always goes to the stricter side. A content-reading control can never use an `external` model (the policy is rejected). Switch a model live by editing `model:` in `policy.yaml`.

Run the models (NVIDIA GPU): `vllm serve ibm-granite/granite-guardian-4.1-8b --port 8001` and the Basal server on port 8000. The live spike that verifies the exact prompt strings against running servers has not been run yet (Task 0 is pending), so the Granite Guardian prompt constants are taken from the model card and are unverified. Without the models, `MODEL=mock make run` uses a deterministic mock.

Demo: `make demo-docs` (PDFs), `make calibrate-note` (borderline note on the live model), `MODEL=mock make run` or `make run`, then `make demo`. Drop a PDF into the Playground (`/admin/chat`, document mode) to send it through the gateway as a client document. `make eval-models` writes `reports/decision_models_eval.json` (accuracy per model, check and language; p50/p95 latency).

Without Python 3.11+ on the host, run the gateway in Docker: `docker run -d --name foureyes-demo -p 8080:8080 -v "$PWD":/src:ro -e MODEL=mock python:3.12-slim sh -c "cp -r /src /app && cd /app && pip install -q -e '.[dev,harness]' && exec python -m foureyes.cli serve --policy /src/policy.yaml --harness kyc --host 0.0.0.0"` (the policy file is read from the repo, so editing it reloads the gateway live).

Registries: files by default; `KRS_LIVE=1` for the public KRS API, `CH_API_KEY=<key>` for Companies House.

## Honest limits

- Granite Guardian is trained and tested on English only; Polish documents are measured in `make eval-models`.
- The gateway knows agent keys, not people: one `agents:` entry per person/tool until human identity lands (remediation plan).

## Licenses

Granite Guardian 4.1 (Apache-2.0), Basal-1.0 (Apache-2.0), reportlab (BSD), pypdf (BSD-3), python-multipart (Apache-2.0).
