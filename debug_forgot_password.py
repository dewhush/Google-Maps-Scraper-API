
import asyncio
from database import supabase
import requests

def check_user():
    email = "dewantorakuntow@gmail.com"
    print(f"Checking for user: {email}")
    try:
        response = supabase.table("users").select("*").eq("email", email).execute()
        if response.data:
            print("User found:", response.data[0])
        else:
            print("User NOT found in database.")
    except Exception as e:
        print(f"Error checking user: {e}")

def test_endpoint():
    print("\nTesting /auth/forgot-password endpoint...")
    url = "http://localhost:8000/auth/forgot-password" # Assuming port 8000 based on standard fastapi
    # Also try the one with /api prefix
    
    payload = {"email": "dewantorakuntow@gmail.com"}
    
    try:
        resp = requests.post(url, json=payload)
        print(f"Response ({url}): {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error hitting {url}: {e}")

    url2 = "http://localhost:8000/api/auth/forgot-password"
    try:
        resp = requests.post(url2, json=payload)
        print(f"Response ({url2}): {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error hitting {url2}: {e}")

if __name__ == "__main__":
    check_user()
    test_endpoint()
