---
name: browser
description: Headless browser for web scraping and navigation. Use to search or read live websites.
metadata:
  {
    "openclaw":
      {
        "emoji": "🌐",
        "requires": { "bins": ["python3"] },
      },
  }
---

# Browser Skill

Use this skill to navigate to websites and extract content using a headless browser.

## Commands

- `browser --action navigate --url "https://example.com"`
- `browser --action extract --url "https://example.com"`

## Notes

- Powered by Playwright.
- Runs in headless mode.
