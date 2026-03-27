# -*- coding: UTF-8 -*-
"""
OrderSubmitter — Order submission logic.

Extracted from concert.py to handle:
- Scanning for submit buttons on the order confirmation page
- Multiple strategies for finding and clicking the submit button
- Page scanning helpers used during submission
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
    ElementClickInterceptedException,
    WebDriverException,
)


class OrderSubmitter:
    """Handles finding and clicking the order submit button."""

    def __init__(self, driver, config):
        self.driver = driver
        self.config = config

    def scan_page_info(self):
        """Print current page URL and title for debugging."""
        logger.info("  📄 页面信息:")
        logger.info(f"    URL: {self.driver.current_url}")
        logger.info(f"    标题: {self.driver.title}")

    def scan_page_text(self):
        """Print the first 20 lines of the page body text for debugging."""
        logger.info("  🔍 扫描页面文本内容...")
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            if body_text:
                lines = body_text.split('\n')[:20]
                logger.info(f"    页面文本内容（前20行）:")
                for line in lines:
                    line = line.strip()
                    if line:
                        logger.info(f"      {line}")
            else:
                logger.warning("    ⚠ 页面无文本内容")
        except (NoSuchElementException, WebDriverException) as e:
            logger.error(f"    扫描失败: {e}")

    def scan_elements(self, tag_name, label):
        """Scan elements of the specified tag type for debugging.

        Args:
            tag_name: HTML tag to scan (e.g. 'button', 'input')
            label: human-readable label for log output
        """
        logger.info(f"  🔍 扫描所有{label}...")
        try:
            elements = self.driver.find_elements(By.TAG_NAME, tag_name)
            if elements:
                logger.info(f"    找到 {len(elements)} 个{label}:")
                for idx, elem in enumerate(elements[:10]):
                    try:
                        if tag_name == "input":
                            elem_type = elem.get_attribute('type') or 'text'
                            elem_name = elem.get_attribute('name') or ''
                            elem_id = elem.get_attribute('id') or ''
                            elem_class = elem.get_attribute('class') or ''
                            logger.info(f"      [{idx}] type='{elem_type}' name='{elem_name}' id='{elem_id}' class='{elem_class}'")
                        elif tag_name == "button":
                            btn_text = elem.text.strip()
                            btn_class = elem.get_attribute('class') or ''
                            logger.info(f"      [{idx}] text='{btn_text}' class='{btn_class}'")
                    except WebDriverException:
                        pass
            else:
                logger.info(f"    未找到{label}")
        except WebDriverException as e:
            logger.error(f"    扫描失败: {e}")

    def scan_submit_buttons(self):
        """Scan and print candidate submit buttons for debugging."""
        logger.info("  🔍 扫描提交按钮...")
        try:
            submit_candidates = []

            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in all_buttons:
                try:
                    btn_text = btn.text.strip()
                    btn_class = btn.get_attribute('class') or ''
                    if any(keyword in btn_text for keyword in ['提交订单', '提交', '确认', '立即支付', '去支付', '支付']):
                        submit_candidates.append(('button', btn, btn_text, btn_class))
                        logger.info(f"    [button] text='{btn_text}' class='{btn_class}'")
                except WebDriverException:
                    pass

            for tag in ['div', 'span']:
                elements = self.driver.find_elements(By.TAG_NAME, tag)
                for elem in elements:
                    try:
                        elem_text = elem.text.strip()
                        if elem_text in ['立即提交', '提交订单', '提交', '确认']:
                            elem_class = elem.get_attribute('class') or ''
                            view_name = elem.get_attribute('view-name') or ''
                            submit_candidates.append((tag, elem, elem_text, elem_class, view_name))
                            logger.info(f"    [{tag}] text='{elem_text}' class='{elem_class}' view-name='{view_name}'")
                    except WebDriverException:
                        pass

            if not submit_candidates:
                logger.warning("    ⚠ 未找到明显的提交按钮")
        except WebDriverException as e:
            logger.error(f"    扫描失败: {e}")

    def try_submit_by_text(self, submit_button_texts):
        """Strategy 1-2: Find submit button by element text content.

        Args:
            submit_button_texts: ordered list of text strings to try

        Returns:
            bool: True if submit was triggered
        """
        for btn_text in submit_button_texts:
            for tag in ['button', 'div', 'span']:
                try:
                    xpath = f"//{tag}[contains(text(), {escape_xpath_string(btn_text)})]"
                    submit_btn = self.driver.find_element(By.XPATH, xpath)
                    logger.info(f"  ✓ 找到<{tag}>: {btn_text}")
                    submit_btn.click()
                    logger.info('***订单已提交***')
                    return True
                except (NoSuchElementException, ElementClickInterceptedException, WebDriverException):
                    continue

            try:
                xpath = f"//span[text()={escape_xpath_string(btn_text)}]"
                submit_btn = self.driver.find_element(By.XPATH, xpath)
                logger.info(f"  ✓ 找到<span>(精确匹配): {btn_text}")
                try:
                    parent = submit_btn.find_element(By.XPATH, '..')
                    parent.click()
                except (NoSuchElementException, ElementClickInterceptedException, WebDriverException):
                    submit_btn.click()
                logger.info('***订单已提交***')
                return True
            except (NoSuchElementException, ElementClickInterceptedException, WebDriverException):
                continue

        return False

    def try_submit_by_view_name(self):
        """Strategy 3: Find submit button by view-name attribute.

        Returns:
            bool: True if submit was triggered
        """
        try:
            xpath = "//div[@view-name='TextView']//span[contains(text(), '提交')]"
            submit_btn = self.driver.find_element(By.XPATH, xpath)
            logger.info(f"  ✓ 找到div[@view-name='TextView']")
            parent_div = submit_btn.find_element(By.XPATH, '..')
            parent_div.click()
            logger.info('***订单已提交***')
            return True
        except (NoSuchElementException, ElementClickInterceptedException, WebDriverException):
            return False

    def try_submit_by_class(self):
        """Strategy 4: Find submit button by CSS class name.

        Returns:
            bool: True if submit was triggered
        """
        submit_button_classes = [
            'submit-button',
            'submit-btn',
            'confirm-button',
            'pay-button',
            'bui-btn-contained',
        ]

        for class_name in submit_button_classes:
            try:
                xpath = f"//*[contains(@class, '{class_name}')]"
                submit_btn = self.driver.find_element(By.XPATH, xpath)
                logger.info(f"  ✓ 通过class找到按钮: {class_name}")
                submit_btn.click()
                logger.info('***订单已提交***')
                return True
            except (NoSuchElementException, ElementClickInterceptedException, WebDriverException):
                continue

        return False

    def try_submit_by_original_xpath(self):
        """Strategy 5: Use the original hard-coded XPath.

        Returns:
            bool: True if submit was triggered
        """
        try:
            submit_btn = self.driver.find_element(
                value='//*[@id="dmOrderSubmitBlock_DmOrderSubmitBlock"]/div[2]/div/div[2]/div[2]/div[2]',
                by=By.XPATH)
            logger.info("  ✓ 通过原有XPath找到按钮")
            submit_btn.click()
            logger.info('***订单已提交***')
            return True
        except (NoSuchElementException, ElementClickInterceptedException, WebDriverException):
            return False

    def submit_order(self):
        """Try all strategies in order to submit the order."""
        logger.info('***准备提交订单***')

        self.scan_submit_buttons()

        submit_button_texts = ['立即提交', '提交订单', '提交', '确认', '立即支付', '去支付', '支付']

        if (self.try_submit_by_text(submit_button_texts) or
                self.try_submit_by_view_name() or
                self.try_submit_by_class() or
                self.try_submit_by_original_xpath()):
            return

        logger.warning(f"  ⚠ 所有方法都失败，请手动点击提交按钮")
