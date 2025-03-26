import requests
import json

# API endpoint
base_url = "http://localhost:8000"

def test_health_check():
    """Test the health check endpoint"""
    response = requests.get(f"{base_url}/health")
    print(f"Health Check Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print("=" * 50)

def test_generator_api():
    """Test the generator API (auth required - may not work)"""
    # Endpoint for MCP generator
    endpoint = f"{base_url}/generators/generate"
    
    # Request payload based on router definition
    payload = {
        "doc_url": "https://api.example.com/docs",
        "request_message": "Generate MCP server for Example API",
        "api_credentials": {
            "api_key": "example_key"
        }
    }
    
    # Make the POST request
    try:
        response = requests.post(endpoint, json=payload)
        print(f"Generator API Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
    except json.JSONDecodeError:
        print(f"Response status: {response.status_code}")
        print(f"Raw response: {response.text}")
    print("=" * 50)

def test_without_auth():
    """Test the test endpoint (no auth required)"""
    # Endpoint for test API
    endpoint = f"{base_url}/test/generate"
    
    # Request payload
    payload = {
        "doc_url": "https://api.example.com/docs",
        "request_message": "Generate MCP server for Example API",
        "api_credentials": {
            "api_key": "example_key"
        }
    }
    
    # Make the POST request
    try:
        response = requests.post(endpoint, json=payload)
        print(f"Test API Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
    print("=" * 50)

if __name__ == "__main__":
    # Test the health check endpoint first
    test_health_check()
    
    # Test the generator API (this might fail due to auth requirement)
    test_generator_api()
    
    # Test the endpoint without auth requirement
    test_without_auth() 