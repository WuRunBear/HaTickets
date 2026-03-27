# -*- coding: UTF-8 -*-
"""Unit tests for web/ticket_selector.py."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException,
)
from selenium.webdriver.common.by import By

from config import Config
from ticket_selector import TicketSelector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides):
    defaults = dict(
        index_url="https://www.damai.cn/",
        login_url="https://passport.damai.cn/login",
        target_url="https://detail.damai.cn/item.htm?id=123",
        users=["UserA", "UserB"],
        city="杭州",
        dates=["2026-04-11"],
        prices=["680"],
        if_listen=True,
        if_commit_order=True,
        max_retries=3,
        fast_mode=True,
        page_load_delay=0.1,
    )
    defaults.update(overrides)
    return Config(**defaults)


def _make_selector(fast_mode=True, **config_overrides):
    """Build a TicketSelector with a fresh mock driver."""
    config = _make_config(fast_mode=fast_mode, **config_overrides)
    driver = Mock()
    driver.find_element = Mock()
    driver.find_elements = Mock(return_value=[])
    driver.execute_script = Mock()
    return TicketSelector(driver, config), driver, config


def _mock_elem(text="", displayed=True, enabled=True, class_attr=""):
    elem = Mock()
    elem.text = text
    elem.is_displayed = Mock(return_value=displayed)
    elem.is_enabled = Mock(return_value=enabled)
    elem.get_attribute = Mock(return_value=class_attr)
    elem.click = Mock()
    parent = Mock()
    parent.click = Mock()
    elem.find_element = Mock(return_value=parent)
    return elem


# ===========================================================================
# select_option_by_config
# ===========================================================================

class TestSelectOptionByConfig:

    def test_returns_false_when_config_list_empty(self):
        sel, driver, _ = _make_selector()
        assert sel.select_option_by_config([], [_mock_elem("680元")]) is False

    def test_returns_false_when_element_list_empty(self):
        sel, driver, _ = _make_selector()
        assert sel.select_option_by_config(["680"], []) is False

    def test_clicks_matching_element_and_returns_true(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("680元")
        result = sel.select_option_by_config(["680"], [elem])
        assert result is True
        elem.click.assert_called_once()

    def test_skips_sold_out_element(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("680元 无票")
        result = sel.select_option_by_config(["680"], [elem])
        assert result is False
        elem.click.assert_not_called()

    def test_skips_shortage_element(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("680元 缺货")
        result = sel.select_option_by_config(["680"], [elem])
        assert result is False

    def test_custom_skip_keywords(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("680元 待定")
        result = sel.select_option_by_config(["680"], [elem], skip_keywords=["待定"])
        assert result is False

    def test_stale_element_reference_is_skipped(self):
        sel, driver, _ = _make_selector()
        bad_elem = Mock()
        bad_elem.text = "680元"
        bad_elem.click = Mock(side_effect=StaleElementReferenceException())
        good_elem = _mock_elem("680元")
        result = sel.select_option_by_config(["680"], [bad_elem, good_elem])
        assert result is True

    def test_element_click_intercepted_is_skipped(self):
        sel, driver, _ = _make_selector()
        bad_elem = Mock()
        bad_elem.text = "680元"
        bad_elem.click = Mock(side_effect=ElementClickInterceptedException())
        result = sel.select_option_by_config(["680"], [bad_elem])
        assert result is False

    def test_stale_element_text_access_is_skipped(self):
        sel, driver, _ = _make_selector()
        bad_elem = Mock()
        type(bad_elem).text = property(lambda self: (_ for _ in ()).throw(StaleElementReferenceException()))
        good_elem = _mock_elem("680元")
        result = sel.select_option_by_config(["680"], [bad_elem, good_elem])
        assert result is True

    def test_first_config_value_match_wins(self):
        """First matching config value should be selected, not the second."""
        sel, driver, _ = _make_selector()
        elem_a = _mock_elem("280元")
        elem_b = _mock_elem("680元")
        result = sel.select_option_by_config(["680", "280"], [elem_a, elem_b])
        # 680 appears in elem_b, should click that
        assert result is True
        elem_b.click.assert_called_once()
        elem_a.click.assert_not_called()

    def test_no_match_returns_false(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("380元")
        result = sel.select_option_by_config(["680"], [elem])
        assert result is False


# ===========================================================================
# find_and_click_element
# ===========================================================================

class TestFindAndClickElement:

    def test_returns_false_when_no_elements_found(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        result = sel.find_and_click_element("680")
        assert result is False

    def test_clicks_element_and_returns_true(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("680元")
        driver.find_elements.return_value = [elem]
        result = sel.find_and_click_element("680")
        assert result is True
        elem.click.assert_called_once()

    def test_skips_elements_with_skip_keywords(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("680元 售罄")
        driver.find_elements.return_value = [elem]
        result = sel.find_and_click_element("680", skip_keywords=["售罄"])
        assert result is False
        elem.click.assert_not_called()

    def test_skips_empty_text_elements(self):
        sel, driver, _ = _make_selector()
        empty_elem = _mock_elem("")
        good_elem = _mock_elem("680元")
        driver.find_elements.return_value = [empty_elem, good_elem]
        result = sel.find_and_click_element("680")
        assert result is True

    def test_falls_back_to_parent_element_click(self):
        """If the element click fails, should try clicking the parent."""
        sel, driver, _ = _make_selector()
        elem = _mock_elem("680元")
        elem.click = Mock(side_effect=ElementClickInterceptedException())
        parent = Mock()
        parent.click = Mock()
        elem.find_element = Mock(return_value=parent)
        driver.find_elements.return_value = [elem]
        result = sel.find_and_click_element("680")
        assert result is True
        parent.click.assert_called_once()

    def test_stale_element_is_skipped(self):
        sel, driver, _ = _make_selector()
        stale = Mock()
        type(stale).text = property(lambda self: (_ for _ in ()).throw(StaleElementReferenceException()))
        driver.find_elements.return_value = [stale]
        result = sel.find_and_click_element("680")
        assert result is False

    def test_max_results_limits_elements_tried(self):
        sel, driver, _ = _make_selector()
        # XPath would return elements containing '680'; mock simulates that.
        # Make all of them unclickable so we can verify the max_results cutoff.
        elems = [_mock_elem(f"680元-{i}") for i in range(20)]
        for elem in elems:
            elem.click = Mock(side_effect=WebDriverException("intercepted"))
            elem.find_element = Mock(side_effect=NoSuchElementException())
        driver.find_elements.return_value = elems
        result = sel.find_and_click_element("680", max_results=5)
        assert result is False
        # Elements beyond max_results should never be attempted
        for elem in elems[5:]:
            elem.click.assert_not_called()

    def test_print_results_false_suppresses_output(self, capsys):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        sel.find_and_click_element("680", print_results=False)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_webdriver_exception_from_find_elements_handled(self):
        sel, driver, _ = _make_selector()
        elem = Mock()
        elem.text = "680元"
        elem.click = Mock(side_effect=WebDriverException("fail"))
        elem.find_element = Mock(side_effect=WebDriverException("fail"))
        driver.find_elements.return_value = [elem]
        result = sel.find_and_click_element("680")
        assert result is False


# ===========================================================================
# click_element_by_text
# ===========================================================================

class TestClickElementByText:

    def test_clicks_matching_element_returns_true(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("下一步")
        driver.find_elements.return_value = [elem]
        result = sel.click_element_by_text("下一步")
        assert result is True

    def test_returns_false_when_no_match(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        result = sel.click_element_by_text("下一步")
        assert result is False

    def test_exact_match_mode(self):
        sel, driver, _ = _make_selector()
        elem_exact = _mock_elem("下一步")
        driver.find_elements.return_value = [elem_exact]
        result = sel.click_element_by_text("下一步", exact_match=True)
        assert result is True

    def test_exact_match_rejects_partial(self):
        sel, driver, _ = _make_selector()
        # Element text is "下一步 (1)" — doesn't exactly equal "下一步"
        elem = _mock_elem("下一步 (1)")
        driver.find_elements.return_value = [elem]
        result = sel.click_element_by_text("下一步", exact_match=True)
        assert result is False

    def test_custom_tag_names(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("购买")
        driver.find_elements.return_value = [elem]
        result = sel.click_element_by_text("购买", tag_names=["a"])
        assert result is True

    def test_webdriver_exception_on_find_continues(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.side_effect = WebDriverException("boom")
        result = sel.click_element_by_text("购买")
        assert result is False


# ===========================================================================
# select_city_on_page_pc
# ===========================================================================

class TestSelectCityOnPagePc:

    def test_clicks_matching_city_element(self):
        sel, driver, _ = _make_selector()
        city_elem = _mock_elem("杭州")
        container = Mock()
        container.find_elements = Mock(return_value=[city_elem])
        # First find_elements (class check) returns truthy, find_element returns container
        driver.find_elements.return_value = [Mock()]
        driver.find_element = Mock(return_value=container)
        result = sel.select_city_on_page_pc()
        assert result is True
        city_elem.click.assert_called_once()

    def test_no_tour_container_falls_back_to_text_search(self):
        sel, driver, _ = _make_selector()
        # No 'bui-dm-tour' class found
        driver.find_elements.return_value = []
        with patch.object(sel, "find_and_click_element", return_value=True) as mock_find:
            result = sel.select_city_on_page_pc()
        assert result is True
        mock_find.assert_called_once_with("杭州", max_results=10, print_results=False)

    def test_city_not_in_tour_falls_back_to_text_search(self):
        sel, driver, _ = _make_selector()
        city_elem = _mock_elem("上海")  # doesn't match "杭州"
        container = Mock()
        container.find_elements = Mock(return_value=[city_elem])
        driver.find_elements.return_value = [Mock()]
        driver.find_element = Mock(return_value=container)
        with patch.object(sel, "find_and_click_element", return_value=True) as mock_find:
            result = sel.select_city_on_page_pc()
        assert result is True
        mock_find.assert_called_once()

    def test_stale_element_reference_in_city_list_skipped(self):
        sel, driver, _ = _make_selector()
        stale_elem = Mock()
        stale_elem.text = "杭州"
        stale_elem.click = Mock(side_effect=StaleElementReferenceException())
        good_elem = _mock_elem("杭州")
        container = Mock()
        container.find_elements = Mock(return_value=[stale_elem, good_elem])
        driver.find_elements.return_value = [Mock()]
        driver.find_element = Mock(return_value=container)
        result = sel.select_city_on_page_pc()
        assert result is True
        good_elem.click.assert_called_once()

    def test_exception_returns_false(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.side_effect = WebDriverException("error")
        result = sel.select_city_on_page_pc()
        assert result is False

    def test_non_fast_mode_prints_city_list(self, capsys):
        sel, driver, _ = _make_selector(fast_mode=False)
        city_elem = _mock_elem("杭州")
        container = Mock()
        container.find_elements = Mock(return_value=[city_elem])
        driver.find_elements.return_value = [Mock()]
        driver.find_element = Mock(return_value=container)
        sel.select_city_on_page_pc()
        captured = capsys.readouterr()
        assert "杭州" in captured.out


# ===========================================================================
# select_date_on_page_pc
# ===========================================================================

class TestSelectDateOnPagePc:

    def test_clicks_matching_date_element(self):
        sel, driver, _ = _make_selector()
        date_elem = _mock_elem("2026-04-11")
        container = Mock()
        container.find_elements = Mock(return_value=[date_elem])
        driver.find_elements.return_value = [Mock()]  # sku-times-card exists
        driver.find_element = Mock(return_value=container)
        result = sel.select_date_on_page_pc()
        assert result is True
        date_elem.click.assert_called_once()

    def test_no_sku_times_card_falls_back_to_find_and_click(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        with patch.object(sel, "find_and_click_element", return_value=True) as mock_find:
            result = sel.select_date_on_page_pc()
        assert result is True
        mock_find.assert_called_once()

    def test_date_not_found_returns_false(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        with patch.object(sel, "find_and_click_element", return_value=False):
            result = sel.select_date_on_page_pc()
        assert result is False

    def test_date_element_sold_out_skipped(self):
        sel, driver, _ = _make_selector()
        elem_soldout = _mock_elem("2026-04-11 无票")
        container = Mock()
        container.find_elements = Mock(return_value=[elem_soldout])
        driver.find_elements.return_value = [Mock()]
        driver.find_element = Mock(return_value=container)
        # select_option_by_config should skip it; then find_and_click_element is tried
        with patch.object(sel, "find_and_click_element", return_value=False):
            result = sel.select_date_on_page_pc()
        assert result is False

    def test_webdriver_exception_returns_false(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.side_effect = WebDriverException("oops")
        result = sel.select_date_on_page_pc()
        assert result is False

    def test_non_fast_mode_prints_date_list(self, capsys):
        sel, driver, _ = _make_selector(fast_mode=False)
        date_elem = _mock_elem("2026-04-11")
        container = Mock()
        container.find_elements = Mock(return_value=[date_elem])
        driver.find_elements.return_value = [Mock()]
        driver.find_element = Mock(return_value=container)
        sel.select_date_on_page_pc()
        captured = capsys.readouterr()
        assert "2026-04-11" in captured.out


# ===========================================================================
# select_price_on_page_pc
# ===========================================================================

class TestSelectPriceOnPagePc:

    def test_clicks_matching_price_element(self):
        sel, driver, _ = _make_selector()
        price_elem = _mock_elem("680元")
        # find_elements is called twice: once for sku-tickets-card check, once for item-content
        driver.find_elements.side_effect = [
            [Mock()],    # sku-tickets-card found
            [price_elem],  # item-content elements
        ]
        result = sel.select_price_on_page_pc()
        assert result is True
        price_elem.click.assert_called_once()

    def test_no_sku_tickets_card_falls_back(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        with patch.object(sel, "find_and_click_element", return_value=True) as mock_find:
            result = sel.select_price_on_page_pc()
        assert result is True
        mock_find.assert_called_once()

    def test_price_not_found_returns_false(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        with patch.object(sel, "find_and_click_element", return_value=False):
            result = sel.select_price_on_page_pc()
        assert result is False

    def test_price_sold_out_skipped(self):
        sel, driver, _ = _make_selector()
        sold_out_elem = _mock_elem("680元 缺货")
        driver.find_elements.side_effect = [
            [Mock()],         # sku-tickets-card
            [sold_out_elem],  # item-content
        ]
        with patch.object(sel, "find_and_click_element", return_value=False):
            result = sel.select_price_on_page_pc()
        assert result is False

    def test_webdriver_exception_returns_false(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.side_effect = WebDriverException("fail")
        result = sel.select_price_on_page_pc()
        assert result is False


# ===========================================================================
# select_quantity_on_page
# ===========================================================================

class TestSelectQuantityOnPage:

    def test_always_returns_true_on_success(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "try_select_quantity_by_buttons", return_value=True):
            result = sel.select_quantity_on_page()
        assert result is True

    def test_falls_back_to_direct_input_if_buttons_fail(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "try_select_quantity_by_buttons", return_value=False), \
             patch.object(sel, "try_set_quantity_directly", return_value=True) as mock_direct:
            result = sel.select_quantity_on_page()
        assert result is True
        mock_direct.assert_called_once_with(2)  # 2 users

    def test_returns_true_even_if_both_methods_fail(self, capsys):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "try_select_quantity_by_buttons", return_value=False), \
             patch.object(sel, "try_set_quantity_directly", return_value=False):
            result = sel.select_quantity_on_page()
        assert result is True
        captured = capsys.readouterr()
        assert "默认数量" in captured.out

    def test_webdriver_exception_returns_true(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "try_select_quantity_by_buttons", side_effect=WebDriverException("fail")):
            result = sel.select_quantity_on_page()
        assert result is True

    def test_attribute_error_returns_true(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "try_select_quantity_by_buttons", side_effect=AttributeError("bad")):
            result = sel.select_quantity_on_page()
        assert result is True

    def test_unexpected_exception_returns_true(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "try_select_quantity_by_buttons", side_effect=RuntimeError("unexpected")):
            result = sel.select_quantity_on_page()
        assert result is True

    def test_platform_label_in_output(self, capsys):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "try_select_quantity_by_buttons", return_value=True):
            sel.select_quantity_on_page(platform="测试平台")
        captured = capsys.readouterr()
        assert "测试平台" in captured.out


# ===========================================================================
# select_quantity_on_page_pc (delegates to select_quantity_on_page)
# ===========================================================================

class TestSelectQuantityOnPagePc:

    def test_delegates_to_select_quantity_on_page(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "select_quantity_on_page", return_value=True) as mock_qty:
            result = sel.select_quantity_on_page_pc()
        assert result is True
        mock_qty.assert_called_once_with(platform="PC端")


# ===========================================================================
# try_select_quantity_by_buttons
# ===========================================================================

class TestTrySelectQuantityByButtons:

    def test_returns_false_when_no_buttons_found(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        result = sel.try_select_quantity_by_buttons(2)
        assert result is False

    def test_returns_true_when_button_clicked_successfully(self):
        sel, driver, _ = _make_selector()
        btn = Mock()
        btn.is_displayed.return_value = True
        btn.is_enabled.return_value = True
        btn.get_attribute.return_value = ""
        driver.find_elements.return_value = [btn]
        with patch.object(sel, "click_plus_buttons", return_value=True) as mock_click:
            result = sel.try_select_quantity_by_buttons(2)
        assert result is True
        mock_click.assert_called_once_with([btn], 2)

    def test_webdriver_exception_per_selector_continues(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.side_effect = WebDriverException("oops")
        result = sel.try_select_quantity_by_buttons(2)
        assert result is False


# ===========================================================================
# click_plus_buttons
# ===========================================================================

class TestClickPlusButtons:

    def test_returns_true_when_button_clicked(self):
        sel, driver, _ = _make_selector()
        btn = Mock()
        btn.is_displayed.return_value = True
        btn.is_enabled.return_value = True
        btn.get_attribute.return_value = ""  # not disabled
        driver.execute_script = Mock()
        with patch.object(sel, "get_quantity_input_value", return_value="2"):
            result = sel.click_plus_buttons([btn], 2)
        assert result is True
        # target_count - 1 = 1 click
        assert driver.execute_script.call_count == 1

    def test_skips_disabled_button(self):
        sel, driver, _ = _make_selector()
        btn = Mock()
        btn.get_attribute.return_value = "handler-up disabled"
        result = sel.click_plus_buttons([btn], 2)
        assert result is False
        driver.execute_script.assert_not_called()

    def test_skips_not_displayed_button(self):
        sel, driver, _ = _make_selector()
        btn = Mock()
        btn.get_attribute.return_value = ""
        btn.is_displayed.return_value = False
        btn.is_enabled.return_value = True
        result = sel.click_plus_buttons([btn], 2)
        assert result is False

    def test_stale_element_reference_is_skipped(self):
        sel, driver, _ = _make_selector()
        btn = Mock()
        btn.get_attribute.side_effect = StaleElementReferenceException()
        result = sel.click_plus_buttons([btn], 2)
        assert result is False

    def test_single_ticket_no_clicks_needed(self):
        sel, driver, _ = _make_selector(users=["UserA"])
        btn = Mock()
        btn.is_displayed.return_value = True
        btn.is_enabled.return_value = True
        btn.get_attribute.return_value = ""
        driver.execute_script = Mock()
        with patch.object(sel, "get_quantity_input_value", return_value="1"):
            result = sel.click_plus_buttons([btn], 1)
        assert result is True
        # target_count - 1 = 0 clicks
        driver.execute_script.assert_not_called()


# ===========================================================================
# get_quantity_input_value
# ===========================================================================

class TestGetQuantityInputValue:

    def test_returns_value_from_input_element(self):
        sel, driver, _ = _make_selector()
        input_elem = Mock()
        input_elem.get_attribute.return_value = "2"
        driver.find_element.return_value = input_elem
        result = sel.get_quantity_input_value()
        assert result == "2"

    def test_returns_none_when_no_input_found(self):
        sel, driver, _ = _make_selector()
        driver.find_element.side_effect = NoSuchElementException()
        result = sel.get_quantity_input_value()
        assert result is None


# ===========================================================================
# try_set_quantity_directly
# ===========================================================================

class TestTrySetQuantityDirectly:

    def test_returns_true_when_value_set_correctly(self):
        sel, driver, _ = _make_selector()
        input_elem = Mock()
        input_elem.get_attribute.return_value = "2"
        driver.find_element.return_value = input_elem
        driver.execute_script = Mock()
        result = sel.try_set_quantity_directly(2)
        assert result is True
        driver.execute_script.assert_called_once()

    def test_returns_false_when_input_not_found(self):
        sel, driver, _ = _make_selector()
        driver.find_element.side_effect = NoSuchElementException()
        result = sel.try_set_quantity_directly(2)
        assert result is False

    def test_returns_false_when_value_mismatch(self):
        sel, driver, _ = _make_selector()
        input_elem = Mock()
        input_elem.get_attribute.return_value = "1"  # value not updated
        driver.find_element.return_value = input_elem
        driver.execute_script = Mock()
        result = sel.try_set_quantity_directly(2)
        assert result is False

    def test_returns_false_on_webdriver_exception(self):
        sel, driver, _ = _make_selector()
        input_elem = Mock()
        driver.find_element.return_value = input_elem
        driver.execute_script = Mock(side_effect=WebDriverException("js error"))
        result = sel.try_set_quantity_directly(2)
        assert result is False


# ===========================================================================
# scan_elements_by_class
# ===========================================================================

class TestScanElementsByClass:

    def test_returns_true_when_elements_found(self):
        sel, driver, _ = _make_selector()
        elem = _mock_elem("城市内容")
        driver.find_elements.return_value = [elem]
        result = sel.scan_elements_by_class(["bui-dm-tour"], "城市")
        assert result is True

    def test_returns_false_when_no_elements_found(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        result = sel.scan_elements_by_class(["nonexistent-class"], "城市")
        assert result is False

    def test_stale_element_in_list_skipped(self):
        sel, driver, _ = _make_selector()
        stale = Mock()
        type(stale).text = property(lambda self: (_ for _ in ()).throw(StaleElementReferenceException()))
        driver.find_elements.return_value = [stale]
        # Should not raise even with stale element
        result = sel.scan_elements_by_class(["some-class"], "测试")
        assert result is True

    def test_webdriver_exception_on_find_elements_returns_false(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.side_effect = WebDriverException("crash")
        result = sel.scan_elements_by_class(["bui-dm-tour"], "城市")
        assert result is False

    def test_tries_all_selectors_in_list(self):
        sel, driver, _ = _make_selector()
        # First selector returns empty, second returns elements
        driver.find_elements.side_effect = [[], [_mock_elem("found")]]
        result = sel.scan_elements_by_class(["class-a", "class-b"], "test")
        assert result is True
        assert driver.find_elements.call_count == 2


# ===========================================================================
# scan_page_elements
# ===========================================================================

class TestScanPageElements:

    def test_runs_without_raising(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        sel.scan_page_elements()  # should not raise

    def test_outputs_section_headers(self, capsys):
        sel, driver, _ = _make_selector()
        driver.find_elements.return_value = []
        sel.scan_page_elements()
        captured = capsys.readouterr()
        assert "城市" in captured.out
        assert "场次" in captured.out
        assert "票价" in captured.out

    def test_webdriver_exception_on_full_scan_handled(self):
        sel, driver, _ = _make_selector()
        driver.find_elements.side_effect = WebDriverException("crash")
        sel.scan_page_elements()  # should not raise

    def test_prints_date_text_found(self, capsys):
        sel, driver, _ = _make_selector()
        elem_date = _mock_elem("4月11日")
        # Return different results based on call: class scans return empty,
        # date xpath scan returns the date elem, price scan returns empty
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            # Class-based scans (calls 1-3) return empty
            # Date xpath scan (call 4) returns date element
            # Price xpath scan (call 5) returns empty
            if call_count[0] == 4:
                return [elem_date]
            return []
        driver.find_elements.side_effect = side_effect
        sel.scan_page_elements()
        captured = capsys.readouterr()
        assert "4月11日" in captured.out


# ===========================================================================
# Mobile page selection methods
# ===========================================================================

class TestSelectCityOnPage:

    def test_delegates_to_find_and_click(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "find_and_click_element", return_value=True) as mock_find:
            result = sel.select_city_on_page()
        assert result is True
        mock_find.assert_called_once_with("杭州", max_results=10, print_results=False)

    def test_webdriver_exception_returns_false(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "find_and_click_element", side_effect=WebDriverException("fail")):
            result = sel.select_city_on_page()
        assert result is False

    def test_non_fast_mode_uses_print_results_true(self):
        sel, driver, _ = _make_selector(fast_mode=False)
        with patch.object(sel, "find_and_click_element", return_value=False) as mock_find:
            sel.select_city_on_page()
        _, kwargs = mock_find.call_args
        assert kwargs.get("print_results", True) is True


class TestSelectDateOnPage:

    def test_finds_and_clicks_date(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "find_and_click_element", return_value=True):
            result = sel.select_date_on_page()
        assert result is True

    def test_no_date_found_returns_false(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "find_and_click_element", return_value=False):
            result = sel.select_date_on_page()
        assert result is False

    def test_webdriver_exception_returns_false(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "find_and_click_element", side_effect=WebDriverException("err")):
            result = sel.select_date_on_page()
        assert result is False


class TestSelectPriceOnPage:

    def test_finds_and_clicks_price(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "find_and_click_element", return_value=True):
            result = sel.select_price_on_page()
        assert result is True

    def test_no_price_found_returns_false(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "find_and_click_element", return_value=False):
            result = sel.select_price_on_page()
        assert result is False

    def test_webdriver_exception_returns_false(self):
        sel, driver, _ = _make_selector()
        with patch.object(sel, "find_and_click_element", side_effect=WebDriverException("err")):
            result = sel.select_price_on_page()
        assert result is False

    def test_non_fast_mode_scans_price_elements(self, capsys):
        sel, driver, _ = _make_selector(fast_mode=False)
        price_elem = _mock_elem("¥680")
        driver.find_elements.return_value = [price_elem]
        with patch.object(sel, "find_and_click_element", return_value=True):
            sel.select_price_on_page()
        captured = capsys.readouterr()
        assert "¥680" in captured.out or "扫描" in captured.out
