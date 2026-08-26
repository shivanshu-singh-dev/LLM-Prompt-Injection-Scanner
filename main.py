import argparse
from pathlib import Path

from runner import load_payloads, run_scan
from detectors import heuristic, embedding, llm_judge
from report import combine_verdict, write_reports

def main():
    parser = argparse.ArgumentParser(description="LLM Prompt Injection Scanner")
    parser.add_argument("--payloads", default="payloads/payloads.yaml")
    parser.add_argument("--output", default="results")
    parser.add_argument("--skip-judge", action="store_true", help="skip the LLM-judge pass (faster, weaker)")
    args = parser.parse_args()

    print("Loading payloads...")
    payloads = load_payloads(args.payloads)
    payload_map = {p["id"]: p for p in payloads}

    print(f"Running {len(payloads)} payloads against target...")
    results = run_scan(payloads)

    print("Running heuristic detector...")
    for r in results:
        r["heuristic"] = heuristic.score(r["response_text"], payload_map[r["payload_id"]].get("expected_marker"))

    print("Running embedding detector...")
    for r in results:
        r["embedding"] = embedding.score(r["response_text"])

    if not args.skip_judge:
        print("Running LLM-judge detector (slower)...")
        for r in results:
            r["llm_judge"] = llm_judge.score(r["prompt"], r["response_text"])
    else:
        for r in results:
            r["llm_judge"] = {"flagged": False, "reasoning": "skipped", "raw": None}

    for r in results:
        r["verdict"] = combine_verdict(r["heuristic"], r["embedding"], r["llm_judge"])

    Path(args.output).mkdir(exist_ok=True)
    write_reports(results, args.output)

    compromised = sum(1 for r in results if r["verdict"]["compromised"])
    print(f"\nDone: {compromised}/{len(results)} payloads compromised the target.")
    print(f"Reports written to {args.output}/")

if __name__ == "__main__":
    main()
