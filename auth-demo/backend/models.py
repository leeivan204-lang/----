from typing import Dict

# Mock Database
# In a real app, this would be a SQL/NoSQL database connection

class UserInDB:
    def __init__(self, username: str, hashed_password: str, disabled: bool = False, role: str = "user"):
        self.username = username
        self.hashed_password = hashed_password
        self.disabled = disabled
        self.role = role

# In-memory user store
fake_users_db: Dict[str, dict] = {
    "johndoe": {
        "username": "johndoe",
        "hashed_password": "$2b$12$khOEnvbGqPSml50BMSAjFeb09MtxM6Skx1PAJdf0p/u1YM3yTs7Be", # "secret"
        "disabled": False,
        "role": "user",
    },
    "alice": {
        "username": "alice",
        "hashed_password": "$2b$12$khOEnvbGqPSml50BMSAjFeb09MtxM6Skx1PAJdf0p/u1YM3yTs7Be", # "secret"
        "disabled": False,
        "role": "admin",
    },
}
