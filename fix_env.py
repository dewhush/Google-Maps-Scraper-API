content = """MAIL_FROM=onboarding@resend.dev
MAIL_PASSWORD=re_gigGS3mx_CX8pyx9utdRahVhVeFtJhGXn
SECRET_KEY=leadmaps-secret-key-change-in-production-2024
SUPABASE_URL=https://mjohuncbzgzfpyohksex.supabase.co
SUPABASE_KEY=sb_secret_tlKsBJKFIq0WJfpx-NE3dw_CxNT_YGZ
"""

with open(".env", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated .env with Supabase Keys!")
