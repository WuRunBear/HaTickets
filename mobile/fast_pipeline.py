# -*- coding: UTF-8 -*-
"""
FastPipeline — Global-deadline ticket purchase pipeline.

Replaces the cascading-timeout approach (SKU 6s + confirm 8s = 14s dead time)
with a single 5s global deadline shared across all phases.
"""

import threading
import time
import xml.etree.ElementTree as ET
from typing import Callable, List, Optional, Tuple

try:
    from mobile.logger import get_logger
except ImportError:
    from logger import get_logger

logger = get_logger(__name__)

_PIPELINE_DEADLINE_S = 5.0

# Keys that must all exist in _cached_coords for a warm run.
_WARM_REQUIRED_KEYS = frozenset({
    "detail_buy",
    "price",
    "sku_buy",
    "attendee_checkboxes",
})


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def poll_until(condition_fn: Callable[[], bool], deadline: float,
               interval_s: float = 0.05) -> bool:
    """Poll *condition_fn* until it returns True or *deadline* is exceeded.

    Returns True if the condition was met before the deadline, False otherwise.
    """
    while time.time() < deadline:
        if condition_fn():
            return True
        time.sleep(interval_s)
    return False


def batch_shell_taps(device, coordinates: List[Tuple[int, int]]) -> None:
    """Send multiple ``input tap x y`` commands in a single shell call."""
    if not coordinates:
        return
    cmd = "; ".join(f"input tap {x} {y}" for x, y in coordinates)
    device.shell(cmd)


# ---------------------------------------------------------------------------
# FastPipeline
# ---------------------------------------------------------------------------

class FastPipeline:
    """Coordinate-driven pipeline with a single global deadline."""

    def __init__(self, device, config, probe: bool, guard):
        self._device = device
        self._config = config
        self._probe = probe
        self._guard = guard

        self._cached_coords: dict = {}
        self._cached_no_match: set = set()

    # -- Public helpers -----------------------------------------------------

    def has_warm_coords(self) -> bool:
        """True when all keys required for a warm run are cached."""
        return _WARM_REQUIRED_KEYS.issubset(self._cached_coords.keys())

    # -- Warm path ----------------------------------------------------------

    def run_warm(self, start_time: float) -> Optional[bool]:
        """Execute the warm (cached-coordinate) pipeline.

        Returns True on success, None on timeout / failure.
        """
        deadline = start_time + _PIPELINE_DEADLINE_S

        # Step 1: batch city + detail_buy taps
        taps: List[Tuple[int, int]] = []
        city_coord = self._cached_coords.get("city")
        if city_coord is not None:
            taps.append(city_coord)
        detail_buy_coord = self._cached_coords.get("detail_buy")
        if detail_buy_coord is not None:
            taps.append(detail_buy_coord)
        if taps:
            batch_shell_taps(self._device, taps)

        if time.time() >= deadline:
            return None

        # Step 2: background blind clicker (price + sku_buy every 20ms)
        stop_event = threading.Event()
        price_coord = self._cached_coords.get("price")
        sku_buy_coord = self._cached_coords.get("sku_buy")

        def _blind_clicker():
            blind_taps: List[Tuple[int, int]] = []
            if price_coord is not None:
                blind_taps.append(price_coord)
            if sku_buy_coord is not None:
                blind_taps.append(sku_buy_coord)
            if not blind_taps:
                return
            while not stop_event.is_set():
                batch_shell_taps(self._device, blind_taps)
                stop_event.wait(0.02)

        clicker_thread = threading.Thread(target=_blind_clicker, daemon=True)
        clicker_thread.start()

        try:
            # Step 3: poll for attendee checkbox
            checkbox_found = poll_until(
                lambda: self._has_checkbox(),
                deadline=deadline,
            )
            if not checkbox_found:
                return None

            # Step 4: click attendee coordinates
            attendee_coord = self._cached_coords.get("attendee_checkboxes")
            if attendee_coord is not None:
                batch_shell_taps(self._device, [attendee_coord])
            return True
        finally:
            stop_event.set()
            clicker_thread.join(timeout=1.0)

    # -- Cold path ----------------------------------------------------------

    def run_cold(self, start_time: float) -> Optional[bool]:
        """Execute the cold (XML-dump) pipeline.

        Returns True on success, None on timeout / failure.
        """
        deadline = start_time + _PIPELINE_DEADLINE_S

        # Phase 1: initial XML dump
        if time.time() >= deadline:
            return None
        try:
            xml_src = self._device.dump_hierarchy()
            if xml_src:
                ET.fromstring(xml_src)
        except Exception:
            logger.debug("cold pipeline: initial XML dump failed")

        # Phase 2: poll for SKU page
        if time.time() >= deadline:
            return None
        sku_found = poll_until(
            lambda: self._has_sku_layout(),
            deadline=deadline,
        )
        if not sku_found:
            return None

        # Phase 3: SKU XML dump
        if time.time() >= deadline:
            return None
        try:
            xml_src = self._device.dump_hierarchy()
            if xml_src:
                ET.fromstring(xml_src)
        except Exception:
            logger.debug("cold pipeline: SKU XML dump failed")

        # Phase 4: poll for confirm checkbox
        if time.time() >= deadline:
            return None
        checkbox_found = poll_until(
            lambda: self._has_checkbox(),
            deadline=deadline,
        )
        if not checkbox_found:
            return None

        return True

    # -- Private helpers ----------------------------------------------------

    def _has_checkbox(self) -> bool:
        """Check for attendee checkbox via u2 element lookup."""
        try:
            el = self._device(resourceId="cn.damai:id/checkbox")
            return el.exists
        except Exception:
            return False

    def _has_sku_layout(self) -> bool:
        """Check for SKU layout via u2 element lookup."""
        try:
            el = self._device(resourceId="cn.damai:id/layout_sku")
            return el.exists
        except Exception:
            return False
