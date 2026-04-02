# -*- coding: UTF-8 -*-
"""Tests for mobile.fast_pipeline module."""

import threading
import time
from unittest.mock import Mock, MagicMock, patch, call

import pytest

from mobile.fast_pipeline import (
    FastPipeline,
    batch_shell_taps,
    poll_until,
    _PIPELINE_DEADLINE_S,
    _WARM_REQUIRED_KEYS,
)


# ---------------------------------------------------------------------------
# poll_until
# ---------------------------------------------------------------------------

class TestPollUntil:
    """Tests for the generic poll_until utility."""

    def test_returns_true_when_condition_met_immediately(self):
        deadline = time.time() + 5.0
        result = poll_until(lambda: True, deadline=deadline)
        assert result is True

    def test_returns_false_on_timeout(self):
        deadline = time.time() + 0.1
        result = poll_until(lambda: False, deadline=deadline, interval_s=0.02)
        assert result is False

    def test_respects_deadline_timing(self):
        """Elapsed time should be close to the deadline window, not much longer."""
        timeout = 0.2
        start = time.time()
        deadline = start + timeout
        result = poll_until(lambda: False, deadline=deadline, interval_s=0.02)
        elapsed = time.time() - start
        assert result is False
        # Should finish within timeout + a small margin (one extra sleep cycle)
        assert elapsed < timeout + 0.1

    def test_returns_true_after_several_polls(self):
        counter = {"n": 0}

        def condition():
            counter["n"] += 1
            return counter["n"] >= 3

        deadline = time.time() + 5.0
        result = poll_until(condition, deadline=deadline, interval_s=0.01)
        assert result is True
        assert counter["n"] >= 3


# ---------------------------------------------------------------------------
# batch_shell_taps
# ---------------------------------------------------------------------------

class TestBatchShellTaps:

    def test_sends_semicolon_joined_commands(self):
        device = Mock()
        batch_shell_taps(device, [(100, 200), (300, 400)])
        device.shell.assert_called_once_with(
            "input tap 100 200; input tap 300 400"
        )

    def test_noop_on_empty_list(self):
        device = Mock()
        batch_shell_taps(device, [])
        device.shell.assert_not_called()

    def test_single_coordinate(self):
        device = Mock()
        batch_shell_taps(device, [(50, 60)])
        device.shell.assert_called_once_with("input tap 50 60")


# ---------------------------------------------------------------------------
# FastPipeline.has_warm_coords
# ---------------------------------------------------------------------------

class TestHasWarmCoords:

    def _make_pipeline(self, coords=None):
        device = Mock()
        config = Mock()
        fp = FastPipeline(device, config, probe=False, guard=Mock())
        if coords:
            fp._cached_coords = coords
        return fp

    def test_true_with_all_keys(self):
        coords = {k: (100, 200) for k in _WARM_REQUIRED_KEYS}
        fp = self._make_pipeline(coords)
        assert fp.has_warm_coords() is True

    def test_true_with_extra_keys(self):
        coords = {k: (100, 200) for k in _WARM_REQUIRED_KEYS}
        coords["city"] = (50, 50)
        fp = self._make_pipeline(coords)
        assert fp.has_warm_coords() is True

    def test_false_with_missing_key(self):
        coords = {k: (100, 200) for k in list(_WARM_REQUIRED_KEYS)[:-1]}
        fp = self._make_pipeline(coords)
        assert fp.has_warm_coords() is False

    def test_false_when_empty(self):
        fp = self._make_pipeline()
        assert fp.has_warm_coords() is False


# ---------------------------------------------------------------------------
# FastPipeline.run_cold — deadline enforcement
# ---------------------------------------------------------------------------

class TestRunColdDeadline:

    def test_respects_5s_deadline_on_full_timeout(self):
        """When everything times out, run_cold must return within ~5s + margin."""
        device = Mock()
        # dump_hierarchy returns empty so XML parsing is skipped
        device.dump_hierarchy.return_value = ""
        # Element lookups always fail → poll_until loops until deadline
        mock_element = Mock()
        mock_element.exists = False
        device.return_value = mock_element

        config = Mock()
        fp = FastPipeline(device, config, probe=False, guard=Mock())

        start = time.time()
        result = fp.run_cold(start)
        elapsed = time.time() - start

        assert result is None
        # Must finish within the 5s deadline + a small margin
        assert elapsed < _PIPELINE_DEADLINE_S + 1.0


# ---------------------------------------------------------------------------
# FastPipeline.run_warm — fast completion
# ---------------------------------------------------------------------------

class TestRunWarmFast:

    def test_completes_fast_with_cached_coords(self):
        """With cached coords and immediate checkbox detection, should be very fast."""
        device = Mock()
        # checkbox detection succeeds immediately
        mock_element = Mock()
        mock_element.exists = True
        device.return_value = mock_element

        config = Mock()
        fp = FastPipeline(device, config, probe=False, guard=Mock())
        fp._cached_coords = {
            "detail_buy": (540, 1700),
            "price": (200, 800),
            "sku_buy": (540, 1600),
            "attendee_checkboxes": (100, 500),
            "city": (300, 400),
        }

        start = time.time()
        result = fp.run_warm(start)
        elapsed = time.time() - start

        assert result is True
        # Should complete well under 1s
        assert elapsed < 1.0

    def test_returns_none_when_checkbox_not_found(self):
        """Warm path returns None when checkbox never appears."""
        device = Mock()
        mock_element = Mock()
        mock_element.exists = False
        device.return_value = mock_element

        config = Mock()
        fp = FastPipeline(device, config, probe=False, guard=Mock())
        fp._cached_coords = {
            "detail_buy": (540, 1700),
            "price": (200, 800),
            "sku_buy": (540, 1600),
            "attendee_checkboxes": (100, 500),
        }

        # Use a very short deadline to keep the test fast
        start = time.time()
        result = fp.run_warm(start - _PIPELINE_DEADLINE_S + 0.15)
        elapsed = time.time() - start

        assert result is None
        assert elapsed < 1.0

    def test_warm_calls_batch_shell_taps(self):
        """Verify that batch taps are sent for city + detail_buy."""
        device = Mock()
        mock_element = Mock()
        mock_element.exists = True
        device.return_value = mock_element

        config = Mock()
        fp = FastPipeline(device, config, probe=False, guard=Mock())
        fp._cached_coords = {
            "detail_buy": (540, 1700),
            "price": (200, 800),
            "sku_buy": (540, 1600),
            "attendee_checkboxes": (100, 500),
            "city": (300, 400),
        }

        result = fp.run_warm(time.time())
        assert result is True

        # The first shell call should be the city+detail_buy batch
        first_call_args = device.shell.call_args_list[0][0][0]
        assert "input tap 300 400" in first_call_args
        assert "input tap 540 1700" in first_call_args
