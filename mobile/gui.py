import json
import logging
import sys
import threading
import traceback
from pathlib import Path
from queue import Empty, Queue


def _repo_root():
    return Path(__file__).resolve().parents[1]


def _mobile_dir():
    return _repo_root() / "mobile"


def _default_config_path():
    mobile_dir = _mobile_dir()
    for name in ("config.jsonc", "config.local.jsonc"):
        candidate = mobile_dir / name
        if candidate.exists():
            return candidate
    return mobile_dir / "config.jsonc"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class _QueueLogHandler(logging.Handler):
    def __init__(self, queue: Queue, level=logging.INFO):
        super().__init__(level=level)
        self._queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self._queue.put(msg + "\n")


class _StreamToQueue:
    def __init__(self, queue: Queue, prefix: str):
        self._queue = queue
        self._prefix = prefix

    def write(self, text):
        if not text:
            return 0
        self._queue.put(self._prefix + text)
        return len(text)

    def flush(self):
        return None


def _install_log_handler(handler: logging.Handler):
    installed = []
    for name in list(logging.root.manager.loggerDict.keys()):
        obj = logging.root.manager.loggerDict.get(name)
        if isinstance(obj, logging.Logger):
            logger = obj
        else:
            logger = logging.getLogger(name)
        if handler not in logger.handlers:
            logger.addHandler(handler)
            installed.append(logger.name)
    if handler not in logging.getLogger().handlers:
        logging.getLogger().addHandler(handler)
        installed.append("")
    return installed


def _remove_log_handler(handler: logging.Handler, installed_logger_names):
    for name in installed_logger_names:
        logger = logging.getLogger(name)
        try:
            logger.removeHandler(handler)
        except Exception:
            pass


