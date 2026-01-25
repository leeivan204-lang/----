# 使用輕量級 Python 3.12 映像檔
FROM python:3.12-slim-bookworm

# 設定環境變數
# PYTHONUNBUFFERED=1: 讓 log 直接輸出，方便 debugging
# UV_SYSTEM_PYTHON=1: 讓 uv 直接安裝到系統 python 環境 (容器內通常不需要 venv)
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# 安裝系統依賴 (如果有的話)
# RUN apt-get update && apt-get install -y --no-install-recommends curl

# 安裝 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 設定工作目錄
WORKDIR /app

# 複製依賴文件
COPY pyproject.toml uv.lock ./

# 安裝依賴
# --frozen: 嚴格依照 lock file 安裝
RUN uv sync --frozen

# 複製應用程式程式碼
COPY . .

# 建立資料夾結構 (確保掛載點存在)
RUN mkdir -p uploads

# 暴露端口
EXPOSE 8000

# 啟動命令
# 使用 uvicorn 啟動
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
