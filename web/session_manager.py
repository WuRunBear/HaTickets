# -*- coding: UTF-8 -*-
"""
SessionManager — Cookie management and login flow.

Handles:
- Cookie persistence (pickle-based read/write)
- Login flow (cookie login and manual login via URL)

Note: WebDriver creation is performed by Concert.__init__ so that test patches
targeting concert.get_chromedriver_path and concert.webdriver.Chrome work
without needing to patch session_manager.* references.
"""

import os.path
import pickle
from time import sleep


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
        print("***请点击登录***\n")
        while self.driver.title.find('大麦网-全球演出赛事官方购票平台') != -1:
            sleep(1)
        print("***请扫码登录***\n")
        while self.driver.title != '大麦网-全球演出赛事官方购票平台-100%正品、先付先抢、在线选座！':
            sleep(1)
        print("***扫码成功***\n")

        pickle.dump(self.driver.get_cookies(), open("damai_cookies.pkl", "wb"))
        print("***Cookie保存成功***")
        self.driver.get(self.config.target_url)

    def get_cookie(self):
        """Load cookies from disk and inject them into the current session."""
        try:
            cookies = pickle.load(open("damai_cookies.pkl", "rb"))
            for cookie in cookies:
                cookie_dict = {
                    'domain': '.damai.cn',
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                }
                self.driver.add_cookie(cookie_dict)
            print('***完成cookie加载***\n')
        except FileNotFoundError as e:
            print(f"Cookie 文件不存在: {e}")
        except (pickle.UnpicklingError, EOFError) as e:
            print(f"Cookie 文件损坏，无法加载: {e}")

    def login(self, login_method):
        """Perform login using the specified method.

        Args:
            login_method: 0 = open login URL for manual login, 1 = cookie-based login
        """
        if login_method == 0:
            self.driver.get(self.config.login_url)
            print('***开始登录***\n')
        elif login_method == 1:
            if not os.path.exists('damai_cookies.pkl'):
                self.set_cookie()
            else:
                self.driver.get(self.config.target_url)
                self.get_cookie()
