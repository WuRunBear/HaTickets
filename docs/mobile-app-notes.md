# 安卓端 V2 版本介绍

> 当前实际使用请优先参考 [README.md](../README.md) 和 [quick-start.md](./quick-start.md)。

## 执行命令

无需启动额外服务，`adb devices` 能识别设备即可直接执行：

```bash
# 安全探测
./mobile/scripts/start_ticket_grabbing.sh --probe --yes

# 正式抢票
./mobile/scripts/start_ticket_grabbing.sh --yes
```

点击操作使用 UIAutomator2 直连设备的坐标手势，绕过元素交互检查：

```python
bot._click_coordinates(x, y)
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
