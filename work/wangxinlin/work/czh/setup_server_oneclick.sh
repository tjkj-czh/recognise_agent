#!/usr/bin/env bash
set -Eeuo pipefail

############################################
# 用地识别智能体 服务器一键初始化脚本（ROOT专用）
# 适用: Ubuntu 22.04 + NVIDIA GPU + CUDA 12.4
# 特性: 进度显示 + 实时控制台输出 + 错误定位
############################################

# 可通过环境变量覆盖
LANDUSE_BASE_DIR="${LANDUSE_BASE_DIR:-$HOME/tjkj}"
LANDUSE_DB_PASSWORD="${LANDUSE_DB_PASSWORD:-ChangeMe_DB_2026!}"
LANDUSE_MINIO_USER="${LANDUSE_MINIO_USER:-landuse}"
LANDUSE_MINIO_PASSWORD="${LANDUSE_MINIO_PASSWORD:-ChangeMe_MinIO_2026!}"

CONDA_DIR="$HOME/miniconda3"
ENV_NAME="landuse"
DOCKER_DIR="$LANDUSE_BASE_DIR/docker"
ENV_FILE="$LANDUSE_BASE_DIR/.env"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"

# 先准备日志目录，再把所有输出同步到控制台和日志文件
BOOT_LOG_DIR="$LANDUSE_BASE_DIR/logs"
mkdir -p "$BOOT_LOG_DIR"
LOG_FILE="$BOOT_LOG_DIR/setup_server_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

log()  { echo -e "\033[1;32m[INFO]\033[0m $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m $*"; }
err()  { echo -e "\033[1;31m[ERR ]\033[0m $*"; }

TOTAL_STEPS=10
CURRENT_STEP=0

show_step() {
  local title="$1"
  CURRENT_STEP=$((CURRENT_STEP + 1))
  local pct=$((CURRENT_STEP * 100 / TOTAL_STEPS))
  echo
  echo "============================================================"
  echo "[进度] 第 ${CURRENT_STEP}/${TOTAL_STEPS} 步 (${pct}%) - ${title}"
  echo "============================================================"
}

on_error() {
  local line="$1"
  local cmd="$2"
  local code="$3"
  echo
  err "脚本执行失败！"
  err "失败行号: ${line}"
  err "失败命令: ${cmd}"
  err "退出码: ${code}"
  err "完整日志: ${LOG_FILE}"
  echo
  echo "请把上述报错片段 + 日志末尾发给我，我会快速帮你修复。"
  exit "$code"
}
trap 'on_error ${LINENO} "${BASH_COMMAND}" "$?"' ERR

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { err "缺少命令: $1"; exit 1; }
}

# ROOT专用
if [[ "$(id -u)" -ne 0 ]]; then
  err "本脚本为 root 专用，请使用 root 用户执行。"
  exit 1
fi

require_cmd curl
require_cmd wget
require_cmd grep
require_cmd awk

if [[ -f /etc/os-release ]]; then
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" ]]; then
    warn "当前系统不是 Ubuntu，脚本按 Ubuntu 流程执行，可能失败。"
  fi
  if [[ "${VERSION_ID:-}" != "22.04" ]]; then
    warn "推荐 Ubuntu 22.04，当前版本: ${VERSION_ID:-unknown}"
  fi
fi

show_step "安装系统基础依赖"
apt update
DEBIAN_FRONTEND=noninteractive apt install -y \
  ca-certificates gnupg lsb-release software-properties-common \
  git curl wget vim jq unzip build-essential pkg-config \
  libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev \
  gdal-bin libgdal-dev libproj-dev proj-bin libspatialindex-dev

show_step "安装 Docker + Compose"
if ! command -v docker >/dev/null 2>&1; then
  apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
  mkdir -p /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list >/dev/null
  apt update
  DEBIAN_FRONTEND=noninteractive apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
  log "Docker 已安装，跳过安装步骤"
fi

show_step "安装 NVIDIA Container Toolkit"
if ! dpkg -s nvidia-container-toolkit >/dev/null 2>&1; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
    gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
  apt update
  DEBIAN_FRONTEND=noninteractive apt install -y nvidia-container-toolkit
else
  log "nvidia-container-toolkit 已安装，跳过安装步骤"
fi

nvidia-ctk runtime configure --runtime=docker || true
systemctl restart docker

show_step "安装 Miniconda + Python 3.10 环境"
if [[ ! -x "$CONDA_DIR/bin/conda" ]]; then
  wget -O /tmp/Miniconda3-latest-Linux-x86_64.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
  bash /tmp/Miniconda3-latest-Linux-x86_64.sh -b -p "$CONDA_DIR"
else
  log "Miniconda 已安装，跳过安装步骤"
fi

# shellcheck disable=SC1091
source "$CONDA_DIR/etc/profile.d/conda.sh"
conda config --set auto_activate_base false || true
if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  conda create -n "$ENV_NAME" python=3.10 -y
else
  log "Conda 环境 $ENV_NAME 已存在，跳过创建"
