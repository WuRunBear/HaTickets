# Web 端抢票逻辑 (Selenium)

> 源码目录: `damai/`

## 技术栈

- Python 3.8+
- Selenium 4.18.1 + ChromeDriver
- `chromedriver-autoinstaller` 自动管理驱动版本

## 模块结构

| 文件 | 职责 |
|------|------|
| `damai.py` | 入口：校验配置 → 加载 Config → 编排 Concert |
| `concert.py` | 核心自动化：浏览器生命周期、选票、下单（~1560 行） |
| `config.py` | 配置容器类 |
| `check_environment.py` | 环境校验 + ChromeDriver 自动安装 |
| `quick_diagnosis.py` | 轻量级 Chrome/ChromeDriver 版本检查 |
| `config.json` | 用户配置文件 |

## 配置项 (`config.json`)

```json
{
    "index_url": "https://www.damai.cn/",
    "login_url": "https://passport.damai.cn/login",
    "target_url": "目标演出页面URL",
    "users": ["观众1姓名", "观众2姓名"],
    "city": "城市名称",
    "dates": ["场次日期1", "场次日期2"],
    "prices": ["票面价格1", "票面价格2"],
    "if_listen": true,
    "if_commit_order": true,
    "max_retries": 1000,
    "fast_mode": true,
    "page_load_delay": 2
}
```

## 主流程

```
damai.py::grab()
  ├── check_config_file()      # 验证 config.json
  ├── load_config()            # 解析为 Config 对象
  ├── Concert.__init__()       # 初始化 Selenium + ChromeDriver 自动检测
  ├── concert.enter_concert()  # 登录
  ├── concert.choose_ticket()  # 选票主循环
  └── time.sleep(300)          # 页面保持 5 分钟
```

## 详细流程

### 1. 初始化与登录

**ChromeDriver 管理**:
- `check_environment.py::get_chromedriver_path()` 检测本地 Chrome 版本
- 如果 ChromeDriver 版本不匹配，通过 `chromedriver-autoinstaller` 自动安装

**反自动化检测**:
- 禁用 `enable-automation` 开关
- 禁用 `AutomationControlled` Blink 特性

**登录策略** (`concert.login()`):
- 优先加载 `damai_cookies.pkl`（pickle 序列化的 Cookie）
- 不存在则打开浏览器让用户手动扫码，登录后保存 Cookie

### 2. 详情页选择

`choose_ticket()` 先判断是 PC 端还是移动端页面，然后调用对应的选择方法。

**选择顺序**: 城市 → 场次 → 票价 → 数量

每一步都有**多层容错**定位策略：
1. 先用 CSS class 定位（`bui-dm-tour`、`sku-times-card`、`item-content` 等）
2. 失败后用 XPath 文本搜索 (`_find_and_click_element()`)

**选项匹配** (`_select_option_by_config()`):
- 遍历配置中的目标值，逐一与页面元素文本做模糊匹配
- 自动跳过包含 "无票"、"售罄"、"缺货" 的选项

**数量选择** (`_select_quantity_on_page()`):
- 方案1: 查找 `+` 按钮，JS click (target_count - 1) 次
- 方案2: JS 直接设置 input 值并触发 `input`/`change` 事件

### 3. 轮询抢票按钮

`choose_ticket()` 的核心是一个**无限循环**，持续检测购票按钮状态：

| 检测到的文本 | 行为 |
|---|---|
| `提交缺货登记` | 未开售，刷新页面继续等待 |
| `立即预订` / `立即购买` | 点击，进入下一步 |
| `选座购买` | 点击，跳转选座页 |
| `缺货登记` (且 `if_listen=true`) | 点击（监听模式） |

- 快速模式刷新间隔 0.3s，普通模式 1s
- 点击后设置 `status=3`，等待页面跳转

### 4. 选座 (可选)

`choice_seat()`: 页面跳转到"选座购买"时触发
- 提示用户手动选座
- 等待座位图元素消失（说明已选座）
- 自动点击"确认选座"按钮

### 5. 确认订单

`commit_order()`: 这是最复杂的环节

**等待加载**:
- 快速模式: WebDriverWait + 半量 page_load_delay
- 普通模式: 固定 sleep(page_load_delay)

**选择购票人** (`_select_users()`): 对每个用户依次尝试 4 种方法

| 方法 | 策略 |
|---|---|
| 方法1 | 找包含用户名的 `<div>`，在附近查找复选框/iconfont 图标点击 |
| 方法2 | 通过 `<label>` for 属性关联 `<input type="checkbox">` |
| 方法3 | 直接点击包含用户名文本的元素 |
| 方法4 | JS 精确查找 div + 遍历兄弟元素查找 iconfont 图标 |

**提交订单** (`_submit_order()`): 依次尝试 5 种方法

| 方法 | 策略 |
|---|---|
| 方法1-2 | 按文本查找 button/div/span（"立即提交"、"提交订单"等） |
| 方法3 | 通过 `view-name='TextView'` 属性定位 |
| 方法4 | 通过 class 查找（`submit-button`、`bui-btn-contained` 等） |
| 方法5 | 硬编码 XPath |

### 状态机

`Concert.status` 控制流程推进：

```
0 (初始) → 2 (登录成功) → 3 (开始选票)
```

- `choose_ticket()` 要求 `status == 2` 才执行
- `commit_order()` 要求 `status == 3` 才执行

### fast_mode 的影响

| 维度 | 普通模式 | 快速模式 |
|---|---|---|
| 等待时间 | 0.3~1s | 0.1~0.3s |
| 页面扫描 | 输出所有元素 | 跳过 |
| 调试日志 | 详细 | 精简 |
| 刷新间隔 | 1s | 0.3s |
| 页面加载等待 | page_load_delay | WebDriverWait + 半量 delay |

## 设计特点

1. **极度防御性定位**: 每个操作都有 3-5 种备选定位策略，应对大麦前端频繁改版
2. **Cookie 持久化**: 避免每次重新登录
3. **自动环境管理**: ChromeDriver 版本自动检测和安装
4. **双平台适配**: 同时支持 PC 端和移动端大麦网页
