import requests
import json
import time
import asyncio
import aiohttp
import os

OLLAMA_URL = "http://127.0.0.1:11466/api/chat"
MODEL = "qwen3.5:35b"

async def send_request(session, prompt, request_id):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    print(f"[Req {request_id}] Sending payload...")
    start_time = time.time()
    try:
        async with session.post(OLLAMA_URL, json=payload, timeout=300) as response:
            result = await response.json()
            duration = time.time() - start_time
            print(f"[Req {request_id}] Completed in {duration:.2f}s")
            return result
    except Exception as e:
        print(f"[Req {request_id}] Failed: {e}")
        return None

async def run_stress_test():
    prompts = [
        "Find all .md files in /home/mr-snow/alice_cyberland and list their names.",
        "Calculate the sum of all prime numbers between 1 and 1000.",
        "Write a bash script to monitor GPU usage every second and save it to 'gpu_log.txt'.",
        "What is the current stock price of NVIDIA?",
        "Explain the difference between a process and a thread in Linux."
    ]
    
    print(f"--- Starting Stress Test on {MODEL} ---")
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i, p in enumerate(prompts):
            tasks.append(send_request(session, p, i))
        
        results = await asyncio.gather(*tasks)
    
    print("--- Stress Test Finished ---")
    success_count = sum(1 for r in results if r is not None)
    print(f"Total Success: {success_count}/{len(prompts)}")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
