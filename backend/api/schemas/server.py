from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

# Request Models
class ServerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    credentials: Dict[str, Any] = Field(default_factory=dict)

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

# Response Models
class ServerBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    template_id: str
    status: str
    deployment_url: Optional[str] = None
    version: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_deployed_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class ServerDetails(ServerBase):
    config: Dict[str, Any]
    # Note: Credentials are not included in the response for security reasons

class ServerList(BaseModel):
    servers: List[ServerBase]
    total: int 