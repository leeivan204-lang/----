# 部署指南 (Deployment Guide)

本專案支援使用 Docker 進行快速部署。以下是部署步驟與說明。

## 前置需求

- 安裝 [Docker](https://www.docker.com/get-started) 與 Docker Compose。

## 快速啟動

1.  **下載程式碼** (如果尚未下載)
    ```bash
    git clone <your-repo-url>
    cd <repo-folder>
    ```

2.  **啟動服務**
    執行以下命令來建置並啟動容器：
    ```bash
    docker compose up -d
    ```
    (第一次執行時需要下載映像檔並進行建置，可能需要幾分鐘)

3.  **訪問應用程式**
    打開瀏覽器訪問：[http://localhost:8000](http://localhost:8000)

4.  **停止服務**
    ```bash
    docker compose down
    ```

## 資料備份與持久化

為了確保資料不會因為容器重啟或更新而遺失，我們在 `docker-compose.yml` 中設定了掛載點：

- **資料庫**: 存放在主機的 `./data/logs.db`
- **上傳檔案**: 存放在主機的 `./data/uploads/`

請定期備份 `./data` 資料夾。

## 進階設定

### 環境變數
您可以在 `docker-compose.yml` 中修改環境變數，或建立 `.env` 檔案：

| 變數名稱 | 預設值 | 說明 |
| :--- | :--- | :--- |
| `SECRET_KEY` | `change_me...` | **重要**: 生產環境請務必修改此值以確保安全。 |
| `DB_PATH` | `/data/logs.db` | 容器內資料庫路徑 (建議保持預設) |
| `UPLOAD_DIR` | `/data/uploads` | 容器內上傳目錄路徑 (建議保持預設) |


## 雲端部署建議 (VPS)

若要在 DigitalOcean, AWS EC2, GCP Compute Engine 等 VPS 上部署：

1.  SSH 連線到伺服器。
2.  安裝 Docker 與 Docker Compose。
3.  Clone 本專案程式碼。
4.  執行 `docker compose up -d`。
5.  (選用) 設定 Nginx 反向代理與 SSL 憑證 (使用 Let's Encrypt)。

## 常見問題

**Q: 如何查看日誌 (Logs)?**
```bash
docker compose logs -f
```

**Q: 如何更新程式碼?**
```bash
git pull
docker compose build --no-cache
docker compose up -d
```

## 自動化部署 (CI/CD)

本專案已設定 GitHub Actions workflow (`.github/workflows/deploy.yml`)。

### 設定步驟

1.  **準備伺服器**: 確保伺服器已安裝 Docker, Docker Compose 與 Git。
2.  **首次設定**:
    在伺服器上建立目錄並 Clone 專案：
    ```bash
    mkdir -p ~/apps
    cd ~/apps
    git clone https://github.com/leeivan204/---- work-log-assistant
    cd work-log-assistant
    # 建立必要的資料夾
    mkdir -p data/uploads
    # 首次啟動 (確保環境變數設定正確)
    docker compose up -d
    ```
3.  **設定 GitHub Secrets**:
    在 GitHub Repo > Settings > Secrets and variables > Actions > New repository secret，新增以下變數：
    
    | Name | Value |
    | :--- | :--- |
    | `VPS_HOST` | 伺服器 IP (例如 `1.2.3.4`) |
    | `VPS_USERNAME` | SSH 使用者 (例如 `root`) |
    | `VPS_SSH_KEY` | SSH 私鑰內容 (建議使用專門的 Deploy Key) |
    
4.  **觸發部署**:
    當您推送到 `main` 分支時，GitHub Actions 會自動建置 Image 並部署到伺服器。

