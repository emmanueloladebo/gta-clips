import os
import httpx
from packages.shared.config import settings

def test():
    key = settings.GROQ_API_KEY
    for model in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
        print(f"\n--- Testing model {model} ---")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You output valid JSON."},
                {"role": "user", "content": "Return a JSON object with 'headline': 'GTA 6 RAMPAGE'"}
            ],
            "response_format": {"type": "json_object"}
        }
        try:
            r = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=15)
            print("STATUS:", r.status_code)
            print("TEXT:", r.text[:300])
        except Exception as e:
            print("ERROR:", e)

if __name__ == "__main__":
    test()