def run_gui(config_path=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    try:
        from mobile.config import (
            _strip_jsonc_comments,
            runtime_mode_flags_from_key,
            runtime_mode_key_from_dict,
        )
    except ImportError:
        from config import (
            _strip_jsonc_comments,
            runtime_mode_flags_from_key,
            runtime_mode_key_from_dict,
        )

    root = tk.Tk()
    root.title("HaTickets 配置与运行模式")
    root.geometry("980x720")

    path_var = tk.StringVar(
        value=str(Path(config_path).expanduser()) if config_path else str(_default_config_path())
    )
    status_var = tk.StringVar(value="就绪")
    log_queue = Queue()

    mode_labels = {
        "probe": "安全探测（停在\"立即购票\"前）",
        "validation": "开发验证（不提交订单）",
        "submit": "正式抢票（会提交订单）",
    }
    mode_label_to_key = {v: k for k, v in mode_labels.items()}
    mode_var = tk.StringVar(value=mode_labels["probe"])

    var_serial = tk.StringVar(value="")
    var_app_package = tk.StringVar(value="cn.damai")
    var_app_activity = tk.StringVar(value=".launcher.splash.SplashMainActivity")
    var_item_url = tk.StringVar(value="")
    var_keyword = tk.StringVar(value="")
    var_users = tk.StringVar(value="")
    var_city = tk.StringVar(value="")
    var_date = tk.StringVar(value="")
    var_price = tk.StringVar(value="")
    var_price_index = tk.StringVar(value="0")
    var_auto_navigate = tk.BooleanVar(value=True)
    var_rush_mode = tk.BooleanVar(value=False)
    var_sell_start_time = tk.StringVar(value="")
    var_countdown_lead_ms = tk.StringVar(value="3000")
    var_wait_cta_ready_timeout_ms = tk.StringVar(value="0")
    var_fast_retry_count = tk.StringVar(value="8")
    var_fast_retry_interval_ms = tk.StringVar(value="120")
    var_target_title = tk.StringVar(value="")
    var_target_venue = tk.StringVar(value="")

    header = ttk.Frame(root, padding=10)
    header.pack(fill="x")

    ttk.Label(header, text="配置文件路径").grid(row=0, column=0, sticky="w")
    path_entry = ttk.Entry(header, textvariable=path_var)
    path_entry.grid(row=0, column=1, sticky="ew", padx=(6, 6))
    header.columnconfigure(1, weight=1)

    def browse():
        initial = Path(path_var.get()).expanduser()
        if initial.is_file():
            initial_dir = str(initial.parent)
        else:
            initial_dir = str(_mobile_dir())
        selected = filedialog.askopenfilename(
            title="选择配置文件",
            initialdir=initial_dir,
            filetypes=[("JSONC/JSON", "*.jsonc *.json"), ("All files", "*.*")],
        )
        if selected:
            path_var.set(selected)
            load_from_path()

    ttk.Button(header, text="选择", command=browse).grid(row=0, column=2, padx=(0, 8))

    btn_frame = ttk.Frame(header)
    btn_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0))

    def _get_path() -> Path:
        return Path(path_var.get()).expanduser()

    def _ensure_template_if_missing(path: Path) -> None:
        if path.exists():
            return
        template = _mobile_dir() / "config.example.jsonc"
        if not template.exists():
            raise FileNotFoundError(f"配置模板未找到: {template}")
        _write_text(path, _read_text(template))

    def _parse_int(value: str, field_name: str):
        text = (value or "").strip()
        if text == "":
            raise ValueError(f"{field_name} 不能为空")
        try:
            parsed = int(text)
        except Exception:
            raise ValueError(f"{field_name} 必须是整数")
        return parsed

    def _optional_str(value: str):
        text = (value or "").strip()
        return text if text else None

    def _get_mode_key():
        return mode_label_to_key.get(mode_var.get(), "probe")

    def _build_config_dict_from_form():
        users_raw = (var_users.get() or "").strip()
        users = [x.strip() for x in users_raw.replace("，", ",").split(",") if x.strip()]
        if not users:
            raise ValueError("users 不能为空")

        keyword = (var_keyword.get() or "").strip()
        if not keyword:
            raise ValueError("keyword 不能为空")

        mode_key = _get_mode_key()
        probe_only, if_commit_order = runtime_mode_flags_from_key(mode_key)

        config_dict = {
            "serial": _optional_str(var_serial.get()),
            "app_package": (var_app_package.get() or "").strip() or "cn.damai",
            "app_activity": (var_app_activity.get() or "").strip()
            or ".launcher.splash.SplashMainActivity",
            "item_url": _optional_str(var_item_url.get()),
            "keyword": keyword,
            "target_title": _optional_str(var_target_title.get()),
            "target_venue": _optional_str(var_target_venue.get()),
            "users": users,
            "city": (var_city.get() or "").strip(),
            "date": (var_date.get() or "").strip(),
            "price": (var_price.get() or "").strip(),
            "price_index": _parse_int(var_price_index.get(), "price_index"),
            "if_commit_order": if_commit_order,
            "probe_only": probe_only,
            "auto_navigate": bool(var_auto_navigate.get()),
            "sell_start_time": _optional_str(var_sell_start_time.get()),
            "countdown_lead_ms": _parse_int(var_countdown_lead_ms.get(), "countdown_lead_ms"),
            "wait_cta_ready_timeout_ms": _parse_int(
                var_wait_cta_ready_timeout_ms.get(), "wait_cta_ready_timeout_ms"
            ),
            "fast_retry_count": _parse_int(var_fast_retry_count.get(), "fast_retry_count"),
            "fast_retry_interval_ms": _parse_int(
                var_fast_retry_interval_ms.get(), "fast_retry_interval_ms"
            ),
            "rush_mode": bool(var_rush_mode.get()),
        }

        if not config_dict["city"]:
            raise ValueError("city 不能为空")
        if not config_dict["date"]:
            raise ValueError("date 不能为空")
        if not config_dict["price"]:
            raise ValueError("price 不能为空")

        return {k: v for k, v in config_dict.items() if v is not None}

    def _load_config_into_form(cfg: dict):
        var_serial.set("" if cfg.get("serial") is None else str(cfg.get("serial")))
        var_app_package.set(cfg.get("app_package") or "cn.damai")
        var_app_activity.set(
            cfg.get("app_activity") or ".launcher.splash.SplashMainActivity"
        )
        var_item_url.set("" if cfg.get("item_url") is None else str(cfg.get("item_url")))
        var_keyword.set(cfg.get("keyword") or "")
        users = cfg.get("users") or []
        if isinstance(users, list):
            var_users.set(",".join([str(x) for x in users if str(x).strip()]))
        else:
            var_users.set(str(users))
        var_city.set(cfg.get("city") or "")
        var_date.set(cfg.get("date") or "")
        var_price.set(cfg.get("price") or "")
        var_price_index.set(str(cfg.get("price_index", 0)))
        var_auto_navigate.set(bool(cfg.get("auto_navigate", True)))
        var_rush_mode.set(bool(cfg.get("rush_mode", False)))
        var_sell_start_time.set("" if cfg.get("sell_start_time") is None else str(cfg.get("sell_start_time")))
        var_countdown_lead_ms.set(str(cfg.get("countdown_lead_ms", 3000)))
        var_wait_cta_ready_timeout_ms.set(str(cfg.get("wait_cta_ready_timeout_ms", 0)))
        var_fast_retry_count.set(str(cfg.get("fast_retry_count", 8)))
        var_fast_retry_interval_ms.set(str(cfg.get("fast_retry_interval_ms", 120)))
        var_target_title.set("" if cfg.get("target_title") is None else str(cfg.get("target_title")))
        var_target_venue.set("" if cfg.get("target_venue") is None else str(cfg.get("target_venue")))

    def load_from_path():
        path = _get_path()
        try:
            _ensure_template_if_missing(path)
            text = _read_text(path)
            cfg = json.loads(_strip_jsonc_comments(text))
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))
            status_var.set("读取失败")
            return False

        try:
            mode_key = runtime_mode_key_from_dict(cfg)
            mode_var.set(mode_labels[mode_key])
        except Exception:
            pass
        try:
            _load_config_into_form(cfg)
        except Exception:
            pass

        status_var.set("已载入")
        return True

    def save_to_path():
        path = _get_path()
        try:
            cfg = _build_config_dict_from_form()
            _write_text(path, json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            status_var.set("保存失败")
            return False
        status_var.set("已保存")
        return True

    def apply_mode_and_save():
        if not save_to_path():
            return False
        mode_key = _get_mode_key()
        status_var.set(f"已应用模式：{mode_labels[mode_key]}")
        return True

    left_actions = ttk.Frame(btn_frame)
    left_actions.pack(side="left")
    center_mode = ttk.Frame(btn_frame)
    center_mode.pack(side="left", expand=True)
    right_actions = ttk.Frame(btn_frame)
    right_actions.pack(side="right")

    btn_load = ttk.Button(left_actions, text="载入", command=load_from_path)
    btn_save = ttk.Button(left_actions, text="保存", command=save_to_path)
    btn_apply = ttk.Button(left_actions, text="应用模式并保存", command=apply_mode_and_save)

    btn_load.pack(side="left", padx=(0, 6))
    btn_save.pack(side="left", padx=(0, 6))
    btn_apply.pack(side="left", padx=(0, 6))

    ttk.Label(center_mode, text="运行模式").pack(side="left", padx=(0, 6))
    mode_combo = ttk.Combobox(
        center_mode,
        textvariable=mode_var,
        values=[mode_labels["probe"], mode_labels["validation"], mode_labels["submit"]],
        state="readonly",
        width=14,
    )
    mode_combo.pack(side="left")

    run_btn = ttk.Button(right_actions, text="启动", command=lambda: None)
    stop_btn = ttk.Button(right_actions, text="停止", state="disabled", command=lambda: None)
    btn_clear_log = ttk.Button(right_actions, text="清空日志", command=lambda: None)
    ttk.Label(right_actions, textvariable=status_var).pack(side="right", padx=(12, 0))

    run_btn.pack(side="left", padx=(0, 6))
    stop_btn.pack(side="left", padx=(0, 6))
    btn_clear_log.pack(side="left", padx=(12, 0))

    paned = ttk.Panedwindow(root, orient="vertical")
    paned.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    form_frame = ttk.Frame(paned)
    log_frame = ttk.Frame(paned)
    paned.add(form_frame, weight=3)
    paned.add(log_frame, weight=1)

    form = ttk.Frame(form_frame, padding=10)
    form.pack(fill="both", expand=True)

    def _add_row(row, label, widget):
        ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=4)
        widget.grid(row=row, column=1, sticky="ew", pady=4)

    form.columnconfigure(1, weight=1)

    row = 0
    _add_row(row, "设备序列号（可空）", ttk.Entry(form, textvariable=var_serial))
    row += 1
    _add_row(row, "演出链接（可空）", ttk.Entry(form, textvariable=var_item_url))
    row += 1
    _add_row(row, "搜索关键词", ttk.Entry(form, textvariable=var_keyword))
    row += 1
    _add_row(row, "观演人姓名（逗号分隔）", ttk.Entry(form, textvariable=var_users))
    row += 1
    _add_row(row, "城市", ttk.Entry(form, textvariable=var_city))
    row += 1
    _add_row(row, "场次日期", ttk.Entry(form, textvariable=var_date))
    row += 1
    _add_row(row, "票档文本", ttk.Entry(form, textvariable=var_price))
    row += 1
    _add_row(row, "票档索引（从 0 开始）", ttk.Entry(form, textvariable=var_price_index))
    row += 1

    chk_row = ttk.Frame(form)
    ttk.Checkbutton(chk_row, text="自动导航", variable=var_auto_navigate).pack(side="left", padx=(0, 16))
    ttk.Checkbutton(chk_row, text="极速模式", variable=var_rush_mode).pack(side="left")
    _add_row(row, "功能开关", chk_row)
    row += 1

    _add_row(row, "开抢时间（可空，ISO）", ttk.Entry(form, textvariable=var_sell_start_time))
    row += 1
    _add_row(row, "开抢提前量（毫秒）", ttk.Entry(form, textvariable=var_countdown_lead_ms))
    row += 1
    _add_row(row, "等待按钮就绪（毫秒）", ttk.Entry(form, textvariable=var_wait_cta_ready_timeout_ms))
    row += 1
    _add_row(row, "快速重试次数", ttk.Entry(form, textvariable=var_fast_retry_count))
    row += 1
    _add_row(row, "快速重试间隔（毫秒）", ttk.Entry(form, textvariable=var_fast_retry_interval_ms))
    row += 1
    _add_row(row, "目标标题（可空）", ttk.Entry(form, textvariable=var_target_title))
    row += 1
    _add_row(row, "目标场馆（可空）", ttk.Entry(form, textvariable=var_target_venue))
    row += 1

    log_view = ScrolledText(log_frame, height=12, undo=False)
    log_view.pack(fill="both", expand=True)
    log_view.configure(state="disabled")

    def _append_log(text: str):
        if not text:
            return
        log_view.configure(state="normal")
        log_view.insert("end", text)
        log_view.see("end")
        log_view.configure(state="disabled")

    def _poll_logs():
        appended = 0
        while True:
            try:
                item = log_queue.get_nowait()
            except Empty:
                break
            _append_log(item)
            appended += 1
            if appended >= 200:
                break
        root.after(80, _poll_logs)

    cancel_event = threading.Event()
    bot_ref = {"bot": None}
    bot_ref_lock = threading.Lock()

    def run_bot():
        path = _get_path()
        if not apply_mode_and_save():
            return

        cancel_event.clear()
        run_btn.configure(state="disabled")
        stop_btn.configure(state="normal")
        status_var.set("运行中")

        def _worker():
            bot = None
            handler = None
            installed = []
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            try:
                handler = _QueueLogHandler(log_queue, level=logging.INFO)
                handler.setFormatter(
                    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
                )
                installed = _install_log_handler(handler)
                sys.stdout = _StreamToQueue(log_queue, "")
                sys.stderr = _StreamToQueue(log_queue, "")
                log_queue.put("已启动任务\n")

                try:
                    from mobile.config import Config
                    from mobile.damai_app import DamaiBot
                except ImportError:
                    from config import Config
                    from damai_app import DamaiBot

                cfg = Config.load_config(str(path))
                bot = DamaiBot(config=cfg, setup_driver=True)
                with bot_ref_lock:
                    bot_ref["bot"] = bot
                if cancel_event.is_set():
                    raise RuntimeError("已取消")
                bot.run_with_retry()
                root.after(0, lambda: status_var.set("运行结束"))
            except Exception as exc:
                log_queue.put(traceback.format_exc() + "\n")
                fail_message = f"运行失败: {exc}"
                root.after(0, lambda m=fail_message: status_var.set(m))
            finally:
                with bot_ref_lock:
                    bot_ref["bot"] = None
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                if handler is not None:
                    _remove_log_handler(handler, installed)
                try:
                    if bot and getattr(bot, "driver", None):
                        bot.driver.quit()
                except Exception:
                    pass
                root.after(
                    0,
                    lambda: (
                        run_btn.configure(state="normal"),
                        stop_btn.configure(state="disabled"),
                    ),
                )

        threading.Thread(target=_worker, daemon=True).start()

    run_btn.configure(command=run_bot)

    def stop_bot():
        cancel_event.set()
        log_queue.put("已请求停止任务，正在尝试中断...\n")
        status_var.set("已请求停止")
        with bot_ref_lock:
            bot = bot_ref.get("bot")
        try:
            if bot and getattr(bot, "driver", None):
                bot.driver.quit()
        except Exception:
            pass

    stop_btn.configure(command=stop_bot)
    btn_clear_log.configure(
        command=lambda: (
            log_view.configure(state="normal"),
            log_view.delete("1.0", "end"),
            log_view.configure(state="disabled"),
            status_var.set("日志已清空"),
        )
    )

    _poll_logs()
    load_from_path()
    root.mainloop()
