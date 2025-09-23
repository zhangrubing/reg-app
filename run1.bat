@echo off
REM 软件注册与激活系统 - Windows一键运行脚本
REM 支持自动安装依赖并启动服务

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM 颜色定义
set "RED=[31m"
set "GREEN=[32m"
set "YELLOW=[33m"
set "BLUE=[34m"
set "NC=[0m"

REM 打印带颜色的信息
echo %BLUE%[INFO]%NC% 正在检查Python版本...

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% 未找到Python，请先安装Python 3.8+
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo %GREEN%[SUCCESS]%NC% 找到 Python %PYTHON_VERSION%

REM 检查Python版本是否>=3.8
python -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo %RED%[ERROR]%NC% Python版本过低，需要 >= 3.8
    exit /b 1
)
echo %GREEN%[SUCCESS]%NC% Python版本符合要求

REM 升级pip
echo %BLUE%[INFO]%NC% 升级pip...
python -m pip install --upgrade pip

REM 安装依赖
if exist "backend\requirements.txt" (
    echo %BLUE%[INFO]%NC% 安装依赖包...
    pip install -r backend\requirements.txt
    echo %GREEN%[SUCCESS]%NC% 依赖包安装完成
) else (
    echo %RED%[ERROR]%NC% 未找到backend\requirements.txt文件
    exit /b 1
)

REM 创建必要的目录
echo %BLUE%[INFO]%NC% 创建必要的目录...
if not exist "logs" mkdir logs
if not exist "uploads" mkdir uploads
if not exist "static\assets" mkdir static\assets
echo %GREEN%[SUCCESS]%NC% 目录创建完成

REM 生成配置文件
if not exist ".env" (
    echo %BLUE%[INFO]%NC% 生成配置文件...
    (
        echo # 应用配置
        echo APP_NAME="软件注册与激活系统"
        echo APP_VERSION="1.0.0"
        echo DEBUG=false
        echo.
        echo # 服务器配置
        echo HOST=0.0.0.0
        echo PORT=8000
        echo RELOAD=false
        echo.
        echo # 数据库配置
        echo DATABASE_URL=sqlite+aiosqlite:///./data/regapp.db
        echo.
        echo # Redis配置 ^(可选^)
        echo REDIS_URL=redis://localhost:6379/0
        echo.
        echo # JWT配置
        echo SECRET_KEY=your-secret-key-change-this-in-production
        echo ACCESS_TOKEN_EXPIRE_MINUTES=30
        echo REFRESH_TOKEN_EXPIRE_DAYS=7
        echo.
        echo # 2FA配置
        echo TOTP_ISSUER=RegApp
        echo.
        echo # 日志配置
        echo LOG_LEVEL=INFO
        echo LOG_FILE=logs/app.log
        echo.
        echo # 安全配置
        echo BCRYPT_ROUNDS=12
        echo API_KEY_LENGTH=64
    ) > .env
    echo %GREEN%[SUCCESS]%NC% 配置文件已生成，请根据需要修改 .env 文件
) else (
    echo %BLUE%[INFO]%NC% 配置文件已存在
)

REM 显示欢迎信息
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                软件注册与激活系统                           ║
echo ║                Software Registration ^& Activation System    ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM 设置默认参数
if "%HOST%"=="" set HOST=0.0.0.0
if "%PORT%"=="" set PORT=8000
if "%DEBUG%"=="" set DEBUG=false
if "%RELOAD%"=="" set RELOAD=false

echo %BLUE%[INFO]%NC% 服务启动参数:
echo   主机: %HOST%
echo   端口: %PORT%
echo   调试模式: %DEBUG%

echo %GREEN%[SUCCESS]%NC% 服务启动中...
echo.
echo %BLUE%[INFO]%NC% 访问地址:
echo   首页: http://localhost:%PORT%
echo   API文档: http://localhost:%PORT%/docs
echo   管理面板: http://localhost:%PORT%/dashboard
echo.
echo %YELLOW%[WARNING]%NC% 按 Ctrl+C 停止服务
echo.

REM 启动应用
cd /d %~dp0
set "APP_ENV=dev"
set "APP_SECRET=change-this-secret"
set "SAMPLE_INTERVAL=5"
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8080 --reload --proxy-headers


REM 保持窗口打开（如果应用异常退出）
echo.
echo %RED%[ERROR]%NC% 服务已停止
pause
