# LLM Prompt Injection Scanner

A CLI tool that tests whether a locally-hosted LLM can be manipulated into ignoring its instructions via prompt injection. Sends a library of attack payloads to a target model, evaluates each response with three independent detectors, and outputs a report showing which attacks succeeded.

## Status

Working end-to-end against a local Ollama-hosted model (tested with `llama3.2`). Not yet tested against any cloud API.

## Architecture

```
prompt-injection-scanner/
├── payloads/
│   └── payloads.yaml       # attack library
├── detectors/
│   ├── heuristic.py         # marker match + regex
│   ├── embedding.py         # semantic similarity
│   └── llm_judge.py         # LLM-as-judge
├── runner.py                # sends payloads to the target, logs raw responses
├── report.py                # merges detector verdicts, writes JSON + HTML
├── main.py                  # single CLI entrypoint
└── requirements.txt
```

## Payload library

50 payloads across 3 categories, each tagged with the specific technique it tests:

| Category | What it tests |
|---|---|
| `role_override` | Direct attempts to override or leak the model's instructions (authority spoofing, delimiter injection, payload splitting, leetspeak obfuscation) |
| `jailbreak` | Framing tricks rather than direct instruction attacks (roleplay personas, hypothetical distancing, emotional/urgency pressure, few-shot poisoning, echo/repeat-after-me) |
| `indirect` | Instructions hidden inside content the model is asked to process — documents, code comments, JSON fields, fake tool output, ROT13/zero-width-character obfuscation, long-context distraction |

Most payloads ask the model to output a specific benign marker string (e.g. `DELIMITER_BYPASS`) rather than requesting genuinely harmful content. This keeps success/failure unambiguous — the marker either appears in the response or it doesn't — without requiring the scanner to evaluate real harmful output.

## Detection

A payload is marked **compromised** if any one of three independent detectors flags it. Each result records which detector(s) fired, so a 3/3 agreement and a single-detector catch are distinguishable.

1. **Heuristic** (`heuristic.py`) — exact match against the payload's expected marker string, falling back to regex patterns for compliance language (e.g. "sure, I will...").
2. **Embedding** (`embedding.py`) — encodes the response with `sentence-transformers` (`all-MiniLM-L6-v2`) and compares cosine similarity against small sets of compliance-sounding vs. refusal-sounding exemplar sentences.
3. **LLM-judge** (`llm_judge.py`) — sends the original payload and the response to a separate model call, which returns a structured yes/no judgment on whether compliance occurred.

## Setup

Requires Python 3.10+ and [Ollama](https://ollama.com) installed and running locally.

```bash
ollama pull llama3.2
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Optional flags:

| Flag | Purpose |
|---|---|
| `--payloads <path>` | Use a different payload file (default: `payloads/payloads.yaml`) |
| `--output <dir>` | Change the results directory (default: `results/`) |
| `--skip-judge` | Skip the LLM-judge pass for a faster (less accurate) run |

## Output

- `results/report.json` — full detail: every payload, raw response, and all three detectors' individual verdicts
- `results/report.html` — a readable summary table (payload, category, technique, compromised, which signals fired, confidence)

## Known limitations

- **Target support is Ollama-only.** `runner.py` calls Ollama's native `/api/generate` endpoint. It does not yet speak the OpenAI chat-completions schema, so it will not work against OpenAI or other OpenAI-compatible APIs without changes.
- **LLM-judge defaults to judging its own target model.** Using `llama3.2` to judge `llama3.2`'s responses risks self-grading bias — a model susceptible to a jailbreak may also misjudge whether it just fell for one. Set `JUDGE_MODEL` in `llm_judge.py` to a different pulled model (e.g. `mistral`) to avoid this.
- **Embedding detector threshold is hand-tuned**, not statistically validated against a labeled dataset.
- **No automated tests.**

## Not yet implemented

- OpenAI-compatible API support for the target model
- Automated test suite
- Comparative scanning across multiple models in a single run