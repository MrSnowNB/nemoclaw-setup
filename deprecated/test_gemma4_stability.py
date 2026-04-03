import asyncio
import httpx
import time
import json
import subprocess
import os

BASE_URL = "http://localhost:11466/api/chat"
MODEL = "gemma4-31b-it"

async def get_vram_usage():
    try:
        # Check all 4 GPUs on the Z8 Fury
        cmd = "nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits"
        output = subprocess.check_output(cmd, shell=True).decode().strip().split('\n')
        return sum(int(x) for x in output)
    except Exception:
        return 0

async def send_request(client, prompt, thinking=False, max_tokens=1024):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.7,
        }
    }
    
    if thinking:
        payload["messages"].insert(0, {"role": "system", "content": "<|think|>"})

    start_time = time.time()
    try:
        response = await client.post(BASE_URL, json=payload, timeout=300.0)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            tokens = data.get("eval_count", 0)
            duration = end_time - start_time
            tps = tokens / duration if duration > 0 else 0
            return {
                "status": "success",
                "duration": duration,
                "tokens": tokens,
                "tps": tps,
                "thinking": thinking
            }
        else:
            return {"status": f"error {response.status_code}", "content": response.text}
    except Exception as e:
        return {"status": "exception", "error": str(e)}

async def run_stability_test():
    async with httpx.AsyncClient() as client:
        print(f"--- Starting Stability Test for Gemma-4-31B on {BASE_URL} ---")
        
        # 1. Warm-up
        print("Warming up...")
        await send_request(client, "Hello, who are you?")
        
        # 2. Concurrency Test
        print("\nRunning Concurrency Test (5 simultaneous requests)...")
        prompts = [
            "Explain quantum entanglement in simple terms.",
            "Write a Python script to scrape a website.",
            "What are the main causes of the French Revolution?",
            "Summarize the plot of Blade Runner 2049.",
            "How do I optimize a PostgreSQL database for high read volume?"
        ]
        
        vram_before = await get_vram_usage()
        start_concurrent = time.time()
        tasks = [send_request(client, p) for p in prompts]
        results = await asyncio.gather(*tasks)
        end_concurrent = time.time()
        vram_after = await get_vram_usage()
        
        successes = [r for r in results if r["status"] == "success"]
        print(f"Concurrency Results: {len(successes)}/5 successful")
        if successes:
            avg_tps = sum(r["tps"] for r in successes) / len(successes)
            print(f"Average TPS: {avg_tps:.2f}")
        print(f"Total time: {end_concurrent - start_concurrent:.2f}s")
        print(f"VRAM Delta: {vram_after - vram_before} MB")

        # 3. Thinking Mode Test
        print("\nTesting Thinking Mode...")
        result_think = await send_request(client, "Solve this riddle: I have keys but no locks. I have a space but no room. You can enter, but never leave. What am I?", thinking=True)
        print(f"Thinking Mode Status: {result_think['status']}")
        if result_think["status"] == "success":
            print(f"Thinking Duration: {result_think['duration']:.2f}s")

        # 4. Long Context Test (Light)
        print("\nTesting Long Context (8K sequence)...")
        long_prompt = "Repeat the word 'Alice' 2000 times: " + ("Alice " * 2000)
        result_long = await send_request(client, long_prompt, max_tokens=100)
        print(f"Long Context Status: {result_long['status']}")

if __name__ == "__main__":
    asyncio.run(run_stability_test())
