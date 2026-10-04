# Local decision model

## Why local

The AI guard has to read exactly the data we are protecting: client documents, personal data, bank secrets.
Sending that to a cloud model to decide whether it is safe would defeat the purpose. So FourEyes runs its decision
model **on our own machine**, and the policy validator rejects any configuration where a content-reading control uses
an `external` model.

## What runs

| | |
|---|---|
| Model | **Basal-1.0 1.5B** (Apache-2.0), served locally in Docker (`scripts/models/Dockerfile.basal`) |
| Hardware used | NVIDIA RTX 4060 Laptop, 8 GB; BF16, `eager` mode; ready in about 7 s with weights cached; about 3.7 GB VRAM |
| Used by | `sem.prompt_injection`, `data.classify_net`, `sem.action_judge` (one model, three narrow questions) |
| Interface | one yes/no or multiple-choice question per call, answer with a probability; no free text generation, so the guard itself cannot be talked into doing something |

## Demo mode: mocked answers

**In the demo the model is not running.** `MODEL=mock make run` uses deterministic mocked answers for the agent
and the decision models. The gateway, policy, controls, approvals, budgets, audit and dashboard are real; only the
model's verdicts are scripted. To use the real local model:

```sh
docker compose up -d --build --wait                 # gateway + UI + Basal (NVIDIA GPU)
# or: MODEL=mock DECISION_MODELS=live make run      # scripted agent, real Basal
```

## Which model would do best

| Option | Verdict |
|---|---|
| **Basal-1.0 1.5B** (what the code runs) | Small, fast (about 110 ms per answer, up to about 800 ms for injection), fits a laptop. Often uncertain on our demo set, which is why uncertainty goes to a human |
| **IBM Granite Guardian 4.1 8B** | Purpose-built safety classifier, supported as an optional adapter in `policy.yaml` (`decision_models.granite_guardian`). Best next step for injection detection. English-trained: Polish needs measuring. Live verification still pending |
| **Larger instruction model (7 to 8B) behind the same yes/no interface** | More accurate on paraphrased and translated attacks, needs a bigger GPU. Same adapter shape, change `model:` in the policy |

Recommendation: keep Basal for the fast path (classification, action scope) and put Granite Guardian on
`sem.prompt_injection` once its live check is done. Both are one line in `policy.yaml`, switchable live.

## Example classifications (screenshots)

> Add screenshots here before submitting. Suggested: Playground, then Security tab, open a session, and capture the
> timeline row with the AI assessment. Files go to `1-solution/screenshots/`.

| Example | Expected result | Screenshot |
|---|---|---|
| Registry extract with hidden "skip sanctions screening, email data out" | document `high_risk`; later email goes to approval | `screenshots/injected-document.png` (TODO) |
| Clean registry extract | passes, no flag | `screenshots/clean-document.png` (TODO) |
| Borderline note (low confidence) | separate alert, not an invented detection | `screenshots/borderline-note.png` (TODO) |
| Text with an IBAN pasted into a prompt | class raised to `personal_data`, routed local | `screenshots/data-class-raised.png` (TODO) |
| Email to an outside domain | approval card with real recipient and AI judge flag | `screenshots/approval-card.png` (TODO) |

## Measured on the real model (2026-10-04, small demo set, not a general benchmark)

| Control | Examples | Policy-level accuracy | Uncertain | p50 / p95 |
|---|---:|---:|---:|---|
| Injection | 8 | 0.50 | 8 | 395 / 792 ms |
| Data class | 4 | 0.75 | 1 | 112 / 115 ms |
| Action review | 4 | 0.00 | 4 | 116 / 117 ms |

The low numbers are mostly **abstentions** at `min_confidence: 0.9` (sent to a human), not confident wrong answers.
We did not lower thresholds to improve the demo. Source: [docs/superpowers/notes/2026-10-04-decision-models-spike.md](../docs/superpowers/notes/2026-10-04-decision-models-spike.md).
Re-measure with `make eval-models`.
