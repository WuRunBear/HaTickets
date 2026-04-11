import os
import sys

base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_path)

def _prepend_to_path(path: str) -> None:
    if not path or not os.path.isdir(path):
        return
    current = os.environ.get("PATH", "")
    os.environ["PATH"] = path + os.pathsep + current


adb_dir = os.path.join(base_path, "platform-tools", "adb")
platform_tools_dir = os.path.join(base_path, "platform-tools")
if os.path.isfile(os.path.join(adb_dir, "adb.exe")):
    _prepend_to_path(adb_dir)
elif os.path.isfile(os.path.join(platform_tools_dir, "adb.exe")):
    _prepend_to_path(platform_tools_dir)

if "ANDROID_HOME" not in os.environ and os.path.isdir(platform_tools_dir):
    os.environ["ANDROID_HOME"] = base_path
    os.environ["ANDROID_SDK_ROOT"] = base_path


if __name__ == "__main__":
    from mobile.damai_app import main
    argv = sys.argv[1:]
    if not argv:
        argv = ["--gui"]
    raise SystemExit(main(argv))
