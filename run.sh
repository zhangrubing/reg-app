#!/bin/bash

# 英智软件注册系统 - 一键运行脚本
# 支持国内镜像源，自动安装依赖并启动服务

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python版本
check_python() {
    print_info "检查Python版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
        print_success "找到 Python $PYTHON_VERSION"
        
        # 检查版本是否 >= 3.8
        if $PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
            print_success "Python版本符合要求 (>= 3.8)"
        else
            print_error "Python版本过低，需要 >= 3.8"
            exit 1
        fi
    else
        print_error "未找到Python3，请先安装Python 3.8+"
        exit 1
    fi
}

# 检查pip
check_pip() {
    print_info "检查pip..."
    
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
        print_success "找到 pip3"
    elif $PYTHON_CMD -m pip --version &> /dev/null; then
        PIP_CMD="$PYTHON_CMD -m pip"
        print_success "找到 pip (通过python -m pip)"
    else
        print_error "未找到pip，请先安装pip"
        exit 1
    fi
}

# 设置国内镜像源
setup_china_mirror() {
    print_info "设置国内镜像源..."
    
    # 清华镜像源
    export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
    export PIP_TRUSTED_HOST="pypi.tuna.tsinghua.edu.cn"
    
    print_success "已设置清华镜像源"
}

# 创建虚拟环境
create_venv() {
    if [ ! -d "venv" ]; then
        print_info "创建虚拟环境..."
        $PYTHON_CMD -m venv venv
        print_success "虚拟环境创建完成"
    else
        print_info "虚拟环境已存在"
    fi
    
    # 激活虚拟环境
    print_info "激活虚拟环境..."
    source venv/bin/activate || {
        print_error "激活虚拟环境失败"
        exit 1
    }
    print_success "虚拟环境已激活"
}

# 安装依赖
install_dependencies() {
    print_info "安装依赖包..."
    
    # 升级pip
    $PIP_CMD install --upgrade pip
    
    # 安装依赖
    if [ -f "requirements.txt" ]; then
        $PIP_CMD install -r requirements.txt
        print_success "依赖包安装完成"
    else
        print_error "未找到requirements.txt文件"
        exit 1
    fi
}

# 检查数据库连接
check_database() {
    print_info "检查数据库配置..."
    
    # 检查PostgreSQL连接
    if command -v psql &> /dev/null; then
        print_success "找到PostgreSQL客户端"
    else
        print_warning "未找到PostgreSQL客户端，请确保数据库服务已启动"
    fi
    
    # 检查Redis连接
    if command -v redis-cli &> /dev/null; then
        print_success "找到Redis客户端"
    else
        print_warning "未找到Redis客户端，Redis为可选组件"
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建必要的目录..."
    
    mkdir -p logs
    mkdir -p uploads
    mkdir -p static/assets
    
    print_success "目录创建完成"
}

# 生成配置文件
generate_config() {
    print_info "生成配置文件..."
    
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# 应用配置
APP_NAME="英智软件注册系统"
APP_VERSION="1.0.0"
DEBUG=false

# 服务器配置
HOST=0.0.0.0
PORT=8000
RELOAD=false

# 数据库配置
DATABASE_URL=postgresql+asyncpg://regapp_user:regapp_password@localhost/regapp_db

# Redis配置 (可选)
REDIS_URL=redis://localhost:6379/0

# JWT配置
SECRET_KEY=your-secret-key-change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 2FA配置
TOTP_ISSUER=RegApp

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# 安全配置
BCRYPT_ROUNDS=12
API_KEY_LENGTH=64
EOF
        print_success "配置文件已生成，请根据需要修改 .env 文件"
    else
        print_info "配置文件已存在"
    fi
}

# 运行数据库迁移
run_migrations() {
    print_info "运行数据库迁移..."
    
    # 这里可以添加数据库迁移命令
    # 例如: alembic upgrade head
    
    print_info "数据库迁移完成（如需迁移，请手动执行）"
}

# 启动服务
start_server() {
    print_info "启动FastAPI服务..."
    
    # 检查是否在虚拟环境中
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        print_error "虚拟环境未激活"
        exit 1
    fi
    
    print_info "服务启动参数:"
    echo "  主机: ${HOST:-0.0.0.0}"
    echo "  端口: ${PORT:-8000}"
    echo "  调试模式: ${DEBUG:-false}"
    
    print_success "服务启动中..."
    echo ""
    print_info "访问地址:"
    echo "  首页: http://localhost:${PORT:-8000}"
    echo "  API文档: http://localhost:${PORT:-8000}/docs"
    echo "  管理面板: http://localhost:${PORT:-8000}/dashboard"
    echo ""
    print_info "按 Ctrl+C 停止服务"
    echo ""
    
    # 启动应用
    python backend/app.py
}

# 显示帮助信息
show_help() {
    echo "英智软件注册系统 - 一键运行脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help      显示帮助信息"
    echo "  -d, --dev       开发模式（启用热重载）"
    echo "  -p, --prod      生产模式（默认）"
    echo "  --no-mirror     不使用国内镜像源"
    echo "  --skip-deps     跳过依赖安装"
    echo "  --skip-db       跳过数据库检查"
    echo ""
    echo "环境变量:"
    echo "  HOST            绑定主机 (默认: 0.0.0.0)"
    echo "  PORT            绑定端口 (默认: 8000)"
    echo "  DEBUG           调试模式 (默认: false)"
    echo ""
    echo "示例:"
    echo "  $0              # 生产模式运行"
    echo "  $0 -d           # 开发模式运行"
    echo "  $0 --skip-deps  # 跳过依赖安装"
    echo "  PORT=9000 $0    # 指定端口运行"
}

# 主函数
main() {
    local DEV_MODE=false
    local USE_MIRROR=true
    local SKIP_DEPS=false
    local SKIP_DB=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -d|--dev)
                DEV_MODE=true
                shift
                ;;
            -p|--prod)
                DEV_MODE=false
                shift
                ;;
            --no-mirror)
                USE_MIRROR=false
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --skip-db)
                SKIP_DB=true
                shift
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 设置环境变量
    export DEBUG=$DEV_MODE
    export RELOAD=$DEV_MODE
    
    # 显示欢迎信息
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                英智软件注册系统                           ║"
    echo "║                Software Registration & Activation System    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # 执行检查步骤
    check_python
    check_pip
    
    if [ "$USE_MIRROR" = true ]; then
        setup_china_mirror
    fi
    
    create_venv
    
    if [ "$SKIP_DEPS" = false ]; then
        install_dependencies
    fi
    
    if [ "$SKIP_DB" = false ]; then
        check_database
    fi
    
    create_directories
    generate_config
    run_migrations
    
    # 启动服务
    start_server
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
