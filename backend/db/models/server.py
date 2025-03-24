from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from ..database import Base

def generate_uuid():
    return str(uuid.uuid4())

class MCPServer(Base):
    """Model representing an MCP server instance."""
    __tablename__ = "mcp_servers"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text)
    template_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    status = Column(String, default="created")  # created, building, deployed, error
    
    # Server details
    deployment_url = Column(String)
    version = Column(String)
    
    # Server configuration (stored as JSON)
    config = Column(JSON)
    
    # API keys and credentials (encrypted in production)
    credentials = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_deployed_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<MCPServer(name='{self.name}', status='{self.status}')>" 