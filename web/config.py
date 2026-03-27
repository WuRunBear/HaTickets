# -*- coding: UTF-8 -*-
"""
__Author__ = "WECENG"
__Version__ = "1.0.0"
__Description__ = "配置类"
__Created__ = 2023/10/11 18:01
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.config_validator import validate_url, validate_non_empty_list, validate_positive_int


class Config:

    def __init__(self, index_url, login_url, target_url, users, city, dates, prices, if_listen, if_commit_order, max_retries=1000, fast_mode=True, page_load_delay=2):
        # Validate URLs
        validate_url(index_url, "index_url")
        validate_url(login_url, "login_url")
        validate_url(target_url, "target_url")

        # Validate users
        validate_non_empty_list(users, "users")
        if not all(isinstance(u, str) for u in users):
            raise ValueError(f"users 列表中的每个元素必须是字符串，实际值: {users!r}")

        # Validate city
        if city is not None and (not isinstance(city, str) or len(city.strip()) == 0):
            raise ValueError(f"city 必须是非空字符串或 None，实际值: {city!r}")

        # Validate dates
        if dates is not None:
            if not isinstance(dates, list):
                raise ValueError(f"dates 必须是字符串列表或 None，实际值: {dates!r}")
            if not all(isinstance(d, str) for d in dates):
                raise ValueError(f"dates 列表中的每个元素必须是字符串，实际值: {dates!r}")

        # Validate prices
        if prices is not None:
            if not isinstance(prices, list):
                raise ValueError(f"prices 必须是字符串列表或 None，实际值: {prices!r}")
            if not all(isinstance(p, str) for p in prices):
                raise ValueError(f"prices 列表中的每个元素必须是字符串，实际值: {prices!r}")

        # Validate max_retries
        max_retries = validate_positive_int(max_retries, "max_retries", max_value=100000)

        # Validate page_load_delay
        if not isinstance(page_load_delay, (int, float)) or isinstance(page_load_delay, bool) or page_load_delay < 0:
            raise ValueError(f"page_load_delay 必须是非负数，实际值: {page_load_delay!r}")

        self.index_url = index_url
        self.login_url = login_url
        self.target_url = target_url
        self.users = users
        self.city = city
        self.dates = dates
        self.prices = prices
        self.if_listen = if_listen
        self.if_commit_order = if_commit_order
        self.max_retries = max_retries
        self.fast_mode = fast_mode  # 快速模式：减少等待时间和调试输出
        self.page_load_delay = page_load_delay  # 订单确认页加载等待时间（秒）
