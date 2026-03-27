# -*- coding: UTF-8 -*-
"""
TicketSelector — Ticket/date/price/city selection logic.

Extracted from concert.py to handle:
- Selecting dates, prices, and cities on both PC and mobile pages
- Quantity selection on the details page
- Generic element scanning and click helpers
"""

import time

from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException,
)


class TicketSelector:
    """Handles ticket, date, price, city, and quantity selection on the details page."""

    def __init__(self, driver, config):
        self.driver = driver
        self.config = config

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def select_option_by_config(self, config_list, element_list, skip_keywords=None):
        """Select an option from a page element list based on config values.

        Args:
            config_list: configured option values (e.g. dates, prices)
            element_list: page elements to search through
            skip_keywords: text patterns that indicate an unavailable option

        Returns:
            bool: True if an option was successfully selected
        """
        if not config_list or not element_list:
            return False

        skip_keywords = skip_keywords or ['无票', '缺货']
        wait_time = 0.2 if self.config.fast_mode else 0.5

        for config_value in config_list:
            for element in element_list:
                try:
                    elem_text = element.text
                    if config_value in elem_text and not any(kw in elem_text for kw in skip_keywords):
                        element.click()
                        time.sleep(wait_time)
                        return True
                except (StaleElementReferenceException, ElementClickInterceptedException, WebDriverException):
                    continue
        return False

    def find_and_click_element(self, search_text, max_results=10, skip_keywords=None, print_results=True):
        """Find and click an element containing the given text.

        Args:
            search_text: text to search for
            max_results: maximum number of elements to try
            skip_keywords: text patterns to skip
            print_results: whether to print search results

        Returns:
            bool: True if an element was successfully clicked
        """
        skip_keywords = skip_keywords or []
        xpath = f"//*[contains(text(), '{search_text}')]"
        elements = self.driver.find_elements(By.XPATH, xpath)

        if print_results:
            print(f"  找到 {len(elements)} 个包含 '{search_text}' 的元素")

        for idx, elem in enumerate(elements[:max_results]):
            try:
                elem_text = elem.text.strip()
                if not elem_text or any(kw in elem_text for kw in skip_keywords):
                    continue

                if print_results and len(elem_text) < 100:
                    print(f"    [{idx}] {elem_text}")

                for target in [elem, elem.find_element(By.XPATH, '..')]:
                    try:
                        target.click()
                        wait_time = 0.2 if self.config.fast_mode else 0.5
                        time.sleep(wait_time)
                        if print_results:
                            print(f"  ✓ 已点击: {elem_text}")
                        return True
                    except (ElementClickInterceptedException, StaleElementReferenceException, WebDriverException):
                        continue
            except (StaleElementReferenceException, NoSuchElementException, WebDriverException):
                continue

        if print_results:
            print(f"  ⚠ 未找到匹配的元素")
        return False

    def click_element_by_text(self, text_content, tag_names=None, exact_match=False):
        """Click an element identified by its text content.

        Args:
            text_content: text to match
            tag_names: HTML tag names to search (default: div, span, button)
            exact_match: whether to require an exact text match

        Returns:
            bool: True if an element was successfully clicked
        """
        tag_names = tag_names or ['div', 'span', 'button']

        for tag in tag_names:
            try:
                if exact_match:
                    xpath = f"//{tag}[text()='{text_content}']"
                else:
                    xpath = f"//{tag}[contains(text(), '{text_content}')]"
                elements = self.driver.find_elements(By.XPATH, xpath)
                for elem in elements[:5]:
                    try:
                        elem_text = elem.text.strip()
                        if (exact_match and elem_text == text_content) or \
                           (not exact_match and text_content in elem_text):
                            for target in [elem, elem.find_element(By.XPATH, '..')]:
                                try:
                                    target.click()
                                    time.sleep(0.5)
                                    return True
                                except (ElementClickInterceptedException, StaleElementReferenceException, WebDriverException):
                                    continue
                    except (StaleElementReferenceException, NoSuchElementException, WebDriverException):
                        continue
            except WebDriverException:
                continue
        return False

    # ------------------------------------------------------------------
    # PC page selection
    # ------------------------------------------------------------------

    def select_city_on_page_pc(self):
        """Select city on the PC details page (with fuzzy matching)."""
        try:
            if self.driver.find_elements(value='bui-dm-tour', by=By.CLASS_NAME):
                city_name_element_list = self.driver.find_element(
                    value='bui-dm-tour', by=By.CLASS_NAME
                ).find_elements(value='tour-card', by=By.CLASS_NAME)

                if not self.config.fast_mode:
                    print(f"  找到 {len(city_name_element_list)} 个城市选项:\n")
                    cities = []
                    for city_elem in city_name_element_list:
                        try:
                            city_text = city_elem.text.strip()
                            if city_text:
                                cities.append(city_text)
                        except StaleElementReferenceException:
                            pass
                    for idx, city_text in enumerate(cities):
                        print(f"    [{idx}] {city_text}")
                    print()

                for city_name_element in city_name_element_list:
                    try:
                        if self.config.city in city_name_element.text:
                            if not self.config.fast_mode:
                                print(f"  ✓ 匹配成功: {city_name_element.text}\n")
                            city_name_element.click()
                            time.sleep(0.1 if self.config.fast_mode else 0.2)
                            return True
                    except (StaleElementReferenceException, ElementClickInterceptedException, WebDriverException):
                        continue

            if not self.config.fast_mode:
                print(f"  尝试通用文本搜索...")
            return self.find_and_click_element(
                self.config.city,
                max_results=10,
                print_results=not self.config.fast_mode
            )

        except Exception as e:
            if not self.config.fast_mode:
                print(f"  城市选择异常: {e}")
            return False

    def select_date_on_page_pc(self):
        """Select date/session on the PC details page (with fuzzy matching)."""
        try:
            if self.driver.find_elements(value='sku-times-card', by=By.CLASS_NAME):
                order_name_element_list = self.driver.find_element(
                    value='sku-times-card', by=By.CLASS_NAME
                ).find_elements(value='bui-dm-sku-card-item', by=By.CLASS_NAME)

                if not self.config.fast_mode:
                    print(f"  找到 {len(order_name_element_list)} 个场次选项:\n")
                    dates = []
                    for elem in order_name_element_list:
                        try:
                            text = elem.text.strip()
                            if text:
                                dates.append(text)
                        except StaleElementReferenceException:
                            pass
                    for idx, text in enumerate(dates):
                        print(f"    [{idx}] {text}")
                    print()

                if self.select_option_by_config(self.config.dates, order_name_element_list):
                    return True

            if not self.config.fast_mode:
                print(f"  尝试通用文本搜索...")
            for date in self.config.dates:
                if self.find_and_click_element(date, max_results=10, skip_keywords=['无票', '售罄'], print_results=not self.config.fast_mode):
                    return True

            if not self.config.fast_mode:
                print(f"  ⚠ 未找到匹配的场次")
            return False

        except WebDriverException as e:
            if not self.config.fast_mode:
                print(f"  场次选择异常: {e}")
            return False

    def select_price_on_page_pc(self):
        """Select ticket price on the PC details page (with fuzzy matching)."""
        try:
            if self.driver.find_elements(value='sku-tickets-card', by=By.CLASS_NAME):
                sku_name_element_list = self.driver.find_elements(value='item-content', by=By.CLASS_NAME)

                if not self.config.fast_mode:
                    print(f"  找到 {len(sku_name_element_list)} 个票价选项:\n")
                    prices = []
                    for elem in sku_name_element_list:
                        try:
                            text = elem.text.strip()
                            if text:
                                prices.append(text)
                        except StaleElementReferenceException:
                            pass
                    for idx, text in enumerate(prices):
                        print(f"    [{idx}] {text}")
                    print()

                if self.select_option_by_config(self.config.prices, sku_name_element_list, ['缺', '售罄', '无票']):
                    return True

            if not self.config.fast_mode:
                print(f"  尝试通用文本搜索...")
            for price in self.config.prices:
                if self.find_and_click_element(price, max_results=15, skip_keywords=['缺货', '售罄', '无票'], print_results=not self.config.fast_mode):
                    return True

            if not self.config.fast_mode:
                print(f"  ⚠ 未找到匹配的票价")
            return False

        except WebDriverException as e:
            if not self.config.fast_mode:
                print(f"  票价选择异常: {e}")
            return False

    def select_quantity_on_page_pc(self):
        """Select ticket quantity on the PC details page."""
        return self.select_quantity_on_page(platform="PC端")

    # ------------------------------------------------------------------
    # Mobile page selection
    # ------------------------------------------------------------------

    def select_city_on_page(self):
        """Select city on the mobile details page."""
        try:
            return self.find_and_click_element(
                self.config.city,
                max_results=10,
                print_results=not self.config.fast_mode
            )
        except WebDriverException as e:
            if not self.config.fast_mode:
                print(f"  城市选择异常: {e}")
            return False

    def select_date_on_page(self):
        """Select date/session on the mobile details page."""
        try:
            if not self.config.fast_mode:
                print(f"  搜索场次: {self.config.dates}")
            for date in self.config.dates:
                if self.find_and_click_element(date, max_results=10, skip_keywords=['无票', '售罄'], print_results=not self.config.fast_mode):
                    if not self.config.fast_mode:
                        print(f"  ✓ 已选择场次: {date}\n")
                    return True

            if not self.config.fast_mode:
                print(f"  ⚠ 未找到匹配的场次")
            return False
        except WebDriverException as e:
            if not self.config.fast_mode:
                print(f"  场次选择异常: {e}")
            return False

    def select_price_on_page(self):
        """Select ticket price on the mobile details page."""
        try:
            if not self.config.fast_mode:
                print("  扫描票价元素...")
                price_candidates = self.driver.find_elements(By.XPATH, "//*[contains(text(), '¥') or contains(text(), '元')]")
                seen = set()
                for elem in price_candidates[:15]:
                    try:
                        text = elem.text.strip()
                        if text and text not in seen and len(text) < 50:
                            print(f"    - {text}")
                            seen.add(text)
                    except StaleElementReferenceException:
                        pass
                print()

            for price in self.config.prices:
                if not self.config.fast_mode:
                    print(f"  尝试匹配: {price}")
                if self.find_and_click_element(price, max_results=10,
                                               skip_keywords=['缺货', '售罄', '无票'],
                                               print_results=not self.config.fast_mode):
                    if not self.config.fast_mode:
                        print(f"  ✓ 已选择票价: {price}\n")
                    return True

            if not self.config.fast_mode:
                print(f"  ⚠ 未找到匹配的票价")
            return False
        except WebDriverException as e:
            if not self.config.fast_mode:
                print(f"  票价选择异常: {e}")
            return False

    def select_quantity_on_page(self, platform="移动端"):
        """Select ticket quantity on the details page (PC and mobile).

        Args:
            platform: label for log output

        Returns:
            bool: always True (does not block the flow)
        """
        try:
            target_count = len(self.config.users)
            print(f"  【{platform}详情页】目标数量: {target_count} 张")

            success = self.try_select_quantity_by_buttons(target_count)

            if not success:
                success = self.try_set_quantity_directly(target_count)

            if not success:
                print(f"  ⚠ 未找到数量选择器，将使用默认数量 (1 张)")

            return True

        except (AttributeError, TypeError, ValueError) as e:
            print(f"  ❌ 数量选择配置错误: {e}")
            return True
        except WebDriverException as e:
            print(f"  ⚠ WebDriver 异常，继续执行: {e}")
            return True
        except Exception as e:
            # Intentional broad catch: quantity selection must never block the
            # ticket-grabbing flow; any unexpected error is logged and ignored.
            print(f"  ⚠ 未预期的异常: {e}")
            return True

    def try_select_quantity_by_buttons(self, target_count):
        """Attempt to select quantity by clicking the + button.

        Args:
            target_count: desired ticket count

        Returns:
            bool: True if successful
        """
        selectors_to_try = [
            ("//div[contains(@class, 'cafe-c-input-number')]//a[contains(@class, 'handler-up')]", "cafe-c-input-number 结构"),
            ("//a[contains(@class, 'cafe-c-input-number-handler-up')]", "cafe-c-input-number-handler-up"),
            ("//div[contains(@class, 'number_right_info')]//a[last()]", "number_right_info"),
            ("//*[contains(@class, 'cafe-c-input-number')]//a[contains(text(), '+')]", "cafe-input-number + 按钮"),
            ("//a[contains(@class, 'handler-up')]", "通用 handler-up"),
        ]

        for selector, method_name in selectors_to_try:
            try:
                plus_btns = self.driver.find_elements(By.XPATH, selector)
                if plus_btns:
                    print(f"    ✓ 找到 + 按钮 ({method_name}): {len(plus_btns)} 个")
                    if self.click_plus_buttons(plus_btns, target_count):
                        return True
            except (NoSuchElementException, WebDriverException):
                continue

        return False

    def click_plus_buttons(self, plus_btns, target_count):
        """Click the + button to increase quantity.

        Args:
            plus_btns: list of + button elements
            target_count: desired ticket count

        Returns:
            bool: True if successful
        """
        for btn in plus_btns[:3]:
            try:
                class_attr = btn.get_attribute('class') or ''
                if 'disabled' in class_attr.lower():
                    continue

                if btn.is_displayed() and btn.is_enabled():
                    for i in range(target_count - 1):
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.25)

                    current_val = self.get_quantity_input_value()
                    if current_val:
                        print(f"    输入框当前值: {current_val}")

                    print(f"  ✓ 已选择 {target_count} 张票")
                    return True
            except StaleElementReferenceException:
                continue
            except WebDriverException:
                continue

        return False

    def get_quantity_input_value(self):
        """Read the current value from the quantity input field.

        Returns:
            str: input value, or None on failure
        """
        input_selectors = [
            "//input[contains(@class, 'cafe-c-input-number-input')]",
            "//div[contains(@class, 'cafe-c-input-number')]//input",
        ]
        for inp_sel in input_selectors:
            try:
                input_elem = self.driver.find_element(By.XPATH, inp_sel)
                return input_elem.get_attribute('value')
            except NoSuchElementException:
                continue
        return None

    def try_set_quantity_directly(self, target_count):
        """Directly set the quantity input field value.

        Args:
            target_count: desired ticket count

        Returns:
            bool: True if successful
        """
        from selenium.common.exceptions import JavascriptException

        try:
            input_selector = "//input[contains(@class, 'cafe-c-input-number-input')]"
            input_elem = self.driver.find_element(By.XPATH, input_selector)
            print(f"    找到输入框，直接设置值")

            self.driver.execute_script(f"""
                arguments[0].value = '{target_count}';
                arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                arguments[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                arguments[0]._value = '{target_count}';
                if (arguments[0]._v_model) {{
                    arguments[0]._v_model = '{target_count}';
                }}
            """, input_elem)

            time.sleep(0.3)
            new_val = input_elem.get_attribute('value')
            print(f"    设置后输入框值: {new_val}")

            if new_val == str(target_count):
                print(f"  ✓ 已选择 {target_count} 张票")
                return True
        except NoSuchElementException:
            pass
        except (JavascriptException, WebDriverException) as e:
            print(f"    直接设置输入框失败: {e}")

        return False

    # ------------------------------------------------------------------
    # Page scanning helpers
    # ------------------------------------------------------------------

    def scan_elements_by_class(self, class_names, label):
        """Scan elements by CSS class name for debugging.

        Returns:
            bool: True if any matching elements were found
        """
        print(f"  🔍 扫描{label}...")
        try:
            for selector in class_names:
                try:
                    elements = self.driver.find_elements(By.CLASS_NAME, selector)
                    if elements:
                        print(f"  ✓ 找到 class='{selector}': {len(elements)} 个")
                        for idx, elem in enumerate(elements[:3]):
                            try:
                                text = elem.text.strip()[:50]
                                if text:
                                    print(f"      [{idx}] {text}")
                            except StaleElementReferenceException:
                                pass
                        return True
                except WebDriverException:
                    pass
            return False
        except WebDriverException as e:
            print(f"    扫描失败: {e}")
            return False

    def scan_page_elements(self):
        """Scan page elements for debugging purposes."""
        try:
            print("【1】查找城市相关元素:")
            city_selectors = ['bui-dm-tour', 'tour-list', 'city-list', 'sku-tour']
            self.scan_elements_by_class(city_selectors, "城市")

            print("\n【2】查找场次相关元素:")
            date_selectors = ['sku-times-card', 'sku-times', 'date-list', 'tour-list']
            self.scan_elements_by_class(date_selectors, "场次")

            print("\n【3】查找票价相关元素:")
            price_selectors = ['sku-tickets-card', 'sku-ticket', 'price-list', 'ticket-list']
            self.scan_elements_by_class(price_selectors, "票价")

            print("\n【4】查找所有包含日期的文本:")
            try:
                all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '月') or contains(text(), '日')]")
                seen = set()
                for elem in all_elements[:20]:
                    try:
                        text = elem.text.strip()
                        if text and 3 < len(text) < 100 and text not in seen:
                            print(f"  - {text}")
                            seen.add(text)
                    except StaleElementReferenceException:
                        pass
            except WebDriverException:
                pass

            print("\n【5】查找所有包含价格的文本:")
            try:
                all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '¥') or contains(text(), '元')]")
                seen = set()
                for elem in all_elements[:20]:
                    try:
                        text = elem.text.strip()
                        if text and text not in seen and len(text) < 50:
                            print(f"  - {text}")
                            seen.add(text)
                    except StaleElementReferenceException:
                        pass
            except WebDriverException:
                pass

        except WebDriverException as e:
            print(f"  扫描异常: {e}")
