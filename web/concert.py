# -*- coding: UTF-8 -*-
"""
__Author__ = "WECENG"
__Version__ = "1.0.0"
__Description__ = ""
__Created__ = 2023/10/10 17:00

Concert — slim orchestrator that delegates to focused sub-modules.

Sub-modules:
  session_manager  — WebDriver lifecycle and cookie management
  ticket_selector  — Ticket/date/price/city/quantity selection
  user_selector    — Attendee selection strategies
  order_submitter  — Order submission strategies
"""

import os.path
import pickle
import time
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException,
    TimeoutException,
)
from check_environment import get_chromedriver_path

from session_manager import SessionManager
from ticket_selector import TicketSelector
from user_selector import UserSelector
from order_submitter import OrderSubmitter


class Concert:
    def __init__(self, config):
        self.config = config
        self.status = 0  # 状态,表示如今进行到何种程度
        self.login_method = 1  # {0:模拟登录,1:Cookie登录}自行选择登录方式

        # Driver setup is done here so tests can patch concert.get_chromedriver_path
        # and concert.webdriver.Chrome without needing to patch session_manager.*
        print("⏳ 正在检查 Chrome 环境...")
        try:
            chromedriver_path = get_chromedriver_path()
            print(f"✓ ChromeDriver 就绪: {chromedriver_path}\n")
        except RuntimeError as e:
            print(f"✗ 环境检查失败: {e}")
            print("\n建议运行: python damai/check_environment.py")
            exit(1)

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_experimental_option("excludeSwitches", ['enable-automation'])
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')

        from selenium.webdriver.chrome.service import Service
        service = Service(chromedriver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Sub-modules receive the ready driver
        self._session = SessionManager(self.driver, config)
        self._ticket_selector = TicketSelector(self.driver, config)
        self._user_selector = UserSelector(self.driver, config)
        self._order_submitter = OrderSubmitter(self.driver, config)

    # ===================================================================
    # Session / Auth
    # (implemented directly here so tests can patch concert.pickle,
    #  concert.os.path, and concert.time.sleep without needing to patch
    #  the session_manager module references)
    # ===================================================================

    def set_cookie(self):
        """
        :return: 写入cookie
        """
        self.driver.get(self.config.index_url)
        print("***请点击登录***\n")
        while self.driver.title.find('大麦网-全球演出赛事官方购票平台') != -1:
            sleep(1)
        print("***请扫码登录***\n")
        while self.driver.title != '大麦网-全球演出赛事官方购票平台-100%正品、先付先抢、在线选座！':
            sleep(1)
        print("***扫码成功***\n")

        # 将cookie写入damai_cookies.pkl文件中
        pickle.dump(self.driver.get_cookies(), open("damai_cookies.pkl", "wb"))
        print("***Cookie保存成功***")
        # 读取抢票目标页面
        self.driver.get(self.config.target_url)

    def get_cookie(self):
        """
        :return: 读取cookie
        """
        try:
            cookies = pickle.load(open("damai_cookies.pkl", "rb"))
            for cookie in cookies:
                cookie_dict = {
                    'domain': '.damai.cn',  # 域为大麦网的才为有效cookie
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                }
                self.driver.add_cookie(cookie_dict)
            print('***完成cookie加载***\n')
        except FileNotFoundError as e:
            print(f"Cookie 文件不存在: {e}")
        except (pickle.UnpicklingError, EOFError) as e:
            print(f"Cookie 文件损坏，无法加载: {e}")

    def login(self):
        """
        :return: 登录
        """
        if self.login_method == 0:
            self.driver.get(self.config.login_url)
            print('***开始登录***\n')
        elif self.login_method == 1:
            if not os.path.exists('damai_cookies.pkl'):
                # 没有cookie就获取
                self.set_cookie()
            else:
                self.driver.get(self.config.target_url)
                self.get_cookie()

    def finish(self):
        self.driver.quit()

    # ===================================================================
    # Navigation
    # ===================================================================

    def enter_concert(self):
        """:return: 打开浏览器"""
        print('***打开浏览器，进入大麦网***\n')
        self.login()
        self.status = 2
        print('***登录成功***')
        if self.is_element_exist('/html/body/div[2]/div[2]/div/div/div[3]/div[2]'):
            self.driver.find_element(value='/html/body/div[2]/div[2]/div/div/div[3]/div[2]', by=By.XPATH).click()

    def is_element_exist(self, element):
        """判断元素是否存在"""
        flag = True
        browser = self.driver
        try:
            browser.find_element(value=element, by=By.XPATH)
            return flag
        except NoSuchElementException:
            flag = False
            return flag

    # ===================================================================
    # Helper utilities
    # ===================================================================

    def _get_element_text_safe(self, locator, by=By.CLASS_NAME):
        """安全地获取元素文本"""
        try:
            elements = self.driver.find_elements(value=locator, by=by)
            return elements[0].text if elements else None
        except (StaleElementReferenceException, WebDriverException):
            return None

    def _click_element_safe(self, locator, by=By.CLASS_NAME):
        """安全地点击元素"""
        try:
            element = self.driver.find_element(value=locator, by=by)
            element.click()
            return True
        except (NoSuchElementException, ElementClickInterceptedException, StaleElementReferenceException):
            return False

    def _get_wait_time(self, short=False):
        """根据快速模式获取等待时间"""
        if short:
            return 0.1 if self.config.fast_mode else 0.2
        return 0.2 if self.config.fast_mode else 0.3

    def _is_order_confirmation_page(self):
        """检查是否为订单确认页"""
        title = self.driver.title
        if '订单确认页' in title or '确认购买' in title:
            return True
        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            return '支付方式' in page_text
        except (NoSuchElementException, WebDriverException):
            return False

    # ===================================================================
    # Ticket flow orchestration
    # ===================================================================

    def choose_ticket(self):
        """:return: 选票"""
        if self.status != 2:
            return

        print("*******************************\n")
        print("***开始在详情页选择***\n")

        is_mobile = 'm.damai.cn' in self.driver.current_url

        if is_mobile:
            print("检测到移动端页面\n")
            self.select_details_page_mobile()
        else:
            print("检测到PC端页面\n")
            self.select_details_page_pc()

        print("*******************************\n")
        print("***开始轮询检测预订按钮***\n")

        clicked_booking = False
        while not self._is_order_confirmation_page():
            if clicked_booking:
                if self._is_order_confirmation_page():
                    print('  ✓ 页面已跳转到订单确认页\n')
                    break
                elif '选座购买' in self.driver.title:
                    print('  ✓ 页面已跳转到选座购买页\n')
                    break
                else:
                    wait_time = 0.2 if self.config.fast_mode else 0.5
                    time.sleep(wait_time)
                    continue

            try:
                buy_button = self._get_element_text_safe('buy__button__text', By.CLASS_NAME)
                by_link = self._get_element_text_safe('buy-link', By.CLASS_NAME)

                if buy_button == "提交缺货登记":
                    self.status = 2
                    self.driver.get(self.config.target_url)
                    print('***抢票未开始，刷新等待开始***\n')
                    continue

                clickable_actions = [
                    ("立即预订", buy_button, 'buy__button__text'),
                    ("立即购买", buy_button, 'buy__button__text'),
                    ("缺货登记", buy_button, 'buy__button__text', lambda: self.config.if_listen),
                    ("选座购买", buy_button, 'buy__button__text'),
                ]

                action_taken = False
                for action in clickable_actions:
                    text, current_text, locator, *condition = action
                    if current_text == text and (not condition or condition[0]()):
                        print(f'✓ 检测到按钮: {text}')
                        self._click_element_safe(locator, By.CLASS_NAME)
                        self.status = 3
                        clicked_booking = True
                        print('  等待页面跳转...\n')
                        action_taken = True
                        break

                if not action_taken and by_link in ("不，立即预订", "不，立即购买"):
                    print(f'✓ 检测到链接: {by_link}')
                    self._click_element_safe('buy-link', By.CLASS_NAME)
                    self.status = 3
                    clicked_booking = True
                    print('  等待页面跳转...\n')

            except (NoSuchElementException, StaleElementReferenceException, WebDriverException) as e:
                print(f"轮询检测按钮时出现异常: {e}")

            if '选座购买' in self.driver.title:
                self.choice_seat()
            elif self._is_order_confirmation_page():
                print('***进入订单确认页***\n')
                self.commit_order()
            else:
                print('***抢票未开始，刷新等待开始***\n')
                refresh_wait = 0.3 if self.config.fast_mode else 1
                time.sleep(refresh_wait)
                self.driver.refresh()

    def choice_seat(self):
        while self.driver.title == '选座购买':
            while self.is_element_exist('//*[@id="app"]/div[2]/div[2]/div[1]/div[2]/img'):
                print('请快速选择您的座位！！！')
            while self.is_element_exist('//*[@id="app"]/div[2]/div[2]/div[2]/div'):
                self.driver.find_element(value='//*[@id="app"]/div[2]/div[2]/div[2]/button', by=By.XPATH).click()

    def choice_order(self):
        """选择订单：包括场次、票档、人数"""
        self.driver.find_element(value='buy__button__text', by=By.CLASS_NAME).click()
        time.sleep(0.2)
        print("***选定场次***\n")

        if self.driver.find_elements(value='sku-times-card', by=By.CLASS_NAME) and self.config.dates:
            order_name_element_list = self.driver.find_element(
                value='sku-times-card', by=By.CLASS_NAME
            ).find_elements(value='bui-dm-sku-card-item', by=By.CLASS_NAME)
            if self._select_option_by_config(self.config.dates, order_name_element_list):
                print("  ✓ 场次选择成功")

        print("***选定票档***\n")
        if self.driver.find_elements(value='sku-tickets-card', by=By.CLASS_NAME) and self.config.prices:
            sku_name_element_list = self.driver.find_elements(value='item-content', by=By.CLASS_NAME)
            if self._select_option_by_config(self.config.prices, sku_name_element_list, ['缺', '售罄']):
                print("  ✓ 票档选择成功")

        print("***选定人数***\n")
        if self.driver.find_elements(value='bui-dm-sku-counter', by=By.CLASS_NAME):
            for i in range(len(self.config.users) - 1):
                self.driver.execute_script(
                    'document.getElementsByClassName("number-edit-bg")[1].click();')
            print(f"  ✓ 已选择 {len(self.config.users)} 张票")

        self.driver.find_element(value='bui-btn-contained', by=By.CLASS_NAME).click()

    # ===================================================================
    # Order confirmation — forward to sub-modules
    # ===================================================================

    def commit_order(self):
        """提交订单"""
        if self.status not in [3]:
            return

        print('***开始确认订单***\n')

        if not self.config.fast_mode:
            print('⏳ 等待订单确认页加载...\n')
            time.sleep(self.config.page_load_delay)
        else:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(max(1, self.config.page_load_delay / 2))
            except TimeoutException:
                time.sleep(self.config.page_load_delay)

        ticket_count = len(self.config.users)

        if not self.config.fast_mode:
            print(f"  购票数量: {ticket_count} 张（已在详情页选择）\n")
            print(f"  配置观众: {self.config.users}")
            print(f"  需要选择观众: {ticket_count} 个\n")

        users_to_select = self.config.users[:ticket_count]

        try:
            if not self.config.fast_mode:
                self._scan_page_info()
                self._scan_page_text()
                self._scan_elements("input", "输入框")
                self._scan_elements("button", "按钮")

            user_found = self._scan_user_elements(retry_count=5, retry_interval=0.5)
            self._select_users(ticket_count, users_to_select)

        except Exception as e:
            # Broad catch is intentional: user-selection can fail for many reasons
            # (DOM changes, unexpected page state, network issues). We log and
            # continue so the user can manually complete the selection.
            print("***购票人信息选择过程出现异常***\n")
            print(f"  异常信息: {e}")
            print("\n  建议:")
            print("    1. 在浏览器中手动选择购票人")
            if not self.config.fast_mode:
                print("    2. 查看上方扫描输出，确认用户名格式")
            print("    3. 检查用户名是否与配置一致")
            print(f"    4. 确保选择 {ticket_count} 个观众\n")

        if self.config.fast_mode:
            time.sleep(0.1)
        else:
            time.sleep(0.5)

        if self.config.if_commit_order:
            self._submit_order()

    # ===================================================================
    # Details page — forward to TicketSelector
    # ===================================================================

    def select_details_page_mobile(self):
        """在移动端详情页完成所有选择：城市、场次、票价、数量"""
        if not self.config.fast_mode:
            print("⏳ 开始在移动端详情页进行选择...\n")

        success = True

        if self.config.city and success:
            if not self.config.fast_mode:
                print("***选择城市***")
                print(f"  目标城市: {self.config.city}")
            success = self.select_city_on_page()
            if not self.config.fast_mode:
                print()

        if self.config.dates and success:
            if not self.config.fast_mode:
                print("***选择场次***")
                print(f"  目标场次: {self.config.dates}")
            success = self.select_date_on_page()
            if not self.config.fast_mode:
                print()

        if self.config.prices and success:
            if not self.config.fast_mode:
                print("***选择票价***")
                print(f"  目标票价: {self.config.prices}")
            success = self.select_price_on_page()
            if not self.config.fast_mode:
                print()

        if len(self.config.users) > 1 and success:
            if not self.config.fast_mode:
                print("***选择购票数量***")
                print(f"  目标数量: {len(self.config.users)} 张")
            self.select_quantity_on_page()
            if not self.config.fast_mode:
                print()

        print("***详情页选择完成***\n")

    def select_details_page_pc(self):
        """在PC端详情页完成所有选择：城市、场次、票价、数量"""
        if not self.config.fast_mode:
            print("⏳ 开始在PC端详情页进行选择...\n")
            print("***扫描页面元素***\n")
            self.scan_page_elements()
            print()

        success = True

        if self.config.city and success:
            if not self.config.fast_mode:
                print("***选择城市***")
                print(f"  目标城市: {self.config.city}")
            success = self.select_city_on_page_pc()
            if not self.config.fast_mode:
                print()

        if self.config.dates and success:
            if not self.config.fast_mode:
                print("***选择场次***")
                print(f"  目标场次: {self.config.dates}")
            success = self.select_date_on_page_pc()
            if not self.config.fast_mode:
                print()

        if self.config.prices and success:
            if not self.config.fast_mode:
                print("***选择票价***")
                print(f"  目标票价: {self.config.prices}")
            success = self.select_price_on_page_pc()
            if not self.config.fast_mode:
                print()

        if len(self.config.users) > 1 and success:
            if not self.config.fast_mode:
                print("***选择购票数量***")
                print(f"  目标数量: {len(self.config.users)} 张")
            self._select_quantity_on_page(platform="PC端")
            if not self.config.fast_mode:
                print()

        print("***详情页选择完成***\n")

    # ===================================================================
    # Ticket selection methods — forward to TicketSelector
    # ===================================================================

    def _select_option_by_config(self, config_list, element_list, skip_keywords=None):
        """根据配置列表选择选项 — delegates to TicketSelector"""
        return self._ticket_selector.select_option_by_config(config_list, element_list, skip_keywords)

    def _find_and_click_element(self, search_text, max_results=10, skip_keywords=None, print_results=True):
        """查找并点击包含指定文本的元素 — delegates to TicketSelector"""
        return self._ticket_selector.find_and_click_element(search_text, max_results, skip_keywords, print_results)

    def _click_element_by_text(self, text_content, tag_names=None, exact_match=False):
        """通过文本内容点击元素 — delegates to TicketSelector"""
        return self._ticket_selector.click_element_by_text(text_content, tag_names, exact_match)

    def select_city_on_page_pc(self):
        """在PC端详情页选择城市"""
        return self._ticket_selector.select_city_on_page_pc()

    def select_date_on_page_pc(self):
        """在PC端详情页选择场次"""
        return self._ticket_selector.select_date_on_page_pc()

    def select_price_on_page_pc(self):
        """在PC端详情页选择票价"""
        return self._ticket_selector.select_price_on_page_pc()

    def select_quantity_on_page_pc(self):
        """在PC端详情页选择数量"""
        return self._ticket_selector.select_quantity_on_page_pc()

    def select_city_on_page(self):
        """在页面选择城市（移动端）"""
        return self._ticket_selector.select_city_on_page()

    def select_date_on_page(self):
        """在页面选择场次（移动端）"""
        return self._ticket_selector.select_date_on_page()

    def select_price_on_page(self):
        """在页面选择票价（移动端）"""
        return self._ticket_selector.select_price_on_page()

    def select_quantity_on_page(self):
        """在页面选择数量（移动端）"""
        return self._ticket_selector.select_quantity_on_page(platform="移动端")

    def _select_quantity_on_page(self, platform="移动端"):
        """在详情页选择数量（PC端和移动端通用）"""
        return self._ticket_selector.select_quantity_on_page(platform=platform)

    def _try_select_quantity_by_buttons(self, target_count):
        """通过点击 + 按钮选择数量"""
        return self._ticket_selector.try_select_quantity_by_buttons(target_count)

    def _click_plus_buttons(self, plus_btns, target_count):
        """点击 + 按钮增加数量"""
        return self._ticket_selector.click_plus_buttons(plus_btns, target_count)

    def _get_quantity_input_value(self):
        """获取数量输入框的值"""
        return self._ticket_selector.get_quantity_input_value()

    def _try_set_quantity_directly(self, target_count):
        """直接设置输入框的值"""
        return self._ticket_selector.try_set_quantity_directly(target_count)

    def _scan_elements_by_class(self, class_names, label):
        """扫描指定class的元素"""
        return self._ticket_selector.scan_elements_by_class(class_names, label)

    def scan_page_elements(self):
        """扫描页面元素，用于调试"""
        return self._ticket_selector.scan_page_elements()

    # ===================================================================
    # User selection methods — forward to UserSelector
    # ===================================================================

    def _scan_user_elements(self, retry_count=5, retry_interval=0.5):
        """扫描购票人相关元素"""
        return self._user_selector.scan_user_elements(retry_count, retry_interval)

    def _try_select_user_method1(self, user, users_to_select, user_selected):
        """方法1: 查找并点击包含用户名的div"""
        return self._user_selector.try_select_user_method1(user, users_to_select, user_selected)

    def _try_select_user_method2(self, user, users_to_select, user_selected):
        """方法2: 通过复选框和label选择"""
        return self._user_selector.try_select_user_method2(user, users_to_select, user_selected)

    def _try_select_user_method3(self, user, users_to_select, user_selected):
        """方法3: 点击包含用户名的元素"""
        return self._user_selector.try_select_user_method3(user, users_to_select, user_selected)

    def _try_select_user_method4(self, user, users_to_select, user_selected):
        """方法4: 使用JavaScript查找并点击"""
        return self._user_selector.try_select_user_method4(user, users_to_select, user_selected)

    def _select_users(self, ticket_count, users_to_select):
        """选择观演人员"""
        return self._user_selector.select_users(ticket_count, users_to_select)

    # ===================================================================
    # Order submission methods — forward to OrderSubmitter
    # ===================================================================

    def _scan_page_info(self):
        """扫描页面基本信息用于调试"""
        return self._order_submitter.scan_page_info()

    def _scan_page_text(self):
        """扫描页面文本内容"""
        return self._order_submitter.scan_page_text()

    def _scan_elements(self, tag_name, label):
        """扫描指定类型的元素"""
        return self._order_submitter.scan_elements(tag_name, label)

    def _scan_submit_buttons(self):
        """扫描提交按钮"""
        return self._order_submitter.scan_submit_buttons()

    def _try_submit_by_text(self, submit_button_texts):
        """方法1-2: 通过元素文本查找"""
        return self._order_submitter.try_submit_by_text(submit_button_texts)

    def _try_submit_by_view_name(self):
        """方法3: 通过view-name属性查找"""
        return self._order_submitter.try_submit_by_view_name()

    def _try_submit_by_class(self):
        """方法4: 通过class查找"""
        return self._order_submitter.try_submit_by_class()

    def _try_submit_by_original_xpath(self):
        """方法5: 原有的XPath"""
        return self._order_submitter.try_submit_by_original_xpath()

    def _submit_order(self):
        """提交订单"""
        return self._order_submitter.submit_order()
