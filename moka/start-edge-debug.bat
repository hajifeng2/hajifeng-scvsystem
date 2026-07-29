@echo off
chcp 65001 >nul
echo ============================================
echo  Edge CDP 启动器 (remote debugging 9222)
echo  profile: 本文件夹下 .edge-auto (独立 profile)
echo ============================================
echo.

echo [1/3] 关闭现有 Edge...
taskkill /F /IM msedge.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/3] 以远程调试端口启动 Edge (独立 profile，绕过 Edge136 对默认 profile 的限制)...
:: Edge 可执行路径，按实际安装位置改：
set EDGE="C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
:: profile 用本文件夹下 .edge-auto（首次需登录 Moka；若复用已有登录如 D:\摩卡系统\.edge-auto，改此行）
set PROFILE=%~dp0.edge-auto
start "" %EDGE% --remote-debugging-port=9222 --user-data-dir="%PROFILE%"

echo [3/3] 等待端口就绪...
timeout /t 5 /nobreak >nul

echo.
echo 完成。检查端口:
curl -s http://localhost:9222/json/version
echo.
echo 首次使用：在打开的 Edge 里登录 app.mokahr.com，保持登录。之后复用该 profile。
pause
