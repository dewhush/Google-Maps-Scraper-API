
content = """MAIL_FROM=onboarding@resend.dev
MAIL_PASSWORD=re_gigGS3mx_CX8pyx9utdRahVhVeFtJhGXn
SUPABASE_KEY=sb_secret
"""
with open('.env', 'w', encoding='utf-8') as f:
    f.write(content)
print("Written .env with UTF-8")
