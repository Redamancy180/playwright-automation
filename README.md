# Playwright Automation

Python Playwright automation helpers packaged for team reuse, versioning, and later GitHub maintenance.

## Project Structure

```text
playwright-automation/
├─ src/pw_automation/
│  ├─ browser.py
│  ├─ config.py
│  └─ runner.py
├─ scripts/
├─ tests/
├─ .github/workflows/
├─ .env.example
├─ pyproject.toml
├─ requirements.txt
└─ requirements-dev.txt
```

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements-dev.txt`.
3. Install browser binaries with `playwright install chromium`.
4. Copy `.env.example` to `.env` and adjust paths if needed.
5. Run `python scripts/run_demo.py --url https://example.com`.

## Environment Variables

- `PW_DEBUG_PORT`: Chrome remote debugging port
- `PW_USER_DATA_DIR`: Chrome user data directory
- `PW_CHROME_PATH`: Local Chrome executable path
- `PW_DEFAULT_TIMEOUT_MS`: Default Playwright timeout in milliseconds
- `PW_KEEP_BROWSER_OPEN_ON_ERROR`: Whether to keep the browser open on failure

## Next Step

When you are ready, initialize Git in this folder and create the GitHub repository against this local project root.
