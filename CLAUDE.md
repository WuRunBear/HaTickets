# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Damai.com (大麦网) ticket purchasing automation system with three platform modules:
- **Web** (`damai/`): Selenium + ChromeDriver browser automation (Python)
- **Mobile** (`damai_appium/`): Appium + UIAutomator2 Android app automation (Python)
- **Desktop** (`src/` + `src-tauri/`): Tauri v1 desktop app — Vue 3 frontend + Rust backend calling Damai's mtop API directly

Web and Mobile follow the same flow: config → driver init → navigation → ticket selection → order submission. Desktop bypasses the browser entirely, making HTTP requests to Damai's API from the Rust backend via Tauri commands.

Performance is critical — this is competitive ticket-grabbing where milliseconds matter.

## Commands

```bash
# === Python (Web & Mobile modules) ===
poetry install
poetry run test                              # run all tests (coverage auto-enabled)
poetry run pytest tests/test_setup_validation.py   # single file
poetry run pytest -k "test_name"             # single test
poetry run pytest -m unit                    # by marker (unit | integration | slow)

# Environment check (Web)
./check_environment.sh

# Mobile: start Appium then run
./start_appium.sh
./start_ticket_grabbing.sh

# === Desktop (Tauri app) ===
yarn install                  # install frontend deps
yarn tauri dev                # dev mode (Vite on :1420 + Tauri window)
yarn tauri build              # production build
cargo test --manifest-path src-tauri/Cargo.toml   # Rust tests
```

## Architecture

### Web (`damai/`)
- `damai.py` — Entry point: validates config, loads `Config`, orchestrates `Concert`
- `concert.py` — Core automation: Selenium WebDriver lifecycle, cookie-based auth, ticket selection polling loop, order submission. Uses `self.status` state machine (0=init, 2=logged in, 3=selecting)
- `config.py` — Config container (URL, users, city, dates, prices, retry count, fast_mode, page_load_delay)

### Mobile (`damai_appium/`)
- `damai_app_v2.py` — Current impl: `DamaiBot` with coordinate-based gesture clicks (faster than element.click()), aggressive timeout tuning, batch coordinate collection
- `damai_app.py` — Legacy version (deprecated)
- `config.py` — Mobile config via `load_config()` reading `config.jsonc`

### Desktop (`src/` + `src-tauri/`)
- **Frontend** (`src/`): Vue 3 + Vuex + Vue Router + Arco Design UI
  - Views: `dm.vue` (ticket operations), `my.vue` (account/settings)
  - Components: `dm/` (Form, Product, VisitUser), `my/` (Form), `common/` (Header, Proxy, Qa, Tip, Update)
  - `sql/` — SQLite schema/queries (via `tauri-plugin-sql`)
- **Backend** (`src-tauri/src/`): Rust + reqwest calling Damai's mtop API
  - `main.rs` — Tauri commands: `get_product_info`, `get_ticket_list`, `get_ticket_detail`, `create_order`, `get_user_list`, `export_sql_to_txt`
  - `proxy_builder.rs` — HTTP/SOCKS proxy support for all API requests
  - `utils.rs` — SQLite export utility
  - All API requests use 3s timeout, spoofed mobile Chrome UA, and anti-crawl headers

### Configuration
- Web: `damai/config.json`
- Mobile: `damai_appium/config.jsonc`
- Desktop: SQLite database (managed via Tauri plugin)

### Tests (`tests/`)
- `conftest.py` — Shared fixtures: `mock_config`, `mock_selenium_driver`, `mock_appium_driver`, `sample_html_response`, `mock_time`, `temp_dir`
- Custom markers auto-applied by file location (unit/integration)
- Coverage threshold: 80% (enforced in pyproject.toml)

### CI/CD
- `.github/workflows/release.yml` — Tag-triggered (`v*`) cross-platform Tauri build (macOS/Linux/Windows) with GitHub Release upload

## Key Design Decisions
- Desktop module calls Damai's mtop API directly from Rust (no browser overhead) — the fastest path
- Mobile v2 uses coordinate-based gesture clicks over element.click() for speed
- Proxy support is first-class in the Desktop module (`ProxyBuilder` wraps reqwest with HTTP/SOCKS proxy)
- ChromeDriver auto-detection and auto-installation to prevent version mismatch (Web)
- Cookie persistence for Web login to avoid repeated manual auth
- `fast_mode` config flag reduces polling intervals in Web module
