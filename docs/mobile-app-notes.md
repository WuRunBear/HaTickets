# 安卓端 V2 版本介绍

> **注意**：当前默认驱动已切换为 UIAutomator2 (u2) 直连模式，无需 Appium Server。
> 下文中关于 Appium 的内容为历史实现参考。当前实际使用请优先参考 [README.md](../README.md) 和 [quick-start.md](./quick-start.md)。

## 执行命令

### 驱动模式

**u2 直连（默认，推荐）**：
```bash
# 无需启动任何服务，直接执行
./mobile/scripts/start_ticket_grabbing.sh --probe --yes
```

**Appium 回退模式**（`config.jsonc` 中 `driver_backend: "appium"`）：
```bash
appium --address 0.0.0.0 --port 4723 --relaxed-security
```

Appium 模式下可以用 `mobile: clickGesture` 直接原生点击（u2 模式使用 `d.click()` 实现同等效果）：

```python
# Appium 模式
driver.execute_script('mobile: clickGesture', {'elementId': target.id})
# u2 模式（自动适配，无需手动区分）
bot._click_coordinates(x, y)
```

### 执行抢票任务

```bash
./mobile/scripts/start_ticket_grabbing.sh --yes
```


## 只处理了抢票的，预约的暂未考虑

## 功能
- 大麦的大部分票**只能在APP端购买**，所以只运行了安卓侧的实现并进行修改
- APP更新，**界面信息的票价的Text是空串""**，无法再使用之前的方案去找按钮click，V2是通过分析页面信息，使用索引的方式获取，缺点是需要预先手动写进去，不知道后续有没有什么新的方法获取
- 增加重试机制

## 优化：
- 考虑到界面可以先点到搜索列表，移除了键入搜索和点击搜索按钮的步骤
- 增加了一些加速的配置capabilities，以及一些性能优化的配置
- 优化了多人勾选的逻辑，收集坐标信息，几乎一次性全部点击
- 使用`WebDriverWait`替代`driver.implicitly_wait(5)`，大大提升效率
- 优化了`click()`的方式，使用
```python
driver.execute_script("mobile: clickGesture", {
                "x": x,
                "y": y,
                "duration": 50  # 极短点击时间
            })
```
- 优化显示逻辑，展示执行的进度

## 展望
- 实现预约功能
