@echo off
chcp 65001 >nul

REM ============================================================
REM scripts/start.bat
REM SuoXing-Tuan 工业检测平台 — 一键启动脚本
REM
REM 启动顺序: 后端 → 前端 → 浏览器
REM
REM 用法:
REM   双击运行，或在终端执行: scripts\start.bat
REM ============================================================

set ROOT=%~dp0..

echo.
echo ============================================
echo   SuoXing-Tuan 工业检测平台
echo ============================================
echo.

REM ---- 检查运行环境 ----
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

REM ==================== 1. 启动后端 ====================
echo [1/3] 启动后端服务...

cd /d "%ROOT%\backend"

REM 安装后端依赖（如有缺失）
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo   正在安装后端依赖...
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo   [错误] 后端依赖安装失败
        pause
        exit /b 1
    )
)

start "SuoXing-Tuan-Backend" cmd /c "python main.py"
echo   后端启动中 (http://localhost:8000)...

REM 等待后端就绪
echo   等待后端就绪...
:wait_backend
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/api/health >nul 2>&1
if %errorlevel% neq 0 (
    goto wait_backend
)
echo   后端已就绪!

REM ==================== 2. 启动前端 ====================
echo.
echo [2/3] 启动前端开发服务器...

cd /d "%ROOT%\frontend"

if not exist "node_modules" (
    echo   正在安装前端依赖...
    call npm install
    if %errorlevel% neq 0 (
        echo   [错误] 前端依赖安装失败
        pause
        exit /b 1
    )
)

start "SuoXing-Tuan-Frontend" cmd /c "npm run dev"
echo   前端启动中 (http://localhost:5173)...

REM 等待前端就绪
echo   等待前端就绪...
:wait_frontend
timeout /t 2 /nobreak >nul
curl -s http://localhost:5173 >nul 2>&1
if %errorlevel% neq 0 (
    goto wait_frontend
)
echo   前端已就绪!

REM ==================== 3. 打开浏览器 ====================
echo.
echo [3/3] 打开浏览器...
start "" http://localhost:5173

echo.
echo ============================================
echo   启动完成！
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo   API文档: http://localhost:8000/docs
echo ============================================
echo.
echo 按任意键关闭此窗口（前后端继续运行）
pause >nul
