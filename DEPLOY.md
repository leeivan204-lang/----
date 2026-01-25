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

## 雲端部署建議 (Fly.io)

既然您不使用 Render 且沒有 VPS，最強烈推薦使用 **[Fly.io](https://fly.io)**。
Fly.io 支援 **Docker** 部署，且最重要的是它支援 **Persistent Volumes (持久化硬碟)**，這對於保存您的 SQLite 資料庫 (`logs.db`) 至關重要。

### 設定步驟

1.  **安裝 Fly CLI**:
    - Windows (PowerShell): `iwr https://fly.io/install.ps1 -useb | iex`
    - Mac/Linux: `curl -L https://fly.io/install.sh | sh`

2.  **註冊/登入**:
    ```bash
    fly auth signup
    # 或
    fly auth login
    ```

3.  **初始化 App**:
    在專案目錄執行：
    ```bash
    fly launch --no-deploy
    ```
    - 跟隨提示操作。
    - **重要**: 當它問您是否要修改設定時，確認 `fly.toml` 內容正確 (特別是 `[mounts]` 部分)。
    - **建立 Volume** (存資料用):
      ```bash
      fly volumes create work_log_data --size 1
      ```
      (這會建立一個 1GB 的硬碟空間，掛載到 `/data`，確保資料不遺失)

4.  **設定 GitHub Action 自動部署**:
    - 取得 Deploy Token:
      ```bash
      fly tokens create deploy -x 999999h
      ```
    - 複製產生的 Token。
    - 前往 GitHub Repo > Settings > Secrets > Actions > New Secret。
    - Name: `FLY_API_TOKEN`
    - Value: (剛剛複製的 Token)。

5.  **推送到 GitHub**:
    當您推送到 `main` 分支時，GitHub Action 會自動將程式碼打包並部署到 Fly.io。



