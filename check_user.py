
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env vars safely
load_dotenv()

url = os.getenv("SUPABASE_URL", "https://mjohuncbzgzfpyohksex.supabase.co")
key = os.getenv("SUPABASE_KEY")

if not key:
    # Fallback if .env is missing locally
    key = "sb_secret_tlKsBJKFIq0WJfpx-NE3dw_CxNT_YGZ"

print(f"Checking user 'dewantorokuntow@gmail.com' in DB...")
try:
    supabase: Client = create_client(url, key)
    response = supabase.table("users").select("*").eq("email", "dewantorokuntow@gmail.com").execute()
    
    if response.data:
        print("✅ User FOUND in Database:")
        print(response.data)
    else:
        print("❌ User NOT FOUND in Database.")
        # List all users just in case
        all_users = supabase.table("users").select("email").execute()
        print(f"Existing users: {[u['email'] for u in all_users.data]}")

except Exception as e:
    print("Connection Failed:")
    print(e)
