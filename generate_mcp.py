import requests
import json
import time
import os
import sys
import argparse
import signal
from concurrent.futures import ThreadPoolExecutor

# API endpoint
base_url = "http://localhost:8000"

# Global timeout settings
REQUEST_TIMEOUT = 300  # 5 minutes timeout for the request

# Setup argument parser
def parse_args():
    parser = argparse.ArgumentParser(description="Generate MCP server from API documentation")
    parser.add_argument("--doc-url", default="https://jina.ai/deepsearch", 
                      help="URL to the API documentation")
    parser.add_argument("--message", default="Generate MCP server for Deepsearch that allows users to deep search",
                      help="Request message describing what to generate")
    parser.add_argument("--timeout", type=int, default=REQUEST_TIMEOUT,
                      help="Timeout in seconds for the generation request")
    parser.add_argument("--verbose", "-v", action="store_true",
                      help="Enable verbose output")
    parser.add_argument("--email", default="test@example.com",
                      help="Email for authentication")
    parser.add_argument("--password", default="password123",
                      help="Password for authentication")
    parser.add_argument("--skip-auth", action="store_true",
                      help="Skip authentication step")
    return parser.parse_args()

# Handle keyboard interrupt
def timeout_handler(signum, frame):
    print("\n\nOperation timed out or interrupted! The API might still be processing your request.")
    print("Check the server logs for more information.")
    sys.exit(1)

def authenticate(args):
    """
    Authenticate with the server to get a valid session and user ID.
    """
    if args.skip_auth:
        print("Skipping authentication (not recommended for production)")
        return None
    
    # Try to sign in first
    try:
        print(f"Signing in as {args.email}...")
        signin_data = {
            "email": args.email,
            "password": args.password
        }
        
        response = requests.post(f"{base_url}/auth/signin", json=signin_data, timeout=10)
        
        if response.status_code == 200:
            auth_data = response.json()
            if args.verbose:
                print("Authentication response:")
                print(json.dumps(auth_data, indent=2))
                
            if not auth_data.get("session"):
                print("Warning: No session token found in the authentication response")
                print("This may cause Row Level Security (RLS) errors with Supabase")
            else:
                print(f"Successfully signed in as {args.email} (User ID: {auth_data.get('user_id')})")
            
            return auth_data
        else:
            print(f"Sign-in failed with status {response.status_code}")
            try:
                error_details = response.json()
                print(f"Error details: {json.dumps(error_details, indent=2)}")
            except:
                print(f"Raw response: {response.text}")
                
            # Try to sign up instead
            try:
                print(f"Signing up as {args.email}...")
                signup_data = {
                    "email": args.email,
                    "password": args.password,
                    "full_name": "Test User"
                }
                
                response = requests.post(f"{base_url}/auth/signup", json=signup_data, timeout=10)
                
                if response.status_code == 200:
                    auth_data = response.json()
                    if args.verbose:
                        print("Authentication response:")
                        print(json.dumps(auth_data, indent=2))
                        
                    if not auth_data.get("session"):
                        print("Warning: No session token found in the authentication response")
                        print("This may cause Row Level Security (RLS) errors with Supabase")
                    else:
                        print(f"Successfully signed up as {args.email} (User ID: {auth_data.get('user_id')})")
                    
                    return auth_data
                else:
                    print(f"Sign-up failed with status {response.status_code}")
                    try:
                        error_details = response.json()
                        print(f"Error details: {json.dumps(error_details, indent=2)}")
                    except:
                        print(f"Raw response: {response.text}")
                    
                    print("Proceeding without authentication (may not work with RLS)")
                    return None
            except Exception as e:
                print(f"Sign-up error: {str(e)}")
                print("Proceeding without authentication (may not work with RLS)")
                return None
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        print("Proceeding without authentication (may not work with RLS)")
        return None

