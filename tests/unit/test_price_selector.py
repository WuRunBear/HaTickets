"""Unit tests for PriceSelector."""
from unittest.mock import MagicMock
import pytest
from mobile.price_selector import PriceSelector


class TestSelectByIndex:
    def test_clicks_correct_coordinates(self):
        d = MagicMock()
        config = MagicMock()
        config.price_index = 2
        probe = MagicMock()
        selector = PriceSelector(device=d, config=config, probe=probe)
        selector._get_price_coords_by_index = MagicMock(return_value=(100, 200))
        selector._click_coordinates = MagicMock()
        result = selector.select_by_index()
        selector._click_coordinates.assert_called_once_with(100, 200)
        assert result is True

    def test_returns_false_when_no_coords(self):
        d = MagicMock()
        config = MagicMock()
        config.price_index = 99
        probe = MagicMock()
        selector = PriceSelector(device=d, config=config, probe=probe)
        selector._get_price_coords_by_index = MagicMock(return_value=None)
        result = selector.select_by_index()
        assert result is False
