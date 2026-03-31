# 2026-04-01 u2 Migration Failures

## Context

- Branch: `feature/u2-migration-20260331`
- Command:
  - `poetry run pytest tests/unit/test_mobile_config.py tests/unit/test_mobile_damai_app.py -q`

## Failures Captured

1. `tests/unit/test_mobile_config.py::TestMobileConfigInit::test_config_init_stores_all_attributes`
   - Assertion mismatch:
   - expected `cfg.driver_backend == "appium"`
   - actual `cfg.driver_backend == "u2"`

2. Multiple `tests/unit/test_mobile_damai_app.py::TestRunTicketGrabbing::*` failures
   - Runtime error:
   - `抢票过程发生错误: 'Mock' object is not iterable`

3. `tests/unit/test_mobile_damai_app.py::TestSkuInspectionHelpers::test_get_visible_price_options_returns_empty_when_cards_are_not_a_sequence`
   - TypeError:
   - `'Mock' object is not iterable`

## Initial Root Cause Analysis

- New container/query adapters assume iterables in several paths.
- Existing tests intentionally return `Mock()` (non-iterable) for some container APIs; old code tolerated this.
- One config assertion was not updated for new default backend behavior.

## Resolution Plan

1. Update config test expectation to default `u2`.
2. Harden adapter methods to gracefully handle non-list/non-tuple/non-iterable mocks.
3. Restore Appium fallback behavior in price-selection backup path (`self.wait.until`) to keep old tests and behavior stable.
4. Re-run focused tests and then full test suite.

## Additional Failures (2nd Round)

- Command:
  - `poetry run pytest tests/unit tests/integration -q -o addopts=''`

1. `tests/unit/test_mobile_hot_path_benchmark.py` (5 failures)
   - `_fast_check_detail_page` switched to `bot._find_all(...)`, while test helper only mocked `bot.driver.find_elements`.
   - Result: fast-check no longer bypassed in tests, causing assertion mismatches.

2. `tests/integration/test_mobile_workflow.py::TestConfigToBotInit::test_load_config_to_bot_init`
   - Config JSON omitted `driver_backend`, defaulting to `u2` and hitting mocked `uiautomator2.connect`.
   - Mock settings object did not support dict assignment.

## Additional Fixes Applied

1. `_fast_check_detail_page` now:
   - supports both `bot._find_all(...)` and legacy `bot.driver.find_elements(...)`,
   - and safely returns `None` when result is non-iterable.
2. Integration fixture/config updated to set `driver_backend="appium"` where test intends Appium path.
3. `_setup_u2_driver()` made tolerant to non-mapping `settings` objects in mocked environments.
4. Added dedicated adapter coverage tests in:
   - `tests/unit/test_mobile_damai_app_u2_adapter.py`

## Tooling Error (3rd Round)

- Command:
  - `poetry lock --no-update`
- Error:
  - `The option "--no-update" does not exist`
- Root Cause:
  - Local Poetry version does not support this flag.
- Resolution:
  - Use compatible command `poetry lock` to regenerate lock file.

## Final Verification

- `poetry run pytest tests/unit/test_mobile_config.py tests/unit/test_mobile_damai_app.py -q -o addopts=''`
  - `255 passed`
- `poetry run pytest tests/unit/test_mobile_hot_path_benchmark.py tests/integration/test_mobile_workflow.py -q -o addopts=''`
  - `44 passed`
- `poetry run pytest -q -o addopts=''`
  - `897 passed`
- `poetry lock`
  - success, lock file written
- `poetry run pytest`
  - `897 passed`
  - coverage `80.21%` (threshold `>=80%` satisfied)