def generate_mcp_server(args):
    """
    Generate an MCP server from API documentation with improved error handling
    """
    # Authenticate first
    auth_data = authenticate(args)
    
    # Get auth headers if available
    auth_headers = {}
    if auth_data and auth_data.get("session"):
        auth_headers = {
            "Authorization": f"Bearer {auth_data.get('session')}"
        }
        print("Using authenticated session for requests")
    
    # Endpoint for MCP generator
    endpoint = f"{base_url}/generators/generate"
    
    # Request payload with real documentation URL
    payload = {
        "doc_url": args.doc_url,
        "request_message": args.message,
        "api_credentials": {
            "api_key": "jina_acd51f2ce2414643b43119b62567f7dbFlYZe9DLybjxNkUut28Y4kQIG-Hn"  # Example credential
        }
    }
    
    print(f"Sending request to generate MCP server for {args.doc_url}...")
    try:
        # First check if the server is running
        try:
            health_response = requests.get(f"{base_url}/health", timeout=10)
            if health_response.status_code != 200:
                print(f"Error: Server not healthy. Status code: {health_response.status_code}")
                try:
                    print(f"Error details: {json.dumps(health_response.json(), indent=2)}")
                except:
                    print(f"Raw response: {health_response.text}")
                return
                
            print(f"Server health check: {json.dumps(health_response.json(), indent=2)}")
        except requests.exceptions.Timeout:
            print("Error: Health check timed out. The server might be overloaded.")
            return
        
        # Register signal handlers for timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.signal(signal.SIGINT, timeout_handler)
        
        print("\nStarting MCP generation process. This will take a few minutes...")
        print("The process involves three stages:")
        print("1. Documentation processing: Reading and parsing the API docs")
        print("2. Planning: Creating a structured plan for the MCP server")
        print("3. Code generation: Implementing the actual MCP server code")
        print("\nPlease be patient. You can press Ctrl+C to interrupt at any time.\n")
        
        # Start a timer
        start_time = time.time()
        
        # Send the actual generation request with appropriate timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                lambda: requests.post(endpoint, json=payload, headers=auth_headers, timeout=args.timeout)
            )
            
            # Wait for the future to complete with progress indicator
            response = None
            dots = 1
            while not future.done():
                progress = "." * dots
                print(f"\rProcessing{progress.ljust(10)}", end="", flush=True)
                dots = (dots % 10) + 1
                time.sleep(0.5)
                
                # Check if we've been running for too long
                if time.time() - start_time > args.timeout:
                    print("\nRequest is taking longer than expected, but still running...")
                    print("The server might still be processing. Check server logs for more information.")
                    break
            
            # Get the response if the future completed
            if future.done():
                response = future.result()
            else:
                print("\nRequest is still in progress but may be hung...")
                print("Checking for server health to see if it's still processing")
                try:
                    health_check = requests.get(f"{base_url}/health", timeout=5)
                    if health_check.status_code == 200:
                        print("\nServer is still healthy. It might be processing your request in the background.")
                        print("You can check the server logs for more information.")
                    else:
                        print("\nServer health check failed. The server might be experiencing issues.")
                except:
                    print("\nCouldn't check server health. Connection might be lost.")
                
                # Try to determine if template ID was returned
                print("\nAttempting to continue by checking if any templates were created...")
                template_check = requests.get(f"{base_url}/generators/list-templates", timeout=5)
                
                if template_check.status_code == 200:
                    print("\nRequest may be processing. Check the server logs for more details.")
                
                # End the request
                return
        
        if response and response.status_code == 200:
            end_time = time.time()
            elapsed = end_time - start_time
            
            result = response.json()
            print(f"\n\nSuccess! MCP server generation completed in {elapsed:.1f} seconds.")
            print(f"Template ID: {result.get('template_id')}")
            
            # If the result includes a template ID, we can check for the generated files
            template_id = result.get('template_id')
            if template_id:
                template_dir = f"backend/templates/generated/{template_id}"
                print(f"\nGenerated files will be available at: {template_dir}")
                
                # Check if the directory exists
                if os.path.exists(template_dir):
                    print(f"\nGeneration completed! Files are available at: {template_dir}")
                    files = os.listdir(template_dir)
                    print(f"Generated files: {', '.join(files)}")
                else:
                    print("\nNote: Files might be generated asynchronously and not yet available.")
                    print("Check the server logs for more information.")
            
            if args.verbose:
                print("\nFull response:")
                print(json.dumps(result, indent=2))
            else:
                print("\nAdd -v flag for detailed output")
        elif response:
            print(f"\nError: Status code {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Raw response: {response.text}")
        else:
            print("\nNo response received. The request may have timed out.")
            print("Check the server logs for more information.")
    except requests.exceptions.Timeout:
        print("\nError: Request timed out. The server might be overloaded or processing a large request.")
        print("The server might still be processing your request. Check server logs.")
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the server. Is it running?")
    except KeyboardInterrupt:
        print("\n\nOperation interrupted! The API might still be processing your request.")
        print("Check the server logs for more information.")
    except Exception as e:
        print(f"\nException occurred: {str(e)}")

if __name__ == "__main__":
    args = parse_args()
    generate_mcp_server(args) 