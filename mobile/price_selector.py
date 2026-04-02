"""PriceSelector — ticket price and SKU selection."""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Tuple
from mobile.logger import get_logger

if TYPE_CHECKING:
    from mobile.page_probe import PageProbe

logger = get_logger(__name__)


class PriceSelector:
    def __init__(self, device, config, probe) -> None:
        self._d = device
        self._config = config
        self._probe = probe

    def select_by_index(self) -> bool:
        """Select price option by config.price_index. Returns True on success."""
        coords = self._get_price_coords_by_index()
        if coords is None:
            logger.warning(f"无法定位 price_index={self._config.price_index} 的坐标")
            return False
        self._click_coordinates(*coords)
        logger.info(f"通过配置索引选择票价: price_index={self._config.price_index}")
        return True

    def _get_price_coords_by_index(self) -> Optional[Tuple[int, int]]:
        """Stub: will be filled with extraction from damai_app.py"""
        return None

    def _click_coordinates(self, x, y) -> None:
        try:
            self._d.click(int(x), int(y))
        except Exception:
            pass
