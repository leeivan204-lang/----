---
description: main.py 後端 API 測試案例
---

> 狀態：初始為 [ ]、完成為 [x]
> 注意：狀態只能在測試通過後由流程更新。
> 測試類型：API 邏輯、資料庫操作、檔案處理

---

## [x] 【API 邏輯】取得空紀錄列表
**範例輸入**：
- 資料庫狀態：無資料
- Request: `GET /api/logs`
**期待輸出**：
- Status Code: 200
- Body: `[]`

---

## [x] 【API 邏輯】新增純文字紀錄
**範例輸入**：
- Request: `POST /api/logs`
- Form Data:
    - role: "Teacher"
    - date: "2024-01-20"
    - title: "教學研討"
    - desc: "討論課程內容"
**期待輸出**：
- Status Code: 200
- Body JSON 包含:
    - `status`: "success"
    - `file_names`: ""
    - `id`: (Integer)
- 資料庫: `work_logs` 表中新增一筆對應資料

---

## [x] 【API 邏輯】新增含檔案紀錄 (檔案上傳功能)
**範例輸入**：
- Request: `POST /api/logs`
- Form Data:
    - role: "Admin"
    - date: "2024-01-20"
    - title: "會議記錄"
- Files: `upload_test.txt` (內容: "content")
**期待輸出**：
- Status Code: 200
- Body JSON 包含:
    - `status`: "success"
    - `file_names`: (字串包含 `_upload_test.txt`)
- 檔案系統: `uploads/` 資料夾下存在該檔案 (檔名有 timestamp 前綴)
- 資料庫: `work_logs` 表中該筆資料 `file_names` 欄位正確

---

## [x] 【API 邏輯】取得紀錄列表 (資料驗證)
**範例輸入**：
- 前置條件：已新增上述紀錄
- Request: `GET /api/logs`
**期待輸出**：
- Status Code: 200
- Body: JSON Array，包含剛新增的紀錄，且按照日期與 ID 倒序排列

---

## [x] 【API 邏輯】下載已上傳檔案
**範例輸入**：
- 前置條件：取得上傳後的檔名 (例如 `1705766400_upload_test.txt`)
- Request: `GET /uploads/{filename}`
**期待輸出**：
- Status Code: 200
- Body: 檔案內容 ("content")

---

## [x] 【API 邏輯】下載不存在的檔案
**範例輸入**：
- Request: `GET /uploads/non_existent_file.txt`
**期待輸出**：
- Status Code: 404
- Body: `{"detail": "File not found"}`

---

## [x] 【API 邏輯】刪除紀錄與關聯檔案
**範例輸入**：
- 前置條件：已新增含檔案的紀錄，ID 為 `log_id`，檔名為 `filename`
- Request: `DELETE /api/logs/{log_id}`
**期待輸出**：
- Status Code: 200
- Body: `{"status": "success", "message": "Log deleted"}`
- 資料庫: 該 ID 資料已移除
- 檔案系統: `uploads/` 資料夾下該 `filename` 已被移除

---
