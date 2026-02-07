from django.conf import settings
from django.core.mail import EmailMultiAlternatives
import random

def send_otp(email):
    otp = str(random.randint(100000, 999999))

    subject = "🔐 SkillLink – Verify Your Email"
    from_email = settings.EMAIL_HOST_USER
    to = [email]

    text_content = f"""
    Your OTP for SkillLink registration is {otp}.
    This OTP is valid for 10 minutes.
    """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body {{
          background-color: #f4f6f8;
          font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
          margin: 0;
          padding: 0;
        }}
        .container {{
          max-width: 520px;
          margin: 40px auto;
          background: #ffffff;
          border-radius: 12px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.08);
          overflow: hidden;
        }}
        .header {{
          background: linear-gradient(135deg, #f9b934, #c68a14);
          padding: 20px;
          text-align: center;
          color: #111;
          font-size: 22px;
          font-weight: 700;
        }}
        .content {{
          padding: 30px;
          color: #333;
        }}
        .otp {{
          margin: 25px 0;
          text-align: center;
          font-size: 32px;
          letter-spacing: 6px;
          font-weight: bold;
          color: #c68a14;
        }}
        .info {{
          font-size: 14px;
          color: #555;
          line-height: 1.6;
        }}
        .footer {{
          background: #f8fafc;
          padding: 15px;
          text-align: center;
          font-size: 12px;
          color: #777;
        }}
        .brand {{
          font-weight: 700;
          color: #c68a14;
        }}
      </style>
    </head>

    <body>
      <div class="container">
        <div class="header">
          SkillLink Verification
        </div>

        <div class="content">
          <p>Hi 👋,</p>

          <p class="info">
            Thank you for registering on <span class="brand">SkillLink</span>.
            Please use the OTP below to verify your email address.
          </p>

          <div class="otp">{otp}</div>

          <p class="info">
            ⏱ This OTP is valid for <b>10 minutes</b>.<br>
            If you didn’t request this, you can safely ignore this email.
          </p>
        </div>

        <div class="footer">
          © {2026} <span class="brand">SkillLink</span><br>
          Connecting Skills, Empowering Students
        </div>
      </div>
    </body>
    </html>
    """

    email_message = EmailMultiAlternatives(
        subject,
        text_content,
        from_email,
        to,
    )
    email_message.attach_alternative(html_content, "text/html")
    email_message.send(fail_silently=False)

    return otp

