from datetime import datetime
import os
import json
from typing import Optional

def get_env_var(var_name: str) -> Optional[str]:
    """
    Get environment variable value, handling empty strings as None
    
    Args:
        var_name: Name of the environment variable
        
    Returns:
        The environment variable value or None if not found or empty
    """
    value = os.getenv(var_name)
    if value is None or value.strip() == "":
        return None
    return value

def write_to_log(message: str) -> None:
    """
    Write a message to the logs.txt file in the workbench directory.
    
    Args:
        message: The message to log
    """
    # Get the directory structure
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    workbench_dir = os.path.join(parent_dir, "workbench")
    log_path = os.path.join(workbench_dir, "logs.txt")
    
    # Create workbench directory if it doesn't exist
    os.makedirs(workbench_dir, exist_ok=True)

    # Add timestamp to the log entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"

    # Write to log file
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(log_entry)
        
def save_json(data: dict, filename: str) -> None:
    """
    Save data as JSON to the specified filename in the workbench directory
    
    Args:
        data: Dictionary data to save
        filename: Name of the JSON file to create
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    workbench_dir = os.path.join(parent_dir, "workbench")
    os.makedirs(workbench_dir, exist_ok=True)
    
    filepath = os.path.join(workbench_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    write_to_log(f"Saved data to {filepath}")
    
def load_json(filename: str) -> Optional[dict]:
    """
    Load JSON data from the specified filename in the workbench directory
    
    Args:
        filename: Name of the JSON file to load
        
    Returns:
        Dictionary with the loaded data or None if file doesn't exist
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    workbench_dir = os.path.join(parent_dir, "workbench")
    filepath = os.path.join(workbench_dir, filename)
    
    if not os.path.exists(filepath):
        write_to_log(f"File not found: {filepath}")
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        write_to_log(f"Loaded data from {filepath}")
        return data
    except Exception as e:
        write_to_log(f"Error loading data from {filepath}: {str(e)}")
        return None 