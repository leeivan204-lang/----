import os
import shutil
import sqlite3
from typing import List, Optional
from datetime import datetime, timedelta
import httpx

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext

# 載入環境變數
load_dotenv()

# --- Config ---
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-keep-it-secret") # In production, use a strong env var!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200 # 30 days

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
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "logs.db")

# 確保上傳目錄存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Security & Auth Setup ---
# --- Security & Auth Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Modified: auto_error=False to allow checking token manually or skipping it
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

class User(BaseModel):
    username: str
    role: str
    email: Optional[str] = None

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

# --- Database ---
# ... (omitted for brevity, we are jumping to get_current_user area)

# NOTE: I need to target the block around line 46 and line 155. 
# Since replace_file_content works on contiguous blocks, and these are far apart, I might need 2 calls or MultiReplace.
# Actually I can just update oauth2_scheme first.

# Let's split this.

# --- Database ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Work Logs Table (Added workspace_id)
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT,
            user_id TEXT,
            workspace_id INTEGER
        )
    ''')
    
    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            google_sheet_url TEXT
        )
    ''')

    # Workspaces Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sheet_tab_name TEXT,
            owner_id TEXT
        )
    ''')

    # Workspace Users (Join Table)
    c.execute('''
        CREATE TABLE IF NOT EXISTS workspace_users (
            workspace_id INTEGER,
            user_id TEXT,
            role TEXT NOT NULL, -- manager, editor, visitor
            PRIMARY KEY (workspace_id, user_id),
            FOREIGN KEY(workspace_id) REFERENCES workspaces(id),
            FOREIGN KEY(user_id) REFERENCES users(username)
        )
    ''')

    # Migrations
    try:
        c.execute("ALTER TABLE work_logs ADD COLUMN category TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE work_logs ADD COLUMN user_id TEXT")
    except sqlite3.OperationalError:
        pass
        
    try:
        c.execute("ALTER TABLE work_logs ADD COLUMN workspace_id INTEGER")
        # If we just added this column, we should create a default workspace and assign all existing logs to it
        print("Migrating: Added workspace_id column. Seeding default workspace...")
        c.execute("INSERT INTO workspaces (name, sheet_tab_name, owner_id) VALUES (?, ?, ?)", 
                  ("預設工作區", "Log", "admin"))
        default_ws_id = c.lastrowid
        
        # Update all logs to default workspace
        c.execute("UPDATE work_logs SET workspace_id = ?", (default_ws_id,))
        
        # Migrate existing users to default workspace:
        # 1. Admin -> manager
        # 2. User -> editor
        c.execute("SELECT username, role FROM users")
        for u in c.fetchall():
            uname, urole = u
            ws_role = "manager" if urole == "admin" else "editor"
            c.execute("INSERT OR IGNORE INTO workspace_users (workspace_id, user_id, role) VALUES (?, ?, ?)", 
                      (default_ws_id, uname, ws_role))
            
    except sqlite3.OperationalError:
        pass
        pass # Already exists
        
    try:
        c.execute("ALTER TABLE work_logs ADD COLUMN user_id TEXT")
    except sqlite3.OperationalError:
        pass # Already exists

    # Create Default Admin if not exists (Check if ANY admin exists)
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    if c.fetchone()[0] == 0:
        admin_pwd = pwd_context.hash("admin")
        c.execute("INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)", ("admin", admin_pwd, "admin"))
        print("Created default admin user (password: admin)")

    # Create Default User if not exists
    c.execute("SELECT * FROM users WHERE username = 'user'")
    if not c.fetchone():
        user_pwd = pwd_context.hash("user")
        c.execute("INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?)", ("user", user_pwd, "user"))
        print("Created default normal user (password: user)")

    conn.commit()
    conn.close()

init_db()

# --- Auth Helper Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_db_user(username: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        return UserInDB(**dict(row))
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    
    user = get_db_user(token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_optional_user(token: str = Depends(oauth2_scheme)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            return None
        token_data = TokenData(username=username, role=role)
    except JWTError:
        return None
    
    user = get_db_user(token_data.username)
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

# --- Pydantic Models for Response ---
class WorkLog(BaseModel):
    id: int
    role: str
    date: str
    title: str
    desc: Optional[str] = None
    link: Optional[str] = None
    notes: Optional[str] = None
    file_names: Optional[str] = None
    category: Optional[str] = None
    user_id: Optional[str] = None

# --- API Endpoints ---

# Auth: Login (ID Only - Logic Adjusted)
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Modified: Ignore password check, just check if user exists
    user = get_db_user(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # We still use the hashed password from DB to verify? No, user said "Only ID".
    # So if user exists, we grant token.
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Auth: Create User (Create ID)
@app.post("/api/users")
async def create_user(
    username: str = Form(...),
    password: str = Form("default"), 
    google_sheet_url: Optional[str] = Form(None),
    role: str = Form("user"), # Default to user
    token: Optional[str] = Depends(oauth2_scheme) # Check if authorized
):
    # Security: Only Admin can create 'admin' role
    if role == "admin":
        if not token:
             raise HTTPException(status_code=403, detail="Admin token required")
        # Validate token manually or use helper
        try:
             payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
             if payload.get("role") != "admin":
                 raise HTTPException(status_code=403, detail="Not authorized")
        except Exception:
             raise HTTPException(status_code=403, detail="Invalid token")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_pwd = get_password_hash(password)
    c.execute("INSERT INTO users (username, hashed_password, role, google_sheet_url) VALUES (?, ?, ?, ?)", 
              (username, hashed_pwd, role, google_sheet_url))
    conn.commit()
    conn.close()
    
    # Sync to Google Sheet if URL exists
    if google_sheet_url:
        try:
            async with httpx.AsyncClient() as client:
                # Assuming the Script accepts POST with JSON data
                payload = {
                    "action": "create_user",
                    "username": username,
                    "role": "user",
                    "created_at": str(datetime.now())
                }
                await client.post(google_sheet_url, json=payload, timeout=10.0)
        except Exception as e:
            print(f"Failed to sync with Google Sheet: {e}")
            # We don't fail the registration if sync fails, but maybe log it
    
    return {"status": "success", "username": username, "message": "User created successfully"}

# Auth: Me
@app.get("/api/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.put("/api/me/sheet")
async def update_sheet_url(url: str = Form(...), current_user: User = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET google_sheet_url = ? WHERE username = ?", (url, current_user.username))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Updated sync URL"}

@app.get("/api/logs", response_model=List[WorkLog])
def get_logs(
    workspace_id: int,
    date: Optional[str] = None,
    user_id: Optional[str] = None,
    keyword: Optional[str] = None,
    user: Optional[User] = Depends(get_optional_user) # Allow guest access
):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Permission Check: Must be member of workspace (any role)
    # If Guest (no user): We need to decide if Guests are per-workspace or global. 
    # Plan says: "User ... Visitor". Visitor implies they are in workspace_users with role='visitor'.
    # But if they are not logged in, they don't have a user_id. 
    # Current "Guest Mode" is public access. 
    # Let's assume if user is None (Guest), they can only access "Public Workspaces" or we just allow it for now logic-wise 
    # BUT the multi-tenant plan implies strict membership. 
    # Let's ENFORCE membership. So Guest must actually login as a "Visitor User"? 
    # Or does "Guest Mode" bypass this? 
    # Re-reading prompt: "每個資料庫有一個管理者、數個編輯者、數個訪客". This implies Visitors ARE users with "visitor" role.
    # So the "Guest Visit" button previously made was for "Public Access". 
    # To support specific Visitors, they need accounts. 
    # However, to keep it simple and consistent with previous "Guest Visit", 
    # let's assume if user is None, they are viewing a PUBLIC workspace or forbidden?
    # Let's STRICTLY enforce membership. If you are a visitor, you must log in with an ID that has 'visitor' role.
    # WAIT, User asked "Visitor how to see data" -> I added "Guest Visit" (No ID).
    # NOW User asks for "Multi-DB with specific Visitors". 
    # This conflicts. "Guest Visit" (No ID) cannot have specific workspace permissions unless the workspace is public.
    # I will allow access if user is member OR if user is None (Legacy Guest Mode, maybe restricted to default workspace or specific public one).
    # Update: Let's require user to be at least a member.
    
    # Check membership
    has_access = False
    if user:
        c.execute("SELECT role FROM workspace_users WHERE workspace_id = ? AND user_id = ?", (workspace_id, user.username))
        row = c.fetchone()
        if row:
            has_access = True
    
    # If no access and not public (concept not yet implemented), forbid. 
    # For dev transition: If workspace_id is default (1) and user is None, maybe allow? 
    # Let's enforce: User must be member.
    # If user is None (Guest Button), they have no ID. They cannot be a "specific visitor" in a DB.
    # I will MODIFY the Guest Button logic later to maybe use a shared "visitor" account or just keep it as is.
    # For now, let's just checking membership if user exists.
    
    if not has_access:
        # Check if user is Admin (Global)? 
        # If user is admin (global), maybe allow all?
        if user and user.role == "admin":
             pass
        else:
             # What about totally anonymous guest? 
             # If "Guest Mode" button was used, user is None.
             # We should probably allow them to see Default Workspace (1) for backward compatibility?
             if user is None and workspace_id == 1:
                 pass
             else:
                 conn.close()
                 raise HTTPException(status_code=403, detail="Access denied to this workspace")

    query = "SELECT * FROM work_logs WHERE workspace_id = ?"
    params = [workspace_id]
    
    if date:
        query += " AND date = ?"
        params.append(date)
        
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)
        
    if keyword:
        query += " AND (title LIKE ? OR desc LIKE ? OR notes LIKE ?)"
        kw_param = f"%{keyword}%"
        params.extend([kw_param, kw_param, kw_param])
        
    query += " ORDER BY date DESC, id DESC"
    
    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/logs/{log_id}")
def get_single_log(log_id: int, current_user: User = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM work_logs WHERE id = ?", (log_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Log not found")
    return dict(row)

# API: 新增紀錄 (含檔案上傳)
@app.post("/api/logs")
async def create_log(
    role: str = Form(""), 
    date: str = Form(...),
    title: str = Form(...),
    desc: Optional[str] = Form(None),
    link: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    workspace_id: int = Form(1), # Default to 1 if missing
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    saved_file_names = []
    
    # 處理檔案上傳
    if files:
        for file in files:
            if file.filename:
                # 簡單防止檔名衝突：時間戳 + 原始檔名
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
        INSERT INTO work_logs (role, date, title, desc, link, notes, file_names, category, user_id, workspace_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (role, date, title, desc, link, notes, file_names_str, category, current_user.username, workspace_id))
    
    conn.commit()
    new_id = c.lastrowid
    
    # Check for Google Sheet URL to sync
    c.execute("SELECT google_sheet_url FROM users WHERE username = ?", (current_user.username,))
    row = c.fetchone()
    sheet_url = row[0] if row else None
    
    conn.close()
    
    # Include ID and WorkspaceID in response/sync
    log_data = {
        "id": new_id,
        "role": role,
        "date": date,
        "title": title,
        "desc": desc,
        "link": link,
        "notes": notes,
        "category": category,
        "user_id": current_user.username,
        "workspace_id": workspace_id,
        "file_names": file_names_str
    }
    
    # Background Sync (Fire and Forget)
    if sheet_url:
        # Prepare file for sync (Upload the first one if available)
        # Note: synchronizing multiple large files via GAS JSON is limited.
        # We upload the LAST file added as a sample, or logic to loop?
        # For this version, let's upload the most recent file.
        
        sync_file_path = None
        if saved_file_names:
            sync_file_path = os.path.join(UPLOAD_DIR, saved_file_names[-1])

        import asyncio
        asyncio.create_task(sync_log_to_sheet(sheet_url, log_data, sync_file_path))
    
    return {
        "id": new_id,
        "status": "success", 
        "message": "Log created successfully",
        "file_names": file_names_str
    }

import base64
import mimetypes

async def sync_log_to_sheet(url: str, data: dict, file_path: Optional[str] = None):
    try:
        # If file_path is provided, encode it
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
                # Limit size? 5MB
                if len(content) < 5 * 1024 * 1024:
                    encoded = base64.b64encode(content).decode('utf-8')
                    data['file_content'] = encoded
                    data['file_name'] = os.path.basename(file_path)
                    mime = mimetypes.guess_type(file_path)[0]
                    data['mime_type'] = mime
        
        async with httpx.AsyncClient() as client:
            # Increase timeout for file upload
            await client.post(url, json=data, timeout=30.0)
    except Exception as e:
        print(f"Sync error: {e}")

# API: 刪除紀錄 (Admin only or Own log)
@app.delete("/api/logs/{log_id}")
def delete_log(log_id: int, current_user: User = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check ownership
    c.execute("SELECT user_id, file_names FROM work_logs WHERE id = ?", (log_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Log not found")
        
    owner_id, file_names = row
    
    # Only Admin or Owner can delete
    if current_user.role != "admin" and current_user.username != owner_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized to delete this log")
    
    # Delete files
    if file_names:
        files = file_names.split(",")
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

# API: 更新紀錄 (Edit)
@app.put("/api/logs/{log_id}")
async def update_log(
    log_id: int,
    date: str = Form(...),
    title: str = Form(...),
    desc: Optional[str] = Form(None),
    link: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    workspace_id: int = Form(...),
    role: str = Form(""),
    files: List[UploadFile] = File(None),
    current_user: User = Depends(get_current_user)
):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check ownership
    c.execute("SELECT user_id, file_names FROM work_logs WHERE id = ?", (log_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Log not found")
        
    owner_id, old_files_str = row
    if current_user.role != "admin" and current_user.username != owner_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized")

    # Handle Files: append new ones
    saved_file_names = []
    if files:
        for file in files:
            if file.filename:
                final_filename = f"{int(datetime.now().timestamp())}_{file.filename}"
                file_path = os.path.join(UPLOAD_DIR, final_filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                saved_file_names.append(final_filename)
    
    # Combine old and new files
    # (Client should send 'kept_files' if we want deletion, but for now let's just Append or Replace?
    # Simple logic: If 'file_names' logic is needed properly, we need a separate API to delete file.
    # For now, let's just Append new files to existing string.
    
    current_files = old_files_str.split(",") if old_files_str else []
    all_files = current_files + saved_file_names
    # Filter empty
    all_files = [f for f in all_files if f]
    new_files_str = ",".join(all_files)

    c.execute('''
        UPDATE work_logs 
        SET date=?, title=?, desc=?, link=?, notes=?, category=?, role=?, workspace_id=?, file_names=?
        WHERE id=?
    ''', (date, title, desc, link, notes, category, role, workspace_id, new_files_str, log_id))
    
    conn.commit() # FIXED: Added commit
    conn.close()
    
    # Sync update to Google Sheet
    if old_files_str != new_files_str:
        pass

    # Check for Google Sheet URL
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT google_sheet_url FROM users WHERE username = ?", (current_user.username,))
    row = c.fetchone()
    sheet_url = row[0] if row else None
    conn.close()

    if sheet_url:
        log_data = {
            "action": "update",
            "id": log_id,
            "role": role,
            "date": date,
            "title": title,
            "desc": desc,
            "link": link,
            "file_names": new_files_str,
            "category": category,
            "user_id": current_user.username
        }
        if new_files_str:
            # Try to find the last added file
            last_file = new_files_str.split(",")[-1] if "," in new_files_str else new_files_str
            if last_file:
                 update_file_path = os.path.join(UPLOAD_DIR, last_file)
        
        import asyncio
        asyncio.create_task(sync_log_to_sheet(sheet_url, log_data, update_file_path))
    
    return {"status": "success", "message": "Log updated"}

# API: 下載/查看檔案
@app.get("/uploads/{filename}")
async def get_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# Remove duplicate delete_log 
        
    owner_id, file_names = row
    
    # Only Admin or Owner can delete
    if current_user.role != "admin" and current_user.username != owner_id:
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized to delete this log")
    
    # Delete from DB
    c.execute("DELETE FROM work_logs WHERE id = ?", (log_id,))
    conn.commit()
    
    # Get Sheet URL
    c.execute("SELECT google_sheet_url FROM users WHERE username = ?", (owner_id,))
    row_user = c.fetchone()
    sheet_url = row_user[0] if row_user else None
    conn.close()

    # Sync Delete
    if sheet_url:
        sync_data = {"action": "delete", "id": log_id, "user_id": owner_id}
        import asyncio
        asyncio.create_task(sync_log_to_sheet(sheet_url, sync_data))

    return {"status": "success", "message": "Log deleted"}

# API: Admin Data (Testing)
@app.get("/api/admin/stats")
async def get_admin_stats(current_user: User = Depends(get_admin_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    user_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM work_logs")
    log_count = c.fetchone()[0]
    conn.close()
    return {"user_count": user_count, "log_count": log_count}

@app.get("/api/admin/users")
async def get_all_users(current_user: User = Depends(get_admin_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT username, role, google_sheet_url FROM users")
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    return users

@app.delete("/api/admin/users/{username}")
async def delete_user(username: str, current_user: User = Depends(get_admin_user)):
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete super admin")
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    c.execute("DELETE FROM workspace_users WHERE user_id = ?", (username,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.put("/api/admin/users/{username}/rename")
async def rename_user(username: str, new_username: str = Form(...), current_user: User = Depends(get_admin_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Check if new name exists
    c.execute("SELECT * FROM users WHERE username = ?", (new_username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="New username already exists")
        
    try:
        # PRAGMA foreign_keys might be off by default in sqlite, so manual update needed
        c.execute("UPDATE users SET username = ? WHERE username = ?", (new_username, username))
        c.execute("UPDATE workspace_users SET user_id = ? WHERE user_id = ?", (new_username, username))
        c.execute("UPDATE work_logs SET user_id = ? WHERE user_id = ?", (new_username, username))
        c.execute("UPDATE workspaces SET owner_id = ? WHERE owner_id = ?", (new_username, username))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
        
    conn.close()
    return {"status": "success", "old": username, "new": new_username}

# --- Workspace APIs ---

class WorkspaceOut(BaseModel):
    id: int
    name: str
    role: str # My role in this workspace

@app.get("/api/workspaces", response_model=List[WorkspaceOut])
def get_my_workspaces(user: User = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get workspaces where I am a member
    c.execute('''
        SELECT w.id, w.name, wu.role 
        FROM workspaces w
        JOIN workspace_users wu ON w.id = wu.workspace_id
        WHERE wu.user_id = ?
    ''', (user.username,))
    
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/workspaces")
def create_workspace(name: str = Form(...), user: User = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("INSERT INTO workspaces (name, owner_id) VALUES (?, ?)", (name, user.username))
    ws_id = c.lastrowid
    
    # Add creator as manager
    c.execute("INSERT INTO workspace_users (workspace_id, user_id, role) VALUES (?, ?, ?)", 
              (ws_id, user.username, "manager"))
    
    conn.commit()
    conn.close()
    return {"status": "success", "id": ws_id, "name": name}

@app.get("/api/workspaces/{ws_id}/members")
def get_workspace_members(ws_id: int, user: User = Depends(get_current_user)):
    # Check if user is manager in this ws
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT role FROM workspace_users WHERE workspace_id = ? AND user_id = ?", (ws_id, user.username))
    row = c.fetchone()
    if not row or row['role'] != 'manager':
        conn.close()
        raise HTTPException(status_code=403, detail="Not authorized (Manager only)")
        
    c.execute("SELECT user_id, role FROM workspace_users WHERE workspace_id = ?", (ws_id,))
    members = c.fetchall()
    conn.close()
    return [dict(m) for m in members]

@app.post("/api/workspaces/{ws_id}/invite")
def invite_member(ws_id: int, target_username: str = Form(...), role: str = Form("editor"), user: User = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Auth check
    c.execute("SELECT role FROM workspace_users WHERE workspace_id = ? AND user_id = ?", (ws_id, user.username))
    me = c.fetchone()
    if not me or me[0] != 'manager':
        conn.close()
        raise HTTPException(status_code=403, detail="Manager only")
        
    # Check target user exists
    c.execute("SELECT * FROM users WHERE username = ?", (target_username,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="User not found")
        
    try:
        c.execute("INSERT INTO workspace_users (workspace_id, user_id, role) VALUES (?, ?, ?)", 
                  (ws_id, target_username, role))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="User already in workspace")
        
    conn.close()
    return {"status": "success"}

@app.delete("/api/workspaces/{ws_id}/members/{target_uid}")
def remove_member(ws_id: int, target_uid: str, user: User = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Auth check
    c.execute("SELECT role FROM workspace_users WHERE workspace_id = ? AND user_id = ?", (ws_id, user.username))
    me = c.fetchone()
    if not me or me[0] != 'manager':
        conn.close()
        raise HTTPException(status_code=403, detail="Manager only")
        
    c.execute("DELETE FROM workspace_users WHERE workspace_id = ? AND user_id = ?", (ws_id, target_uid))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.put("/api/workspaces/{ws_id}/members/{target_uid}")
def update_member_role(ws_id: int, target_uid: str, role: str = Form(...), user: User = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Auth check
    c.execute("SELECT role FROM workspace_users WHERE workspace_id = ? AND user_id = ?", (ws_id, user.username))
    me = c.fetchone()
    if not me or me[0] != 'manager':
        conn.close()
        raise HTTPException(status_code=403, detail="Manager only")
        
    c.execute("UPDATE workspace_users SET role = ? WHERE workspace_id = ? AND user_id = ?", (role, ws_id, target_uid))
    conn.commit()
    conn.close()
    return {"status": "success"}

# 掛載靜態網頁
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
