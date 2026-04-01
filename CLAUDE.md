# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Damai.com (大麦网) ticket purchasing automation system with three platform modules:
- **Mobile** (`mobile/`): **Primary/recommended** — UIAutomator2 (u2) 直连 Android 设备（默认），Appium 作为可选回退后端（Python）
- **Web** (`web/`): Selenium + ChromeDriver browser automation (Python) — secondary option
- **Desktop** (`desktop/`): Tauri v1 desktop app — **deprecated, blocked by official channel restrictions, do not invest time here**

Mobile and Web follow the same flow: config → driver init → navigation → ticket selection → order submission. Desktop called Damai's mtop API directly from Rust but is no longer viable.

Performance is critical — this is competitive ticket-grabbing where milliseconds matter.

## Prerequisites

- **Python**: ^3.8 + Poetry
- **Web**: Chrome browser (ChromeDriver auto-installed by `web/check_environment.py`)
- **Mobile (u2, default)**: Android device/emulator + adb（无需额外服务进程）
- **Mobile (appium fallback)**: 上述 + Appium 3.1+ + Node.js 20.19+（仅 `driver_backend="appium"` 时需要）
- **Desktop**: Node.js 20+ + Rust toolchain + Yarn (deprecated — see above)

## Commands

```bash
# === Python (Web & Mobile modules) ===
poetry install
poetry run test                              # run all tests (coverage auto-enabled, 80% threshold)
poetry run pytest tests/unit/test_mobile_damai_app.py  # single file
poetry run pytest -k "test_name"             # single test
poetry run pytest -m unit                    # by marker (unit | integration | slow)

# Mobile scripts
mobile/scripts/start_appium.sh               # (optional) start Appium server, only needed if driver_backend="appium"
mobile/scripts/start_ticket_grabbing.sh --probe --yes   # safe probe run
mobile/scripts/start_ticket_grabbing.sh --yes           # live ticket grabbing
mobile/scripts/run_from_prompt.sh --mode summary --yes "prompt text"  # NLP config: preview
mobile/scripts/run_from_prompt.sh --mode apply --yes "prompt text"    # NLP config: write config
mobile/scripts/run_from_prompt.sh --mode probe --yes "prompt text"    # NLP config: write + probe
mobile/scripts/benchmark_hot_path.sh          # hot path performance benchmark

# Environment check (Web)
web/scripts/check_environment.sh

# === Desktop (Tauri app — deprecated) ===
cd desktop && yarn install && yarn tauri dev
cargo test --manifest-path desktop/src-tauri/Cargo.toml
```

## Architecture

### Mobile (`mobile/`) — Primary Module

- `damai_app.py` — `DamaiBot`: supports two driver backends (`u2` default and `appium` fallback). u2 直连设备每次操作 ~30-60ms（Appium 需 ~100-200ms）。Uses coordinate-based gesture clicks, hot-path coordinate caching, aggressive timeout tuning
- `config.py` — Mobile config via `Config.load_config()` reading `config.jsonc`. `driver_backend` field defaults to `"u2"`; set to `"appium"` to use legacy Appium backend
- `item_resolver.py` — Fetches event metadata (name, venue, dates, prices) from item URLs via Damai mobile API
- `prompt_parser.py` — Parses natural-language prompts into structured intent (quantity, date, city, price) with scoring
- `prompt_runner.py` — CLI entrypoint for natural-language ticket discovery and bot invocation
- `hot_path_benchmark.py` — Performance benchmarking for the ticket-grabbing hot path
- `logger.py` — Unified logging (Shanghai timezone, console INFO+ / file DEBUG+)

### Web (`web/`)
- `damai.py` — Entry point: validates config, loads `Config`, orchestrates `Concert`
- `concert.py` — Core automation: Selenium WebDriver lifecycle, multi-session festival support, ticket selection polling loop. Uses `self.status` state machine (0=init, 2=logged in, 3=selecting)
- `config.py` — Config container (URL, users, city, dates, prices, retry count, fast_mode, page_load_delay)
- `session_manager.py` — Cookie-based auth persistence with 24-hour expiry checks
- `ticket_selector.py` — Selects dates/prices/cities/quantities using fuzzy matching and multiple fallback strategies (PC + mobile layouts)
- `user_selector.py` — Selects attendees on order page via four cascading methods (div, checkbox, click, JS)
- `order_submitter.py` — Finds and clicks submit button with text/attribute/CSS/XPath fallbacks
- `check_environment.py` — ChromeDriver auto-detection/installation; called automatically by `Concert.__init__`

### Shared (`shared/`)
- `config_validator.py` — Validates URL format, non-empty lists, positive integers (used by both web and mobile)
- `xpath_utils.py` — XPath string literal escaping via `concat()` to handle single/double quotes

### Desktop (`desktop/`) — Deprecated
- Frontend: Vue 3 + Vuex + Vue Router + Arco Design UI (Vite)
- Backend: Rust + reqwest (Tauri 1.3) calling Damai's mtop API
- All API requests use 3s timeout, spoofed mobile Chrome UA, and anti-crawl headers

### Configuration
- Web: `web/config.json`
- Mobile: `mobile/config.jsonc` (with optional `mobile/config.local.jsonc` for dev overrides via `--config` flag or `HATICKETS_CONFIG_PATH` env var)
- Desktop: SQLite database (managed via Tauri plugin)

### Tests (`tests/`)
- `conftest.py` — Shared fixtures and **module-level mocks for appium and uiautomator2** (injected into `sys.modules` so tests run without real device dependencies)
- Custom markers auto-applied by file path: files under `unit/` get `@pytest.mark.unit`, under `integration/` get `@pytest.mark.integration`
- Coverage: 80% threshold enforced, covers `web/` and `mobile/` only

### Import Convention (Important)
- **Web modules** use bare imports (`from config import Config`, `from concert import Concert`) — `web/` is added to `sys.path` in conftest
- **Mobile modules** use package-qualified imports (`from mobile.config import Config`, `mobile.damai_app`) — `mobile/` is NOT added to sys.path to avoid `Config` name clash

### CI/CD
- `.github/workflows/release.yml` — Tag-triggered (`v*`) cross-platform Tauri build (macOS/Linux/Windows) with GitHub Release upload

## Key Design Decisions
- Mobile is the primary approach; Desktop is deprecated due to official channel restrictions
- Mobile defaults to UIAutomator2 (u2) direct connection — no Appium server needed, ~3x faster per operation; Appium available as fallback via `driver_backend: "appium"`
- Mobile uses coordinate-based gesture clicks over element.click() for speed
- ChromeDriver auto-detection and auto-installation to prevent version mismatch (Web)
- Cookie persistence for Web login to avoid repeated manual auth
- `fast_mode` config flag reduces polling intervals in Web module
- Proxy support is first-class in the Desktop module (`ProxyBuilder` wraps reqwest with HTTP/SOCKS proxy)
