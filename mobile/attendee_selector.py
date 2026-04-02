"""AttendeeSelector — confirm page attendee checkbox automation."""
from __future__ import annotations
from typing import List
from mobile.logger import get_logger

logger = get_logger(__name__)
_CHECKBOX_ID = "cn.damai:id/checkbox"


class AttendeeSelector:
    def __init__(self, device, config) -> None:
        self._d = device
        self._config = config

    def ensure_selected(self) -> None:
        """Ensure the correct number of attendees are checked."""
        required = max(1, len(self._config.users or []))
        checkboxes = self._find_checkboxes()
        if not checkboxes:
            logger.warning("未找到观演人勾选框")
            return
        for cb in checkboxes[:required]:
            self._click_checkbox(cb)
        logger.info(f"已勾选 {min(required, len(checkboxes))}/{required} 位观演人")

    def _find_checkboxes(self) -> List:
        try:
            elements = self._d(resourceId=_CHECKBOX_ID)
            return list(elements) if elements.exists else []
        except Exception:
            return []

    def _click_checkbox(self, element) -> None:
        try:
            element.click()
        except Exception:
            pass
