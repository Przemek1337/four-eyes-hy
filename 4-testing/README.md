# 4. Testing: the self-testing suite

```sh
make install
make test        # runs everything, no GPU and no network needed
```

`make test` runs `pytest` and writes `reports/test_report.json`, which the dashboard shows in the **Proof** tab.
Positive cases (must be allowed) and negative cases (must be blocked, redacted or sent to a human) sit side by side.

## Latest result (local run, 2026-10-04)

| | Passed | Failed |
|---|---:|---:|
| **All tests** | **1316** | **0** |
| Positive cases (allowed) | 211 | 0 |
| Negative cases (blocked or redacted) | 668 | 0 |

`reports/` is not committed (git-ignored); run `make test` to regenerate these numbers on your machine.

### Synthetic attack corpus (fictitious KYC data, seeded, reproducible)

| | Cases | Result |
|---|---:|---|
| Attacks | 600 | **478 stopped, 79.7% detection** |
| Legitimate traffic | 252 | **0 false blocks** |
| Known gaps (measured, reported, not hidden) | 122 | paraphrased or translated injection, role-play framings, partly undone obfuscation, LLM07 |

The "known gaps" are attacks that the deterministic stand-in detector does not catch. The wall tests show that
they do not become harm: a fooled agent still cannot send data out or submit a client without a human.
How the corpus is built: [../docs/attack-corpus.md](../docs/attack-corpus.md).

### Tests per OWASP LLM category

| Category | Passed |
|---|---:|
| LLM01 Prompt Injection | 448 |
| LLM02 Sensitive Information Disclosure | 111 |
| LLM03 Excessive Agency | 60 |
| LLM04 Supply Chain | 96 |
| LLM05 Data and Model Poisoning | 17 |
| LLM06 Unbounded Consumption | 13 |
| LLM07 Misinformation | 2 (known gap) |
| LLM08 Hidden Context Exposure | 17 |
| LLM09 Vector and Embedding Weaknesses | 19 |
| LLM10 Improper Output Handling | 30 |

## Showcase test cases

| Case | Type | Expected | Test file |
|---|---|---|---|
| Missing or forged agent key | negative | BLOCK, audited | `tests/test_gateway_api.py` |
| Clean chat request | positive | ALLOW, OpenAI-shaped answer | `tests/test_gateway_api.py` |
| PESEL in a prompt, then external model requested | negative | class raised, external BLOCK | `tests/test_gateway_api.py`, `tests/test_routing.py` |
| Public question may use the external model | positive | ALLOW, recorded | `tests/test_gateway_api.py` |
| Local model down with private data | negative | BLOCK, never fall back to external | `tests/test_gateway_api.py`, `tests/test_invariants.py` |
| Poisoned document, agent tries to email data out | negative | APPROVAL; human approves the exact call only | `tests/test_gateway_api.py`, `tests/test_provenance.py` |
| Clean case end to end; approval denied | positive and negative | mail not sent after deny | `tests/test_gateway_api.py`, `tests/test_approvals.py` |
| Submit client without sanctions screening | negative | BLOCK | `tests/test_authz.py` |
| Tool not on the agent's list, schema violations | negative | BLOCK | `tests/test_authz.py` |
| Other client's records via search | negative | filtered | `tests/test_gateway_api.py`, `tests/test_attack_matrix.py` |
| 17 concealment techniques (base64, zero-width, look-alikes, ...) | negative | stopped or walled | `tests/test_attack_matrix.py` |
| Malicious pickle, pickle renamed `.safetensors` | negative | BLOCK | `tests/test_signatures.py`, `tests/test_attack_matrix.py` |
| Foreign image or link in model output | negative | removed | `tests/test_dlp_output.py` |
| Step loop, token cap, spend over budget | negative | BLOCK | `tests/test_budgets.py` |
| Policy edited at runtime: control removed, threshold changed | both | takes effect on the next request | `tests/test_policy_live.py` |
| New use case defined only in YAML | positive | works without code changes | `tests/test_generality.py` |
| Properties for any input (Hypothesis) | both | invariants hold | `tests/test_properties.py` |
| Legitimate corpus | positive | **0 false blocks** | `tests/test_benign_corpus.py` |
| Architecture rule: core never imports the demo agent | structure | holds | `tests/test_architecture.py` |

## Other ways to test

| Command | What |
|---|---|
| `make bench` | gateway overhead benchmark (p50, p95) |
| `make demo` | scripted KYC demo scenarios |
| `make demo-traffic` | about 80 requests across all OWASP categories to a running gateway; exits non-zero if an attack gets through |
| `make eval-models` | accuracy and latency of the decision models (needs the real local model) |
| `make smoke` | UI smoke test |
| Playground, **Run test attack** | the same staged attacks from the browser |

Judges can also edit `policy.yaml` or `feeds/signatures.json` while the gateway is running and send their own prompts.
