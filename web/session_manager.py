# -*- coding: UTF-8 -*-
"""
SessionManager — Cookie management and login flow.

Handles:
- Cookie persistence (JSON-based read/write with expiry check)
- Login flow (cookie login and manual login via URL)

Note: WebDriver creation is performed by Concert.__init__ so that test patches
targeting concert.get_chromedriver_path and concert.webdriver.Chrome work
without needing to patch session_manager.* references.
"""

import json
import os
import os.path
import time
from time import sleep

from logger import get_logger

logger = get_logger(__name__)

COOKIE_FILE = "damai_cookies.json"
COOKIE_MAX_AGE = 86400  # 24 hours


class SessionManager:
    """Manages cookie-based authentication for an existing WebDriver session."""

    def __init__(self, driver, config):
        """
        Args:
            driver: a ready Selenium WebDriver instance (created by Concert)
            config: Config object with URL and credential settings
        """
        self.driver = driver
        self.config = config

    def set_cookie(self):
        """Navigate to index, wait for manual login, then persist cookies to disk."""
        self.driver.get(self.config.index_url)
        logger.info("***请点击登录***")
        while self.driver.title.find('大麦网-全球演出赛事官方购票平台') != -1:
            sleep(1)
        logger.info("***请扫码登录***")
        while self.driver.title != '大麦网-全球演出赛事官方购票平台-100%正品、先付先抢、在线选座！':
            sleep(1)
        logger.info("***扫码成功***")

        data = {"cookies": self.driver.get_cookies(), "saved_at": time.time()}
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logger.info("***Cookie保存成功***")
        self.driver.get(self.config.target_url)

    def get_cookie(self):
        """Load cookies from disk and inject them into the current session."""
        try:
            with open(COOKIE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if time.time() - data.get("saved_at", 0) > COOKIE_MAX_AGE:
                os.remove(COOKIE_FILE)
                logger.warning("Cookie 已过期（超过24小时），已自动删除")
                return
            for cookie in data.get("cookies", []):
                cookie_dict = {
                    'domain': '.damai.cn',
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                }
                self.driver.add_cookie(cookie_dict)
            logger.info('***完成cookie加载***')
        except FileNotFoundError:
            logger.warning("Cookie 文件不存在，将重新登录")
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Cookie 文件格式错误: {e}")
            try:
                os.remove(COOKIE_FILE)
            except OSError:
                pass

    def login(self, login_method):
        """Perform login using the specified method.

        Args:
            login_method: 0 = open login URL for manual login, 1 = cookie-based login
        """
        if login_method == 0:
            self.driver.get(self.config.login_url)
            logger.info('***开始登录***')
        elif login_method == 1:
            if not os.path.exists(COOKIE_FILE):
                self.set_cookie()
            else:
                self.driver.get(self.config.target_url)
                self.get_cookie()
