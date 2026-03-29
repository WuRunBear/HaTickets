# -*- coding: UTF-8 -*-
"""Unit tests for mobile/item_resolver.py."""

import pytest

from mobile.item_resolver import (
    build_search_keyword,
    city_keyword,
    extract_item_id,
    normalize_text,
)


class TestExtractItemId:

    def test_extracts_from_full_url(self):
        url = "https://m.damai.cn/shows/item.html?itemId=1016133935724"
        assert extract_item_id(url) == "1016133935724"

    def test_extracts_from_raw_number(self):
        assert extract_item_id("1016133935724") == "1016133935724"

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError, match="itemId"):
            extract_item_id("https://m.damai.cn/shows/item.html")


class TestTextNormalization:

    def test_normalize_text_removes_brackets_and_spaces(self):
        assert normalize_text("【北京】 2026 张杰 未·LIVE") == "北京2026张杰未live"

    def test_city_keyword_strips_city_suffix(self):
        assert city_keyword("北京市") == "北京"

    def test_build_search_keyword_prefers_title_without_city_brackets(self):
        title = "【北京】2026张杰未·LIVE—「开往1982」演唱会-北京站"
        assert build_search_keyword(title) == "2026张杰未·LIVE—「开往1982」演唱会-北京站"
