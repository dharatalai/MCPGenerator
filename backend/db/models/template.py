from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
import uuid
from ..database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Template(Base):
    """Model representing an MCP server template."""
    __tablename__ = "templates"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)  # e.g., "data-source", "tool", "custom"
    
    # Template configuration
    template_path = Column(String, nullable=False)  # Path to template files
    version = Column(String)
    is_public = Column(Boolean, default=True)
    
    # Required fields for the template (stored as JSON schema)
    config_schema = Column(JSON)
    
    # Template metadata
    created_by = Column(String)  # User ID of creator
    requires_approval = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Template(name='{self.name}', category='{self.category}')>" 