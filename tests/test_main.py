import os
import pytest
from fastapi.testclient import TestClient
import sqlite3

# 設定測試環境變數 (必須在 import main 之前)
os.environ["DB_PATH"] = "test_logs.db"
os.environ["UPLOAD_DIR"] = "test_uploads"

# 確保測試目錄存在
os.makedirs("test_uploads", exist_ok=True)

# 為了確保測試隔離，我們需要在每次測試前清理舊的資料庫
if os.path.exists("test_logs.db"):
    os.remove("test_logs.db")
    
from main import app, init_db, UPLOAD_DIR, DB_PATH

# 重新初始化 DB (因為 import 時可能已經跑過，但我們剛刪除了)
init_db()

client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    # Setup: 確保乾淨的 DB 與 Uploads
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    
    # 清空測試上傳目錄
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            os.remove(os.path.join(UPLOAD_DIR, f))
            
    yield
    
    # Teardown
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if os.path.exists(UPLOAD_DIR):
        for f in os.listdir(UPLOAD_DIR):
            os.remove(os.path.join(UPLOAD_DIR, f))
        try:
            os.rmdir(UPLOAD_DIR)
        except:
            pass

def test_get_logs_empty():
    """【API 邏輯】取得空紀錄列表"""
    response = client.get("/api/logs")
    assert response.status_code == 200
    assert response.json() == []

def test_create_log_success():
    """【API 邏輯】新增純文字紀錄"""
    response = client.post(
        "/api/logs",
        data={
            "role": "Teacher",
            "date": "2024-01-20",
            "title": "教學研討",
            "desc": "討論課程內容"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "id" in data
    
    # Verify DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM work_logs WHERE id=?", (data["id"],))
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[3] == "教學研討" # title is 4th column (0-indexed: id, role, date, title)... wait 
    # Schema: id, role, date, title, desc, link, notes, file_names, created_at
    # Indices: 0, 1,    2,    3,     4,    5,    6,     7,          8

def test_create_log_with_file():
    """【API 邏輯】新增含檔案紀錄"""
    file_content = b"content"
    filename = "upload_test.txt"
    files = {"files": (filename, file_content, "text/plain")}
    
    response = client.post(
        "/api/logs",
        data={
            "role": "Admin",
            "date": "2024-01-20",
            "title": "會議記錄"
        },
        files=files
    )
    assert response.status_code == 200
    data = response.json()
    assert "file_names" in data
    assert f"_{filename}" in data["file_names"]
    
    saved_filename = data["file_names"]
    assert os.path.exists(os.path.join(UPLOAD_DIR, saved_filename))

def test_get_logs_verification():
    """【API 邏輯】取得紀錄列表 (資料驗證)"""
    # Create a log first
    client.post(
        "/api/logs",
        data={
            "role": "Teacher",
            "date": "2024-01-20",
            "title": "Check List"
        }
    )
    
    response = client.get("/api/logs")
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) == 1
    assert logs[0]["title"] == "Check List"

def test_download_file():
    """【API 邏輯】下載已上傳檔案"""
    # Upload first
    file_content = b"download content"
    filename = "download_test.txt"
    upload_res = client.post(
        "/api/logs",
        data={"role": "User", "date": "2024-01-20", "title": "For Download"},
        files={"files": (filename, file_content, "text/plain")}
    )
    saved_filename = upload_res.json()["file_names"]
    
    # Download
    response = client.get(f"/uploads/{saved_filename}")
    assert response.status_code == 200
    assert response.content == file_content

def test_download_non_existent_file():
    """【API 邏輯】下載不存在的檔案"""
    response = client.get("/uploads/non_existent_file.txt")
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"

def test_delete_log():
    """【API 邏輯】刪除紀錄與關聯檔案"""
    # Upload first to test file deletion
    file_content = b"to be deleted"
    filename = "delete_test.txt"
    upload_res = client.post(
        "/api/logs",
        data={"role": "User", "date": "2024-01-20", "title": "For Deletion"},
        files={"files": (filename, file_content, "text/plain")}
    )
    log_id = upload_res.json()["id"]
    saved_filename = upload_res.json()["file_names"]
    
    # Verify file exists
    file_path = os.path.join(UPLOAD_DIR, saved_filename)
    assert os.path.exists(file_path)
    
    # Delete
    response = client.delete(f"/api/logs/{log_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    # Verify DB for deletion
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM work_logs WHERE id=?", (log_id,))
    row = cursor.fetchone()
    conn.close()
    assert row is None
    
    # Verify file deletion
    assert not os.path.exists(file_path)
