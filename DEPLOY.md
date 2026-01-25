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

## 雲端部署建議 (No VPS users)

如果您沒有 VPS，推薦使用 **[Render](https://render.com)** (免費方案可用)：

1.  註冊 Render 帳號並連結 GitHub。
2.  點擊 **New +** -> **Blueprint**。
3.  選擇您的 Repository。
4.  Render 會自動讀取 `render.yaml` 並開始部署。

### 設定自動部署 (GitHub Action Trigger)

雖然 Render 會自動監聽 GitHub 變更，但若您希望由 GitHub Action 觸發 (例如在測試通過後)：

1.  在 Render Dashboard 找到您的服務 -> Settings -> **Deploy Hook**。
2.  複製 Deploy Hook URL。
3.  在 GitHub Repo -> Settings -> Secrets -> Actions -> New Secret：
    - Name: `RENDER_DEPLOY_HOOK_URL`
    - Value: (剛剛複製的網址)
4.  現在，每次 Push 到 Main，GitHub Action 跑完測試後會通知 Render 更新。

> **注意**：Render 免費版不支援 Persistent Disk。每次重新部署，網站上的 `logs.db` 會重置。但您的資料會保留在 **Google Sheet** 中 (因為您有設定同步)，所以不用擔心資料遺失。


