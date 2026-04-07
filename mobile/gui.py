import json
import threading
from pathlib import Path


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

    path_var = tk.StringVar(value=str(Path(config_path).expanduser()) if config_path else str(_default_config_path()))
    status_var = tk.StringVar(value="就绪")

    mode_labels = {
        "probe": "安全探测（不提交）",
        "validation": "开发验证（不提交）",
        "submit": "正式抢票（会提交）",
    }
    mode_label_to_key = {v: k for k, v in mode_labels.items()}
    mode_var = tk.StringVar(value=mode_labels["probe"])

    top = ttk.Frame(root, padding=10)
    top.pack(fill="x")

    ttk.Label(top, text="配置文件：").pack(side="left")
    path_entry = ttk.Entry(top, textvariable=path_var)
    path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

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

    ttk.Button(top, text="选择", command=browse).pack(side="left", padx=(0, 6))

    editor = ScrolledText(root, undo=True)
    editor.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    bottom = ttk.Frame(root, padding=(10, 0, 10, 10))
    bottom.pack(fill="x")

    ttk.Label(bottom, text="运行模式：").pack(side="left")
    mode_combo = ttk.Combobox(
        bottom,
        textvariable=mode_var,
        values=[mode_labels["probe"], mode_labels["validation"], mode_labels["submit"]],
        state="readonly",
        width=24,
    )
    mode_combo.pack(side="left", padx=(0, 10))

    def _get_path() -> Path:
        return Path(path_var.get()).expanduser()

    def _ensure_template_if_missing(path: Path) -> None:
        if path.exists():
            return
        template = _mobile_dir() / "config.example.jsonc"
        if not template.exists():
            raise FileNotFoundError(f"配置模板未找到: {template}")
        _write_text(path, _read_text(template))

    def load_from_path():
        path = _get_path()
        try:
            _ensure_template_if_missing(path)
            text = _read_text(path)
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))
            status_var.set("读取失败")
            return

        editor.delete("1.0", "end")
        editor.insert("1.0", text)
        status_var.set("已载入")

        try:
            cfg = json.loads(_strip_jsonc_comments(text))
            mode_key = runtime_mode_key_from_dict(cfg)
            mode_var.set(mode_labels[mode_key])
        except Exception:
            pass

    def save_to_path():
        path = _get_path()
        try:
            _write_text(path, editor.get("1.0", "end-1c") + "\n")
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))
            status_var.set("保存失败")
            return False
        status_var.set("已保存")
        return True

    def apply_mode_and_save():
        raw = editor.get("1.0", "end-1c")
        try:
            cfg = json.loads(_strip_jsonc_comments(raw))
        except Exception as exc:
            messagebox.showerror("模式应用失败", f"当前配置无法解析为 JSON/JSONC：\n{exc}")
            status_var.set("解析失败")
            return False

        mode_key = mode_label_to_key.get(mode_var.get(), "probe")
        probe_only, if_commit_order = runtime_mode_flags_from_key(mode_key)
        cfg["probe_only"] = probe_only
        cfg["if_commit_order"] = if_commit_order
        formatted = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
        editor.delete("1.0", "end")
        editor.insert("1.0", formatted)
        if not save_to_path():
            return False
        status_var.set(f"已应用模式：{mode_labels[mode_key]}")
        return True

    ttk.Button(bottom, text="载入", command=load_from_path).pack(side="left", padx=(0, 6))
    ttk.Button(bottom, text="保存", command=save_to_path).pack(side="left", padx=(0, 12))
    ttk.Button(bottom, text="应用模式并保存", command=apply_mode_and_save).pack(side="left", padx=(0, 12))

    run_btn = ttk.Button(bottom, text="启动", command=lambda: None)
    run_btn.pack(side="left", padx=(0, 6))

    def run_bot():
        path = _get_path()
        if not save_to_path():
            return
        if not apply_mode_and_save():
            return

        run_btn.configure(state="disabled")
        status_var.set("运行中")

        def _worker():
            bot = None
            try:
                try:
                    from mobile.config import Config
                    from mobile.damai_app import DamaiBot
                except ImportError:
                    from config import Config
                    from damai_app import DamaiBot

                cfg = Config.load_config(str(path))
                bot = DamaiBot(config=cfg, setup_driver=True)
                bot.run_with_retry()
                root.after(0, lambda: status_var.set("运行结束"))
            except Exception as exc:
                root.after(0, lambda: status_var.set(f"运行失败: {exc}"))
            finally:
                try:
                    if bot and getattr(bot, "driver", None):
                        bot.driver.quit()
                except Exception:
                    pass
                root.after(0, lambda: run_btn.configure(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    run_btn.configure(command=run_bot)

    ttk.Label(bottom, textvariable=status_var).pack(side="right")

    load_from_path()
    root.mainloop()
