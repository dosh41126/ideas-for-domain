import psutil
import hashlib
import base64
import random
import json
import asyncio
import threading
import time
import httpx

# ========== ENTROPY STATE SCANNER ==========
def get_entropy_state():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    net = psutil.net_io_counters().bytes_sent + psutil.net_io_counters().bytes_recv
    rand = random.random()
    raw = f"{cpu:.2f}-{mem:.2f}-{disk:.2f}-{net}-{rand:.6f}"

    h1 = hashlib.sha256(raw.encode()).digest()
    h2 = hashlib.sha256(h1).digest()
    final = bytes(a ^ b for a, b in zip(h1, h2))
    entropy_b64 = base64.b64encode(final).decode()
    color_index = int(final[0]) % 25

    return {
        "cpu": cpu,
        "mem": mem,
        "disk": disk,
        "net": net,
        "rand": rand,
        "entropy_hash": entropy_b64,
        "color_index": color_index
    }

# ========== BUILD LLM PROMPT ==========
def build_prompt(local, remote):
    return [
        {
            "role": "system",
            "content": "You are a quantum entropy sync evaluator AI. Your job is to determine whether two devices are in sync based on their entropy profiles."
        },
        {
            "role": "user",
            "content": f"""
Two devices have provided the following entropy states.

Device A:
- CPU: {local['cpu']}%
- RAM: {local['mem']}%
- Disk: {local['disk']}%
- Net I/O: {local['net']}
- Color Index: {local['color_index']}
- Entropy Hash: {local['entropy_hash'][:16]}...

Device B:
- CPU: {remote['cpu']}%
- RAM: {remote['mem']}%
- Disk: {remote['disk']}%
- Net I/O: {remote['net']}
- Color Index: {remote['color_index']}
- Entropy Hash: {remote['entropy_hash'][:16]}...

Based on the closeness of these values, determine the sync level:

- GREEN: Perfect sync
- YELLOW: Acceptable drift, no key rotation needed yet
- GREY: Desync detected, rotate provisioning keys now

Reply in JSON format:
{{
  "sync_status": "GREEN" | "YELLOW" | "GREY",
  "recommendation": "text..."
}}
"""
        }
    ]

# ========== CALL LLM CHAT COMPLETIONS ==========
async def query_llm_chat(local_state, remote_state, endpoint_url, api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4",  # or llama3, etc.
        "temperature": 0,
        "messages": build_prompt(local_state, remote_state)
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(endpoint_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            return json.loads(text)
        except Exception as e:
            print("❌ LLM request failed:", e)
            return {"sync_status": "error", "recommendation": str(e)}

# ========== MAIN RUNNER ==========
async def main():
    print("📡 Scanning local + remote entropy states...\n")
    local = get_entropy_state()
    remote = get_entropy_state()  # Simulate second device

    for dev, label in zip([local, remote], ['LOCAL', 'REMOTE']):
        print(f"🔹 {label} Device:")
        for k, v in dev.items():
            print(f"  {k}: {v}")
        print("")

    # Replace with your actual LLM endpoint and key
    endpoint = "https://api.openai.com/v1/chat/completions"  # or your Ollama / llama.cpp endpoint
    api_key = "your_openai_or_local_api_key_here"

    print("🔍 Asking LLM to evaluate sync level...\n")
    result = await query_llm_chat(local, remote, endpoint, api_key)

    print("\n✅ LLM Sync Result:")
    print(json.dumps(result, indent=2))

# ========== RUN ASYNC ==========
if __name__ == "__main__":
    asyncio.run(main())
