#!/home/mr-snow/alice_cyberland/venv_stable/bin/python3
import sys
import json
import argparse
import asyncio
from playwright.async_api import async_playwright

SCHEMA = {
    "name": "browser",
    "description": "Headless browser for web scraping and navigation. Use to search or read live websites.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "extract", "screenshot"],
                "description": "Action to perform."
            },
            "url": {
                "type": "string",
                "description": "The URL to visit."
            }
        },
        "required": ["action", "url"]
    }
}

async def run_browser(action, url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=30000)
            if action == "navigate":
                title = await page.title()
                return f"Successfully navigated to {url}. Page title: {title}"
            elif action == "extract":
                content = await page.inner_text("body")
                return content[:5000]
            elif action == "screenshot":
                return "Screenshot capability detected (implementation pending image return path)."
        except Exception as e:
            return f"Browser error: {e}"
        finally:
            await browser.close()

if __name__ == "__main__":
    if "--schema" in sys.argv:
        print(json.dumps(SCHEMA))
        sys.exit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--url", required=True)
    args = parser.parse_args()

    result = asyncio.run(run_browser(args.action, args.url))
    print(result)
