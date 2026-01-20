import os
import shutil
import sqlite3
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

app = FastAPI(title=os.getenv("VITE_APP_TITLE", "輔導工作紀錄助手"))

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 設定路徑
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "logs.db"))

# 確保上傳目錄存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 資料庫初始化
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS work_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            date TEXT NOT NULL,
            title TEXT NOT NULL,
            desc TEXT,
            link TEXT,
            notes TEXT,
            file_names TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Pydantic 模型 (用於回應)
class WorkLog(BaseModel):
    id: int
    role: str
    date: str
    title: str
    desc: Optional[str] = None
    link: Optional[str] = None
    notes: Optional[str] = None
    file_names: Optional[str] = None

# API: 取得所有紀錄
@app.get("/api/logs", response_model=List[WorkLog])
def get_logs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM work_logs ORDER BY date DESC, id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# API: 新增紀錄 (含檔案上傳)
@app.post("/api/logs")
async def create_log(
    role: str = Form(...),
    date: str = Form(...),
    title: str = Form(...),
    desc: Optional[str] = Form(None),
    link: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    files: List[UploadFile] = File(None)
):
    saved_file_names = []
    
    # 處理檔案上傳
    if files:
        for file in files:
            if file.filename:
                # 簡單防止檔名衝突：時間戳 + 原始檔名
                safe_filename = file.filename # 簡化處理，實際建議 hash 或 uuid
                # 這裡為了方便辨識，若有重複可考慮加後綴，為求簡單暫時覆蓋或直接存
                # 更嚴謹的做法：f"{int(datetime.now().timestamp())}_{file.filename}"
                final_filename = f"{int(datetime.now().timestamp())}_{file.filename}"
                file_path = os.path.join(UPLOAD_DIR, final_filename)
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                
                saved_file_names.append(final_filename)

    file_names_str = ",".join(saved_file_names) if saved_file_names else ""

    # 寫入資料庫
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO work_logs (role, date, title, desc, link, notes, file_names)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (role, date, title, desc, link, notes, file_names_str))
    
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    
    return {
        "id": new_id,
        "status": "success", 
        "message": "Log created successfully",
        "file_names": file_names_str
    }

# API: 刪除紀錄
@app.delete("/api/logs/{log_id}")
def delete_log(log_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 先查詢是否有檔案需要刪除
    c.execute("SELECT file_names FROM work_logs WHERE id = ?", (log_id,))
    row = c.fetchone()
    if row and row[0]:
        files = row[0].split(",")
        for f in files:
            if f:
                f_path = os.path.join(UPLOAD_DIR, f)
                if os.path.exists(f_path):
                    try:
                        os.remove(f_path)
                    except Exception as e:
                        print(f"Error deleting file {f_path}: {e}")

    c.execute("DELETE FROM work_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Log deleted"}

# API: 下載/查看檔案
@app.get("/uploads/{filename}")
async def get_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# 掛載靜態網頁 (最後掛載，以免蓋過 API)
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # 讀取 .env 或預設 Port
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
