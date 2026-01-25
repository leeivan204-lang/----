from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

from auth import create_access_token, get_password_hash, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES
from dependencies import get_current_active_user, get_admin_user
from models import fake_users_db
from schemas import Token, User

app = FastAPI()

# Setup CORS
origins = [
    "http://localhost:5173", # Vite default
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Server started. Available mock users:")
    print(" - johndoe / secret (User)")
    print(" - alice / secret (Admin)")

from debug_state import debug_state, DebugConfig

@app.post("/api/debug/config")
async def update_debug_config(config: dict):
    debug_state.update(config)
    return {"status": "success", "config": debug_state.get_config()}

@app.get("/api/debug/config")
async def get_debug_config():
    return debug_state.get_config()

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    config = debug_state.get_config()
    
    # Mock Scenarios: Login
    if config.force_login_error == "server_error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Simulated Server Error"
        )
    if config.force_login_error == "user_not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )
    if config.force_login_error == "invalid_password":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_dict = fake_users_db.get(form_data.username)
    if not user_dict or not verify_password(form_data.password, user_dict['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Include role in the token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict['username'], "role": user_dict['role']},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    config = debug_state.get_config()
    
    # Mock Scenarios: Protected Route
    if config.force_server_error:
        raise HTTPException(status_code=500, detail="Simulated Server Error")
    
    if config.force_token_expire:
        # Simulate expiry by raising 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return current_user

@app.get("/api/products")
async def get_products(current_user: User = Depends(get_current_active_user)):
    # Standard check for mock errors (optional, but good for consistency)
    config = debug_state.get_config()
    if config.force_server_error:
        raise HTTPException(status_code=500, detail="Simulated Server Error")
    if config.force_token_expire:
        raise HTTPException(status_code=401, detail="Token expired")

    return {
        "products": [
            {"id": 1, "name": "Quantum Widget", "price": 99.99},
            {"id": 2, "name": "Hyper Bolt", "price": 14.50},
            {"id": 3, "name": "Flux Capacitor", "price": 1200.00},
            {"id": 4, "name": "Nano Tube", "price": 5.00},
            {"id": 5, "name": "Cyber Neural Net", "price": 2500.00},
            {"id": 6, "name": "Plasmatic Shield", "price": 450.00},
            {"id": 7, "name": "Hololens Emitter", "price": 300.00},
            {"id": 8, "name": "Void Storage", "price": 9999.99},
            {"id": 9, "name": "Gravity Boots", "price": 120.00},
            {"id": 10, "name": "Sonic Screwdriver", "price": 75.00},
        ]
    }

@app.get("/admin/data")
async def read_admin_data(current_user: User = Depends(get_admin_user)):
    return {"message": "Hello Admin", "data": "Top Secret Data"}

@app.get("/public")
async def check_health():
    return {"status": "ok", "message": "Backend is running"}

# Mount frontend directory
# html=True allows serving index.html at root, and other .html files if matched
from fastapi.staticfiles import StaticFiles
import os

# Ensure we're pointing to the right directory relative to this file
current_dir = os.path.dirname(os.path.realpath(__file__))
frontend_dir = os.path.join(current_dir, "..", "frontend")

# Create frontend dir if not exists (to avoid error on startup before files are created)
os.makedirs(frontend_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static")
