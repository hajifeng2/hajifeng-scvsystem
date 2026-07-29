# lib 包标记
# Windows 控制台默认 GBK，强制 stdout/stderr 用 UTF-8，避免 ✓/❌/⚠️ 等字符 print 崩溃。
# 所有脚本都 from lib.* import，本文件先执行，一处生效。
import sys as _sys

for _s in (_sys.stdout, _sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
