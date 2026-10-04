# Synthetic attack corpus

`make test` runs about 1,100 tests. They record about 850 generated cases on fictitious KYC data (about 590 attacks
and 250 legitimate cases), grouped by OWASP LLM Top 10 (2026). The suite reports a detection rate, a false-block rate and a list of known gaps, so the
numbers are measured rather than claimed.

## Where things are

| File | What it does |
|---|---|
| `src/harness/kyc/synth.py` | Seeded generators: PESEL, IBAN, NIP, passport and secrets that pass their checksums; fictitious companies and directors; clean and poisoned client documents; 17 concealment techniques |
| `tests/test_synth.py` | The generators themselves: checksums hold, output is reproducible from a seed, look-alike numbers are not identifiers |
| `tests/test_attack_matrix.py` | The attack matrix, many variants per OWASP category (see below) |
| `tests/test_benign_corpus.py` | Legitimate traffic that must pass: false blocks are counted |
| `tests/test_properties.py` | Hypothesis tests: statements that must hold for any input |
| `src/foureyes/detect/normalize.py` | Undoes concealment before detection (look-alike letters, zero-width, spacing, leetspeak, full-width, base64, ROT13) |

## How a case is judged

Each attack case is either `stop` (must be stopped, the test fails otherwise) or `gap` (a documented limitation,
measured and reported but not asserted). Every case is recorded, and `reports/test_report.json` gets a `corpus`
block that the dashboard shows under "Proof it works": detection rate, false-block rate, results per OWASP
category and per technique, and the list of known gaps.

## What the matrix covers

- **LLM01** 17 concealment techniques x 14 instructions in a chat prompt, and 17 x 3 in a client document. For
  documents it asserts the wall: whatever the detector decided, the fooled agent cannot send data out or submit a
  client. `test_each_layer_alone_stops_exfiltration...` removes layers to show the wall tests measure something.
- **LLM02** identifiers written the way people type them (spaces, hyphens, lower case, no country code) never reach
  the paid model; secrets of 11 kinds are redacted; look-alike numbers are not treated as personal data; nothing
  from a 25-person batch reaches the audit log.
- **LLM03** missing or forged credentials, tools outside the agent's list (including spelling tricks), 13 schema
  violations, submission without sanctions screening, tampering with an approved call.
- **LLM04** 12 dangerous callables x 6 containers (plain pickle, torch zip, `.bin`, pickle renamed to
  `.safetensors` or `.gguf`, upper-case extension), untrusted sources and formats, code in tool arguments, and
  clean artifacts and ordinary notes that must pass.
- **LLM05** the case status cannot be changed through notes however the field is spelled; notes written after a
  poisoned document stay untrusted; poison planted in the shared index cannot egress.
- **LLM06** step loops, token cap, huge prompts and batch runs against the paid budget.
- **LLM07** no grounding control yet. Recorded as a gap, not hidden.
- **LLM08** the system prompt canary in 7 spellings; 8 phrasings of "show me your instructions".
- **LLM09** 10 ways to reach another client's records.
- **LLM10** 26 outputs: foreign links and images in every markdown and HTML form, active HTML, `javascript:` and
  `data:` URIs, and harmless output that must not be altered.

## Gaps the corpus found, and fixed

Writing the corpus before fixing anything exposed real gaps. These are now closed and covered by tests:

- obfuscated instructions (base64, ROT13, look-alike letters, full-width, spaced letters, zero-width) were not detected
- PESEL with a space or hyphen, lower-case IBAN, IBAN without country code and lower-case passport were not classified as personal data, so they could be sent to a paid external model
- `output.safe` ignored raw HTML, reference-style links, autolinks, protocol-relative URLs and canary variants
- the pickle denylist missed `os.popen`, `shutil`, `socket`, `runpy`, `importlib`, `io`; a pickle renamed to `.safetensors` was never scanned
- `case_status` was protected in one spelling only
- results of `search_documents` were not labelled untrusted
- no length limit on entity fields; no patterns for Stripe, Slack, JWT, Google keys

## Gaps that remain (measured, reported)

Paraphrased or translated attacks ("Forget everything you were told earlier"), role-play framings, leetspeak and
letter-spacing variants that the normaliser only partly undoes, indirect requests for the system prompt, and
LLM07 grounding. The prompt-injection detector in tests is a deterministic stand-in; real classifier numbers
need the model run (`make redteam-live`, not built yet). The wall tests show these gaps do not turn into harm:
detection raises the risk, provenance enforces the wall.

## Demo traffic for the dashboard

`make demo-traffic` sends about 80 requests (attacks across all OWASP categories, legitimate cases, a four-eyes
approval flow) to a running gateway, so blocked threats, session timelines and the approval queue are populated.
It checks each request against what the policy should do and exits non-zero if an attack gets through. Cases whose
outcome depends on the model repeating text back (output handling) are shown but not counted.
