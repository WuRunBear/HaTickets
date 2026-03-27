# -*- coding: UTF-8 -*-
"""Unit tests for shared/xpath_utils.py."""

import pytest
from unittest.mock import Mock

from shared.xpath_utils import escape_xpath_string


class TestEscapeXpathString:

    def test_simple_string(self):
        assert escape_xpath_string("hello") == "'hello'"

    def test_empty_string(self):
        assert escape_xpath_string("") == "''"

    def test_string_with_single_quote(self):
        result = escape_xpath_string("O'Brien")
        assert result == '"O\'Brien"'

    def test_string_with_double_quote(self):
        result = escape_xpath_string('say "hi"')
        assert result == "'say \"hi\"'"

    def test_string_with_both_quotes(self):
        result = escape_xpath_string("it's a \"test\"")
        assert "concat(" in result

    def test_concat_result_contains_original_parts(self):
        value = "it's a \"test\""
        result = escape_xpath_string(value)
        # Should contain both text parts split around the single quote
        assert "it" in result
        assert "s a" in result

    def test_chinese_name_no_quotes(self):
        result = escape_xpath_string("张三")
        assert result == "'张三'"

    def test_no_quotes_uses_single_quote_wrapper(self):
        result = escape_xpath_string("normal text")
        assert result.startswith("'")
        assert result.endswith("'")

    def test_only_double_quotes_uses_single_quote_wrapper(self):
        result = escape_xpath_string('has "double" quotes')
        assert result.startswith("'")
        assert result.endswith("'")

    def test_only_single_quotes_uses_double_quote_wrapper(self):
        result = escape_xpath_string("has 'single' quotes")
        assert result.startswith('"')
        assert result.endswith('"')

    def test_both_quotes_uses_concat(self):
        result = escape_xpath_string("O'Brien said \"hello\"")
        assert result.startswith("concat(")

    def test_xpath_injection_safety_single_quote(self):
        """Verify the escaped value can be safely embedded in an XPath contains() call."""
        user = "O'Brien"
        escaped = escape_xpath_string(user)
        xpath = f"//*[contains(text(), {escaped})]"
        # The XPath should not contain an unescaped bare single quote that breaks parsing
        # The entire literal is now wrapped in double quotes
        assert escaped == '"O\'Brien"'
        assert '"O\'Brien"' in xpath


class TestUserSelectorWithQuotedName:
    """Integration-style tests verifying UserSelector handles names with quotes."""

    def test_try_select_user_method1_with_single_quote_in_name(self):
        """UserSelector.try_select_user_method1 should not raise for names with quotes."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

        from web.user_selector import UserSelector

        mock_driver = Mock()
        mock_driver.find_elements = Mock(return_value=[])

        mock_config = Mock()
        mock_config.fast_mode = True
        mock_config.users = ["O'Brien"]

        selector = UserSelector(mock_driver, mock_config)

        # Should not raise an exception despite single quote in user name
        result = selector.try_select_user_method1("O'Brien", ["O'Brien"], 0)
        assert result == 0  # no element found, so user_selected stays 0

    def test_scan_user_elements_with_single_quote_in_name(self):
        """UserSelector.scan_user_elements should not raise for names with quotes."""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

        from web.user_selector import UserSelector

        mock_driver = Mock()
        mock_driver.find_elements = Mock(return_value=[])

        mock_config = Mock()
        mock_config.fast_mode = True
        mock_config.users = ["O'Brien"]

        selector = UserSelector(mock_driver, mock_config)

        # Should not raise, returns False because no elements found
        result = selector.scan_user_elements(retry_count=1)
        assert result is False
