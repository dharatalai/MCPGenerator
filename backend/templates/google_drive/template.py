"""
Google Drive MCP Server Template
This template creates an MCP server that provides access to Google Drive files.
"""
from mcp.server.fastmcp import FastMCP
import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Initialize FastMCP
mcp = FastMCP("Google Drive")

# Set up Google Drive client
def initialize_drive_client(credentials_json):
    """Initialize Google Drive client with provided credentials."""
    credentials_data = json.loads(credentials_json)
    credentials = Credentials.from_authorized_user_info(credentials_data)
    return build("drive", "v3", credentials=credentials)

# Load credentials from environment
credentials_json = os.environ.get("GOOGLE_CREDENTIALS")
drive_service = None if not credentials_json else initialize_drive_client(credentials_json)

@mcp.tool()
async def list_files(query: str = "", max_results: int = 10):
    """
    List files from Google Drive with optional query.
    
    Args:
        query: Search query in Google Drive query format.
        max_results: Maximum number of results to return.
        
    Returns:
        List of files matching the query.
    """
    if not drive_service:
        return {"error": "Google Drive client not initialized."}
    
    try:
        results = drive_service.files().list(
            q=query,
            pageSize=max_results,
            fields="files(id, name, mimeType, webViewLink)"
        ).execute()
        
        files = results.get("files", [])
        return {"files": files}
    except HttpError as error:
        return {"error": f"An error occurred: {error}"}

@mcp.tool()
async def get_file_content(file_id: str):
    """
    Get the content of a specific Google Drive file.
    
    Args:
        file_id: The ID of the file to retrieve.
        
    Returns:
        The content of the file if it's text or a link for other file types.
    """
    if not drive_service:
        return {"error": "Google Drive client not initialized."}
    
    try:
        # Get file metadata
        file_metadata = drive_service.files().get(fileId=file_id, fields="name,mimeType").execute()
        
        # Check if it's a Google Docs file
        mime_type = file_metadata.get("mimeType", "")
        
        if mime_type.startswith("application/vnd.google-apps"):
            # For Google Docs, return a link
            file_link = f"https://drive.google.com/file/d/{file_id}/view"
            return {
                "name": file_metadata.get("name"),
                "mime_type": mime_type,
                "link": file_link,
                "message": "This is a Google Docs file, use the link to view it."
            }
        
        # For text files, we could download the content
        # (Implementation would depend on the specific requirements)
        return {
            "name": file_metadata.get("name"),
            "mime_type": mime_type,
            "link": f"https://drive.google.com/file/d/{file_id}/view",
            "message": "File content retrieval for binary files is not implemented in this template."
        }
    except HttpError as error:
        return {"error": f"An error occurred: {error}"}

if __name__ == "__main__":
    mcp.run(transport="stdio") 