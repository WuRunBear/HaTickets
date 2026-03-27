# -*- coding: UTF-8 -*-
"""
UserSelector — Purchaser/attendee selection logic.

Extracted from concert.py to handle:
- Scanning for user elements on the order confirmation page
- Four different strategies for selecting users (checkboxes, divs, JS clicks)
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.xpath_utils import escape_xpath_string
from logger import get_logger

logger = get_logger(__name__)
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException,
    JavascriptException,
)


class UserSelector:
    """Handles selecting ticket purchaser(s) on the order confirmation page."""

    def __init__(self, driver, config):
        self.driver = driver
        self.config = config

    def _get_wait_time(self, short=False):
        """Return the appropriate wait time based on fast_mode setting."""
        if short:
            return 0.1 if self.config.fast_mode else 0.2
        return 0.2 if self.config.fast_mode else 0.3

    def scan_user_elements(self, retry_count=5, retry_interval=0.5):
        """Scan for user elements on the page, with automatic retries.

        Args:
            retry_count: number of attempts before giving up
            retry_interval: seconds to wait between retries

        Returns:
            bool: True if any user elements were found
        """
        logger.debug("  🔍 扫描购票人元素...")

        for attempt in range(retry_count):
            if attempt > 0:
                logger.debug(f"  第 {attempt + 1} 次尝试...")
                time.sleep(retry_interval)

            try:
                found_any = False
                for user in self.config.users:
                    xpath = f"//*[contains(text(), {escape_xpath_string(user)})]"
                    user_elements = self.driver.find_elements(By.XPATH, xpath)

                    if user_elements:
                        if not found_any and attempt == 0:
                            logger.debug(f"  找到 {len(user_elements)} 个包含 '{user}' 的元素")
                        found_any = True
                        if attempt == 0:
                            for idx, elem in enumerate(user_elements[:3]):
                                try:
                                    text = elem.text.strip()
                                    tag = elem.tag_name
                                    class_attr = elem.get_attribute('class') or ''
                                    logger.debug(f"    [{idx}] <{tag}> class='{class_attr}' text='{text}'")
                                except StaleElementReferenceException:
                                    pass
                    else:
                        if attempt == 0:
                            logger.warning(f"  ⚠ 未找到包含 '{user}' 的元素")

                if found_any:
                    if attempt > 0:
                        logger.debug(f"  ✓ 第 {attempt + 1} 次尝试成功找到用户元素")
                    return True

            except WebDriverException as e:
                if attempt == 0:
                    logger.warning(f"  扫描异常: {e}")

        logger.warning(f"  ⚠ {retry_count} 次尝试后仍未找到用户元素")
        return False

    def try_select_user_method1(self, user, users_to_select, user_selected):
        """Method 1: Find and click a div containing the user's name."""
        if user_selected >= len(users_to_select):
            return user_selected

        try:
            logger.debug(f"    尝试方法1: 查找并点击包含用户名的div")
            xpath_expression = f"//div[contains(text(), {escape_xpath_string(user)})]"
            user_elements = self.driver.find_elements(By.XPATH, xpath_expression)

            if not user_elements:
                logger.debug(f"      未找到包含 '{user}' 的div")
                return user_selected

            logger.debug(f"      找到 {len(user_elements)} 个包含 '{user}' 的div")

            best_match = None
            for elem in user_elements:
                try:
                    elem_text = elem.text.strip()
                    if elem_text == user:
                        best_match = elem
                        break
                    elif len(elem_text) < 30 and user in elem_text:
                        if best_match is None:
                            best_match = elem
                except StaleElementReferenceException:
                    continue

            if not best_match:
                logger.debug(f"      未找到合适的div元素")
                return user_selected

            checkbox_selectors = [
                "following-sibling::*//i[contains(@class, 'iconfont')]",
                "following-sibling::*[1]//i",
                "following-sibling::i",
                "..//following-sibling::*//i[contains(@class, 'iconfont')]",
                "..//following-sibling::i",
                "..//i[contains(@class, 'iconfont')]",
                "..//i[contains(@class, 'icon')]",
                "..//i[contains(@class, 'check')]",
                "following-sibling::*[1]//input",
                "following-sibling::*[1]//span",
                "..//following-sibling::*//input",
                "../..//input[@type='checkbox']",
                "..//label",
            ]

            for selector in checkbox_selectors:
                try:
                    checkbox = best_match.find_element(By.XPATH, selector)
                    elem_tag = checkbox.tag_name
                    elem_class = checkbox.get_attribute('class') or ''
                    logger.debug(f"        找到可点击元素: <{elem_tag}> class='{elem_class}'")
                    self.driver.execute_script("arguments[0].click();", checkbox)
                    logger.info(f"  ✓ 已选择: {user}")
                    time.sleep(self._get_wait_time())
                    return user_selected + 1
                except (NoSuchElementException, JavascriptException, WebDriverException):
                    continue

            logger.debug(f"        未找到复选框/icon，直接点击div本身")
            try:
                self.driver.execute_script("arguments[0].click();", best_match)
                logger.info(f"  ✓ 已点击: {user}")
                time.sleep(self._get_wait_time())
                return user_selected + 1
            except JavascriptException:
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", best_match)
                    time.sleep(0.2)
                    self.driver.execute_script("arguments[0].click();", best_match)
                    logger.info(f"  ✓ 已点击（滚动后）: {user}")
                    time.sleep(self._get_wait_time())
                    return user_selected + 1
                except (JavascriptException, WebDriverException) as e:
                    logger.error(f"        点击失败: {e}")

        except WebDriverException as e:
            logger.warning(f"    方法1失败: {e}")

        return user_selected

    def try_select_user_method2(self, user, users_to_select, user_selected):
        """Method 2: Select user via checkboxes and labels."""
        if user_selected >= len(users_to_select):
            return user_selected

        try:
            logger.debug(f"    尝试方法2: 查找所有复选框")
            all_checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            all_labels = self.driver.find_elements(By.TAG_NAME, 'label')

            logger.debug(f"      找到 {len(all_checkboxes)} 个复选框")
            logger.debug(f"      找到 {len(all_labels)} 个标签")

            for label in all_labels:
                try:
                    label_text = label.text.strip()
                    if user in label_text:
                        label_for = label.get_attribute('for')
                        if label_for:
                            checkbox = self.driver.find_element(By.ID, label_for)
                            if not checkbox.is_selected():
                                checkbox.click()
                                logger.debug(f"        通过label选择: {label_text}")
                                logger.info(f"  ✓ 已选择: {user}")
                                time.sleep(self._get_wait_time())
                                return user_selected + 1
                except (StaleElementReferenceException, NoSuchElementException,
                        ElementClickInterceptedException, WebDriverException):
                    continue

            if user_selected < len(users_to_select):
                for checkbox in all_checkboxes:
                    try:
                        parent = checkbox.find_element(By.XPATH, '..')
                        nearby_text = parent.text.strip()

                        if user in nearby_text:
                            if not checkbox.is_selected():
                                checkbox.click()
                                logger.debug(f"        通过附近文本选择: {nearby_text}")
                                logger.info(f"  ✓ 已选择: {user}")
                                time.sleep(self._get_wait_time())
                                return user_selected + 1
                    except (StaleElementReferenceException, NoSuchElementException,
                            ElementClickInterceptedException, WebDriverException):
                        continue

        except WebDriverException as e:
            logger.warning(f"    方法2失败: {e}")

        return user_selected

    def try_select_user_method3(self, user, users_to_select, user_selected):
        """Method 3: Click any element containing the user's name."""
        if user_selected >= len(users_to_select):
            return user_selected

        try:
            logger.debug(f"    尝试方法3: 点击包含用户名的元素")
            xpath = f"//*[contains(text(), {escape_xpath_string(user)})]"
            user_elements = self.driver.find_elements(By.XPATH, xpath)

            for elem in user_elements[:10]:
                try:
                    elem_text = elem.text.strip()
                    if elem_text == user or (len(elem_text) < 30 and user in elem_text):
                        logger.debug(f"        尝试点击: {elem_text}")
                        elem.click()
                        logger.info(f"  ✓ 已点击: {user}")
                        time.sleep(self._get_wait_time())
                        return user_selected + 1
                except (StaleElementReferenceException, ElementClickInterceptedException, WebDriverException):
                    continue

        except WebDriverException as e:
            logger.warning(f"    方法3失败: {e}")

        return user_selected

    def try_select_user_method4(self, user, users_to_select, user_selected):
        """Method 4: Use JavaScript to find and click the user element."""
        if user_selected >= len(users_to_select):
            return user_selected

        try:
            logger.debug(f"    尝试方法4: 使用JavaScript查找并点击")
            js_script = f"""
            var divs = document.getElementsByTagName('div');
            var targetDivs = [];
            for (var i = 0; i < divs.length; i++) {{
                if (divs[i].textContent.includes('{user}') &&
                    divs[i].textContent.trim() === '{user}' &&
                    divs[i].offsetParent !== null) {{
                    targetDivs.push(divs[i]);
                }}
            }}
            return targetDivs;
            """
            target_divs = self.driver.execute_script(js_script)

            if not target_divs:
                logger.debug(f"      未找到精确匹配 '{user}' 的div")
                return user_selected

            logger.debug(f"      找到 {len(target_divs)} 个匹配的div")
            div = target_divs[0]

            find_icon_script = """
            var div = arguments[0];
            var nextSibling = div.nextElementSibling;
            if (nextSibling) {
                var icons = nextSibling.getElementsByTagName('i');
                for (var i = 0; i < icons.length; i++) {
                    if (icons[i].className.indexOf('iconfont') !== -1) {
                        return icons[i];
                    }
                }
            }
            var parent = div.parentElement;
            if (parent) {
                var parentSibling = parent.nextElementSibling;
                if (parentSibling) {
                    var icons = parentSibling.getElementsByTagName('i');
                    for (var i = 0; i < icons.length; i++) {
                        if (icons[i].className.indexOf('iconfont') !== -1) {
                            return icons[i];
                        }
                    }
                }
            }
            return div;
            """

            target_elem = self.driver.execute_script(find_icon_script, div)
            elem_tag = target_elem.tag_name
            elem_class = target_elem.get_attribute('class') or ''

            try:
                self.driver.execute_script("arguments[0].click();", target_elem)
                logger.debug(f"      ✓ 已通过JavaScript点击: <{elem_tag}> class='{elem_class}'")
                logger.info(f"  ✓ 已选择: {user}")
                time.sleep(0.5)
                return user_selected + 1
            except (JavascriptException, WebDriverException) as e:
                logger.error(f"      点击失败: {e}")

        except (JavascriptException, WebDriverException) as e:
            logger.warning(f"    方法4失败: {e}")

        return user_selected

    def select_users(self, ticket_count, users_to_select):
        """Select all required attendees using cascading fallback methods.

        Args:
            ticket_count: number of tickets (and users) to select
            users_to_select: ordered list of user names to select
        """
        user_selected = 0

        for i, user in enumerate(users_to_select):
            logger.info(f"  正在选择: {user} ({i + 1}/{ticket_count})")

            if user_selected >= ticket_count:
                logger.warning(f"    ⚠ 已选够 {ticket_count} 人，跳过: {user}")
                continue

            new_user_selected = self.try_select_user_method1(user, users_to_select, user_selected)
            if new_user_selected > user_selected:
                user_selected = new_user_selected
            else:
                new_user_selected = self.try_select_user_method2(user, users_to_select, user_selected)
                if new_user_selected > user_selected:
                    user_selected = new_user_selected
                else:
                    new_user_selected = self.try_select_user_method3(user, users_to_select, user_selected)
                    if new_user_selected > user_selected:
                        user_selected = new_user_selected
                    else:
                        new_user_selected = self.try_select_user_method4(user, users_to_select, user_selected)
                        if new_user_selected > user_selected:
                            user_selected = new_user_selected

            if user_selected <= i:
                logger.warning(f"  ⚠ 未找到用户: {user}")

        logger.info(f"***已选择 {user_selected}/{ticket_count} 个观众***")

        if user_selected > 0:
            logger.info(f"  ✓ 已选择的观众: {users_to_select[:user_selected]}")
        if user_selected < ticket_count:
            logger.warning(f"  ⚠ 未选择的观众: {users_to_select[user_selected:ticket_count]}")
