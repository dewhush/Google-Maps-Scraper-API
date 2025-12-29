import os
import resend
from dotenv import load_dotenv
from datetime import datetime

# Load .env
load_dotenv()

# Setup Resend
resend.api_key = os.getenv("MAIL_PASSWORD")
# Test with the domain you said was verified
sender = "team@leadmaps.web.id"

def get_otp_email_html(otp: str) -> str:
    """Generate aesthetic HTML email content"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verification Code</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f6f9fc;
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
                overflow: hidden;
            }}
            .header {{
                background-color: #4285F4;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 24px;
                font-weight: 600;
            }}
            .content {{
                padding: 40px 30px;
                text-align: center;
            }}
            .description {{
                color: #555555;
                font-size: 16px;
                line-height: 1.5;
                margin-bottom: 30px;
            }}
            .otp-box {{
                background-color: #f0f7ff;
                border: 2px dashed #4285F4;
                border-radius: 8px;
                padding: 20px;
                margin: 0 auto 30px;
                display: inline-block;
            }}
            .otp-code {{
                font-family: 'Courier New', monospace;
                font-size: 32px;
                font-weight: bold;
                color: #4285F4;
                letter-spacing: 4px;
                margin: 0;
            }}
            .warning {{
                background-color: #fff8e1;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                text-align: left;
                font-size: 14px;
                color: #856404;
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 20px;
                text-align: center;
                color: #888888;
                font-size: 12px;
                border-top: 1px solid #eeeeee;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Lead Maps</h1>
            </div>
            <div class="content">
                <h2>Verify your email address</h2>
                <p class="description">
                    Thanks for starting your registration. Please use the following verification code to complete your signup procedure.
                </p>
                
                <div class="otp-box">
                    <p class="otp-code">{otp}</p>
                </div>

                <div class="warning">
                    <strong>Security Notice:</strong> Please do not share this code with anyone. Lead Maps employees will never ask for your password or verification code.
                </div>
                
                <p class="description" style="font-size: 14px; margin-top: 30px;">
                    This code is valid for 10 minutes. If you didn't request this, you can safely ignore this email.
                </p>
            </div>
            <div class="footer">
                &copy; {datetime.now().year} Lead Maps. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

print(f"Testing Resend Configuration...")
print(f"API Key: {resend.api_key[:5]}..." if resend.api_key else "API Key: MISSING")
print(f"Sender: {sender}")

try:
    print("Attempting to send email to dewantorokuntow@gmail.com... with HTML template")
    
    otp = "123456" # Test OTP
    
    params = {
        "from": f"Lead Maps Team <{sender}>",
        "to": ["dewantorokuntow@gmail.com"],
        "subject": "Verification Code (Test Script)",
        "html": get_otp_email_html(otp)
    }
    
    email = resend.Emails.send(params)
    print("SUCCESS! Email Sent.")
    print(email)
except Exception as e:
    print("\nERROR FAILED:")
    print(e)
