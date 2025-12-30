# 🛡️ High-End Security Hardening Guide

Your backend is now protected with **Rate Limiting**, **Argon2 Hashing**, and **Security Middlewares**. To achieve "High-End" security, you should also harden your VPS (Ubuntu).

---

## 1. 🛑 Fail2Ban (Automatic Bot Blocking)
Fail2Ban monitors your logs and automatically blocks IP addresses that show signs of malicious activity (brute-force).

```bash
sudo apt update
sudo apt install fail2ban -y
```
It will automatically start protecting SSH. It is the best way to stop the "Bot Scans" you saw.

---

## 2. 🧱 UFW Firewall (Strict Mode)
You should ONLY allow the ports you actually use.

```bash
# Reset rules
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (IMPORTANT: Don't lock yourself out!)
sudo ufw allow ssh

# Allow LeadMaps (Port 8000 or 80 if you mapped it)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp

# Enable
sudo ufw enable
```

---

## 3. 🔑 SSH Hardening
Stop hackers from even trying to guess your password.

1. **Disable Password Login**: Force use of your `.pem` key only.
   - Edit `/etc/ssh/sshd_config`
   - Set `PasswordAuthentication no`
   - Restart: `sudo systemctl restart ssh`

2. **Change SSH Port**: Move SSH from port 22 to something high (e.g., 2222). *Note: You will need to update your `.bat` and `.ps1` files if you do this.*

---

## 4. 🧹 Regular Updates
Set up automatic security updates.

```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## 🔒 Current Backend Protections
I have already implemented these in your code:
- **Rate Limiting**: Auth routes are limited to 5-10 requests per minute.
- **Argon2v13**: The most secure password hashing algorithm in existence.
- **CSP & HSTS Headers**: Prevents XSS, Clickjacking, and Protocol Downgrades.
- **Bot Blocker**: Automatically returns 403 Forbidden to bot scanners.
- **Strict CORS**: Only allows your official domains to connect.