fi

show_step "安装 Python 依赖（landuse）"
conda run -n "$ENV_NAME" pip install --upgrade pip
conda run -n "$ENV_NAME" pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
conda run -n "$ENV_NAME" pip install \
  fastapi==0.115.0 uvicorn[standard]==0.30.6 pydantic==2.9.0 \
  sqlalchemy==2.0.35 asyncpg==0.29.0 psycopg2-binary==2.9.9 alembic==1.13.2 \
  celery==5.4.0 redis==5.1.1 flower==2.0.1 \
  python-multipart==0.0.9 python-jose==3.3.0 httpx==0.27.2 \
  loguru==0.7.2 websockets==13.1 pandas==2.2.3 minio==7.2.9 \
  transformers==4.44.0 huggingface-hub==0.24.6 accelerate==0.33.0 vllm==0.6.0

if ! conda run -n "$ENV_NAME" pip install rasterio==1.3.10 geopandas==1.0.1 shapely==2.0.6 pyproj==3.6.1 fiona==1.9.6 rio-cogeo==5.3.1; then
  warn "pip 安装遥感依赖失败，切换 conda-forge 兜底"
  conda install -n "$ENV_NAME" -y -c conda-forge rasterio geopandas shapely pyproj fiona
fi

show_step "安装 Node.js 20 + pnpm"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  DEBIAN_FRONTEND=noninteractive apt install -y nodejs
else
  log "Node.js 已安装，跳过安装步骤"
fi
if ! command -v pnpm >/dev/null 2>&1; then
  npm install -g pnpm
else
  log "pnpm 已安装，跳过安装步骤"
fi

show_step "创建目录与配置文件"
mkdir -p "$LANDUSE_BASE_DIR"/{docker,logs,models,data,backups}
mkdir -p "$DOCKER_DIR"

cat > "$ENV_FILE" <<EOF
APP_ENV=dev
APP_NAME=landuse-agent

DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=landuse_agent
DB_USER=landuse
DB_PASSWORD=${LANDUSE_DB_PASSWORD}
DB_URL=postgresql+asyncpg://landuse:${LANDUSE_DB_PASSWORD}@127.0.0.1:5432/landuse_agent

REDIS_URL=redis://127.0.0.1:6379/0

MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=${LANDUSE_MINIO_USER}
MINIO_SECRET_KEY=${LANDUSE_MINIO_PASSWORD}
MINIO_SECURE=false
MINIO_BUCKET_IMAGES=images
MINIO_BUCKET_TILES=tiles
MINIO_BUCKET_PATCHES=patches
MINIO_BUCKET_EXPORTS=exports

VLM_API_URL=http://127.0.0.1:8001/v1
VLM_MODEL_NAME=Qwen/Qwen2-VL-7B-Instruct

MODEL_DIR=${LANDUSE_BASE_DIR}/models
SAM_WEIGHTS=${LANDUSE_BASE_DIR}/models/sam_vit_h_4b8939.pth

CUDA_VISIBLE_DEVICES=0
EOF

cat > "$COMPOSE_FILE" <<'YAML'
version: "3.8"
services:
  postgres:
    image: postgis/postgis:16-3.4
    container_name: landuse-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: landuse_agent
      POSTGRES_USER: landuse
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U landuse -d landuse_agent"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: landuse-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: landuse-minio
    restart: unless-stopped
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data
    command: server /data --console-address ":9001"

volumes:
  pgdata:
  miniodata:
YAML

show_step "启动中间件服务(PostGIS/Redis/MinIO)"
cd "$DOCKER_DIR"
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

docker compose up -d

show_step "创建 MinIO 桶"
for i in {1..30}; do
  if curl -fsS "http://127.0.0.1:9000/minio/health/live" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

docker run --rm --network host minio/mc sh -c "\
mc alias set local http://127.0.0.1:9000 ${LANDUSE_MINIO_USER} ${LANDUSE_MINIO_PASSWORD} && \
mc mb -p local/images || true && \
mc mb -p local/tiles || true && \
mc mb -p local/patches || true && \
mc mb -p local/exports || true"

show_step "环境验证"
log "Docker: $(docker --version)"
log "Compose: $(docker compose version | head -n 1)"
log "Node: $(node -v) | pnpm: $(pnpm -v)"
conda run -n "$ENV_NAME" python -c "import sys, torch; print('Python:', sys.version.split()[0], '| Torch:', torch.__version__, '| CUDA:', torch.cuda.is_available())"

echo
echo "========== 初始化完成 =========="
echo "基础目录: $LANDUSE_BASE_DIR"
echo "环境文件: $ENV_FILE"
echo "编排文件: $COMPOSE_FILE"
echo "日志文件: $LOG_FILE"
echo ""
echo "下一步："
echo "1) 上传你的业务代码到 $LANDUSE_BASE_DIR"
echo "2) 按项目命令启动 FastAPI/Celery/前端构建产物"
