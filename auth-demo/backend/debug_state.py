from typing import Optional
from pydantic import BaseModel

class DebugConfig(BaseModel):
    force_login_error: Optional[str] = None  # "invalid_password", "user_not_found", "server_error", "success"(or None)
    force_token_expire: bool = False
    force_server_error: bool = False

class DebugState:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DebugState, cls).__new__(cls)
            cls._instance.config = DebugConfig()
        return cls._instance

    def update(self, new_config: dict):
        # Update only provided fields
        current_data = self.config.dict()
        current_data.update(new_config)
        self.config = DebugConfig(**current_data)

    def get_config(self) -> DebugConfig:
        return self.config

    def reset(self):
        self.config = DebugConfig()

debug_state = DebugState()
