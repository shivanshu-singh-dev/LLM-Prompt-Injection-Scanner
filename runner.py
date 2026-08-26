import requests
import yaml
import time
from datetime import datetime
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

def load_payloads(path="payloads/payloads.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def send_payload(prompt: str, retries: int = 2, timeout: int = 30) -> dict:
    for attempt in range(retries + 1):
        try:
            start = time.time()
            resp = requests.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "stream": False},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "response_text": data.get("response", ""),
                "latency_sec": round(time.time() - start, 2),
                "error": None,
            }
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                return {
                    "response_text": None,
                    "latency_sec": None,
                    "error": str(e),
                }
            time.sleep(1)

def run_scan(payloads: list[dict]) -> list[dict]:
    results = []

    for i, payload in enumerate(payloads, 1):
        print(f"[{i}/{len(payloads)}] Sending {payload['id']} ({payload['category']})...")

        outcome = send_payload(payload["prompt"])

        results.append({
            "payload_id": payload["id"],
            "category": payload["category"],
            "technique": payload["technique"],
            "prompt": payload["prompt"],
            "response_text": outcome["response_text"],
            "latency_sec": outcome["latency_sec"],
            "error": outcome["error"],
            "timestamp": datetime.utcnow().isoformat(),
        })

    return results

if __name__ == "__main__":
    payloads = load_payloads()
    results = run_scan(payloads)

    succeeded = sum(1 for r in results if r["error"] is None)

    print(f"\nDone: {succeeded}/{len(results)} calls succeeded, {len(results) - succeeded} errored.")

    with open("raw_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("Raw results written to raw_results.json")