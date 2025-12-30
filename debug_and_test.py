
import asyncio
import os
import requests
import socket
import time
import subprocess
import sys
from database import supabase

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def check_user():
    email = "dewantorakuntow@gmail.com"
    print(f"Checking for user: {email}")
    try:
        response = supabase.table("users").select("*").eq("email", email).execute()
        if response.data:
            print(f"User found: {response.data[0]['email']}")
        else:
            print("User NOT found in database.")
    except Exception as e:
        print(f"Error checking user: {e}")

def test_endpoints():
    print("\nTesting endpoints...")
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/auth/forgot-password",
        "/api/auth/forgot-password"
    ]
    
    payload = {"email": "dewantorakuntow@gmail.com"}
    
    for ep in endpoints:
        url = f"{base_url}{ep}"
        try:
            print(f"POST {url}")
            resp = requests.post(url, json=payload, timeout=5)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
        except Exception as e:
            print(f"Failed to connect to {url}: {e}")

def main():
    # 1. Check Supabase
    check_user()

    # 2. Check Server
    port = 8000
    server_process = None
    
    if not is_port_in_use(port):
        print(f"\nPort {port} is free. Starting server...")
        # Start server using uvicorn
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("Waiting for server to start...")
        time.sleep(5) # Give it time to startup
    else:
        print(f"\nPort {port} is already in use. Assuming server is running.")

    # 3. Test Endpoints
    try:
        test_endpoints()
    finally:
        if server_process:
            print("Stopping temporary server...")
            server_process.terminate()
            server_process.wait()

if __name__ == "__main__":
    main()
