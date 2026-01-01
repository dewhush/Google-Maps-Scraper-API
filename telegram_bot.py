"""
Telegram Monitoring Bot for LeadMaps API
Features:
- Traffic monitoring & alerts
- Security threat detection
- Server management (restart)
- Scraping status notifications
"""

import os
import asyncio
import subprocess
import sys
import psutil
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional
import httpx
from dotenv import load_dotenv

# Import IP ban tracker from security module (will be available when server runs)
try:
    from security import ip_ban_tracker
except ImportError:
    ip_ban_tracker = None

# Load env vars if running standalone
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8522429008:AAHAQda0tj4oaR0bd8mFy4kQpm-4ekj_TuQ")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "5673885457")

# Base URL for Telegram API
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ==================== TRAFFIC & SECURITY STATS ====================

class TrafficMonitor:
    def __init__(self):
        self.requests_count = 0
        self.requests_per_ip = defaultdict(int)
        self.requests_per_endpoint = defaultdict(int)
        self.failed_logins = defaultdict(int)
        self.blocked_ips = set()
        self.suspicious_patterns = []
        self.errors = []
        self.start_time = datetime.now()
        
        # Thresholds
        self.rate_limit_threshold = 100  # requests per minute per IP
        self.failed_login_threshold = 5   # max failed logins before alert
        
    def log_request(self, ip: str, endpoint: str, method: str, status_code: int):
        """Log a request for monitoring"""
        self.requests_count += 1
        self.requests_per_ip[ip] += 1
        self.requests_per_endpoint[f"{method} {endpoint}"] += 1
        
        # Check for suspicious activity
        if self.requests_per_ip[ip] > self.rate_limit_threshold:
            if ip not in self.blocked_ips:
                self.suspicious_patterns.append({
                    "type": "rate_limit",
                    "ip": ip,
                    "count": self.requests_per_ip[ip],
                    "time": datetime.now().isoformat()
                })
                return True  # Trigger alert
        
        if status_code >= 400:
            self.errors.append({
                "endpoint": endpoint,
                "status": status_code,
                "ip": ip,
                "time": datetime.now().isoformat()
            })
            
        return False
    
    def log_failed_login(self, ip: str, email: str):
        """Log failed login attempt"""
        self.failed_logins[ip] += 1
        if self.failed_logins[ip] >= self.failed_login_threshold:
            self.suspicious_patterns.append({
                "type": "brute_force",
                "ip": ip,
                "attempts": self.failed_logins[ip],
                "email": email,
                "time": datetime.now().isoformat()
            })
            return True  # Trigger alert
        return False
    
    def get_stats(self) -> dict:
        """Get current traffic statistics"""
        uptime = datetime.now() - self.start_time
        return {
            "uptime": str(uptime).split('.')[0],
            "total_requests": self.requests_count,
            "unique_ips": len(self.requests_per_ip),
            "top_endpoints": dict(sorted(
                self.requests_per_endpoint.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]),
            "top_ips": dict(sorted(
                self.requests_per_ip.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]),
            "recent_errors": self.errors[-5:],
            "blocked_ips": list(self.blocked_ips),
            "suspicious_activity": len(self.suspicious_patterns)
        }
    
    def reset_hourly(self):
        """Reset hourly counters"""
        self.requests_per_ip.clear()
        self.failed_logins.clear()


# Global traffic monitor instance
traffic_monitor = TrafficMonitor()


# ==================== CACHE CLEANUP ====================

import shutil
import glob

async def cleanup_cache() -> dict:
    """Clean up temporary files and cache to free disk space"""
    cleaned = {
        "playwright_temp": 0,
        "browser_cache": 0,
        "crash_reports": 0,
        "log_files": 0,
        "total_freed_mb": 0
    }
    
    cleanup_paths = [
        # Playwright temp files
        ("/tmp/playwright*", "playwright_temp"),
        # Browser cache
        ("~/.cache/ms-playwright", "browser_cache"),
        ("~/.config/chromium/Crash*", "crash_reports"),
        # Old log files
        ("/var/log/*.log.1", "log_files"),
        ("/tmp/core*", "crash_reports"),
    ]
    
    total_freed = 0
    
    for pattern, category in cleanup_paths:
        try:
            expanded_pattern = os.path.expanduser(pattern)
            paths = glob.glob(expanded_pattern)
            
            for path in paths:
                try:
                    if os.path.isdir(path):
                        size = get_directory_size(path)
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        size = os.path.getsize(path) if os.path.exists(path) else 0
                        os.remove(path)
                    
                    cleaned[category] += 1
                    total_freed += size
                except Exception as e:
                    print(f"[CLEANUP] Error cleaning {path}: {e}")
        except:
            pass
    
    cleaned["total_freed_mb"] = round(total_freed / (1024 * 1024), 2)
    
    print(f"[CLEANUP] Cleaned {cleaned['total_freed_mb']}MB")
    return cleaned


def get_directory_size(path: str) -> int:
    """Get total size of a directory"""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_directory_size(entry.path)
    except:
        pass
    return total


async def scheduled_cleanup():
    """Run cleanup every 12 hours and notify via Telegram"""
    while True:
        # Wait 12 hours
        await asyncio.sleep(12 * 60 * 60)  # 12 hours in seconds
        
        print("[CLEANUP] Starting scheduled cleanup...")
        result = await cleanup_cache()
        
        # Get disk usage after cleanup
        try:
            disk = psutil.disk_usage('/')
            disk_info = f"{disk.percent}% used ({disk.free // (1024**3)}GB free)"
        except:
            disk_info = "Unknown"
        
        # Send notification
        await send_alert("cache_cleanup", {
            "freed_mb": result["total_freed_mb"],
            "disk_status": disk_info,
            "playwright": result["playwright_temp"],
            "browser_cache": result["browser_cache"],
            "crash_reports": result["crash_reports"]
        })


# ==================== TELEGRAM BOT FUNCTIONS ====================

async def send_telegram_message(chat_id: str, text: str, reply_markup: dict = None):
    """Send a message via Telegram Bot API"""
    if not chat_id:
        print(f"[TELEGRAM] No chat_id set, skipping message")
        return None
    
    async with httpx.AsyncClient() as client:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            import json
            payload["reply_markup"] = json.dumps(reply_markup)
        
        try:
            response = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
            return response.json()
        except Exception as e:
            print(f"[TELEGRAM] Error sending message: {e}")
            return None


def get_main_keyboard():
    """Get main keyboard with buttons"""
    return {
        "keyboard": [
            [{"text": "📊 Server Status"}, {"text": "🎯 Threat Intel"}],
            [{"text": "🔒 Security Report"}, {"text": "🚫 Banned IPs"}],
            [{"text": "⚡ Quick Actions"}, {"text": "🧹 Clean Cache"}],
            [{"text": "📋 Recent Errors"}, {"text": "🔄 Restart Server"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }


async def get_server_status() -> str:
    """Get server status information"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        uptime = datetime.now() - traffic_monitor.start_time
        
        status = f"""
<b>🖥️ Server Status</b>

<b>⏱ Uptime:</b> {str(uptime).split('.')[0]}
<b>💻 CPU:</b> {cpu_percent}%
<b>🧠 Memory:</b> {memory.percent}% ({memory.used // (1024**2)}MB / {memory.total // (1024**2)}MB)
<b>💾 Disk:</b> {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)

<b>📡 API Status:</b> ✅ Running
<b>🔢 Total Requests:</b> {traffic_monitor.requests_count}
<b>👥 Unique IPs:</b> {len(traffic_monitor.requests_per_ip)}
"""
        return status
    except Exception as e:
        return f"❌ Error getting status: {str(e)}"


async def get_threat_intel() -> str:
    """Get threat intelligence dashboard with attack analytics"""
    import json
    from collections import Counter
    
    # Read security events log
    attack_types = Counter()
    attacker_ips = Counter()
    recent_attacks = []
    total_blocked = 0
    
    try:
        if os.path.exists("security_events.json"):
            with open("security_events.json", "r") as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        total_blocked += 1
                        attack_types[event.get("event_type", "UNKNOWN")] += 1
                        attacker_ips[event.get("ip", "unknown")] += 1
                        if len(recent_attacks) < 5:
                            recent_attacks.append(event)
                    except:
                        pass
    except:
        pass
    
    # Get banned count
    banned_count = len(ip_ban_tracker.get_banned_ips()) if ip_ban_tracker else 0
    
    # Format top attack types
    top_attacks = "\n".join([
        f"  • {t}: {c} attacks"
        for t, c in attack_types.most_common(5)
    ]) or "  No attacks recorded"
    
    # Format top attacker IPs
    top_attackers = "\n".join([
        f"  🚨 {ip}: {c} attempts"
        for ip, c in attacker_ips.most_common(5)
    ]) or "  None detected"
    
    # Calculate threat level
    if total_blocked > 100:
        threat_level = "🔴 HIGH"
    elif total_blocked > 20:
        threat_level = "🟡 MEDIUM"
    else:
        threat_level = "🟢 LOW"
    
    return f"""
<b>🎯 Threat Intelligence Dashboard</b>

<b>🛡️ Threat Level:</b> {threat_level}
<b>🚫 Total Attacks Blocked:</b> {total_blocked}
<b>⛔ Currently Banned:</b> {banned_count} IPs

<b>📊 Attack Types:</b>
{top_attacks}

<b>🚨 Top Attackers:</b>
{top_attackers}

<b>🛡️ Protection Status:</b>
  ✅ Auto-ban: ACTIVE (1 violation = 1h ban)
  ✅ Rate limiting: ACTIVE
  ✅ Bot blocking: ACTIVE
  ✅ Path filtering: ACTIVE
"""


async def get_security_report() -> str:
    """Get security report with banned IPs"""
    patterns = traffic_monitor.suspicious_patterns[-10:]
    
    # Get banned IPs from ip_ban_tracker
    banned_list = []
    if ip_ban_tracker:
        banned_list = ip_ban_tracker.get_banned_ips()
    
    if not patterns and not banned_list:
        return """
<b>🔒 Security Report</b>

✅ No suspicious activity detected
✅ No banned IPs
✅ All systems secure
"""
    
    alerts = "\n".join([
        f"  ⚠️ [{p['type']}] IP: {p['ip']} at {p['time'][:19]}"
        for p in patterns[-5:]
    ]) or "  None"
    
    # Format banned IPs
    if banned_list:
        banned_str = "\n".join([
            f"  🚫 {b['ip']} ({b['expires_in']}s left)"
            for b in banned_list[:10]
        ])
    else:
        banned_str = "  None"
    
    return f"""
<b>🔒 Security Report</b>

<b>⚠️ Recent Alerts:</b>
{alerts}

<b>🚫 Banned IPs ({len(banned_list)}):</b>
{banned_str}

<b>🔐 Failed Logins:</b> {sum(traffic_monitor.failed_logins.values())}
<b>🛡️ Auto-Ban:</b> 1 violation = 1 hour ban
"""


async def _perform_restart():
    """Actual restart logic with delay"""
    print("[RESTART] Scheduled restart in 3 seconds...")
    await asyncio.sleep(3)  # Wait for Telegram ACK
    
    try:
        if os.getenv("PM2_HOME") or os.getenv("PM2_USAGE"):
             print("[RESTART] PM2 restart...")
             subprocess.Popen(["pm2", "restart", "server"])
             return

        print("[RESTART] os.execv restart...")
        python = sys.executable
        os.execv(python, [python] + sys.argv)
    except Exception as e:
        print(f"❌ Restart failing: {e}")

async def restart_server():
    """Trigger server restart"""
    try:
        # Notify user
        await send_telegram_message(ADMIN_CHAT_ID, "<b>🔄 Restarting Server...</b>\n\n<i>This may take a few seconds.</i>")
        
        # Schedule restart in background so we can return and ACK the message
        asyncio.create_task(_perform_restart())
        
        return "Restart sequence initiated."
        
    except Exception as e:
        return f"❌ Restart failed: {str(e)}"


async def get_scraping_status() -> str:
    """Get current scraping status"""
    # This will be called from server.py which has access to scraping_state
    return """
<b>🕷️ Scraping Status</b>

<i>Send /scrape_status from the API or check the dashboard.</i>

To get real-time status, this needs to be integrated with server.py.
"""


async def handle_telegram_update(update: dict):
    """Handle incoming Telegram update"""
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = str(message["chat"]["id"])
    text = message.get("text", "")
    
    # Set admin chat ID if not set
    global ADMIN_CHAT_ID
    if not ADMIN_CHAT_ID:
        ADMIN_CHAT_ID = chat_id
        print(f"[TELEGRAM] Admin chat ID set to: {chat_id}")
    
    response = ""
    
    if text == "/start" or text == "ℹ️ Help":
        response = "Use the buttons below to monitor your server."
    
    elif text == "📊 Server Status":
        response = await get_server_status()
    
    elif text == "🎯 Threat Intel":
        response = await get_threat_intel()
    
    elif text == "⚡ Quick Actions":
        response = """
<b>⚡ Quick Actions</b>

Use these commands:

<b>🔓 Unban an IP:</b>
  /unban 123.45.67.89

<b>🔍 Check IP status:</b>
  /check 123.45.67.89

<b>🗑️ Clear security log:</b>
  /clearlog

<b>📊 View attack stats:</b>
  /stats
"""
    
    elif text == "🔒 Security Report":
        response = await get_security_report()
    
    elif text == "🔄 Restart Server":
        response = await restart_server()
    
    elif text == "🚫 Banned IPs":
        if ip_ban_tracker:
            banned = ip_ban_tracker.get_banned_ips()
            if banned:
                banned_str = "\n".join([
                    f"  🚫 <code>{b['ip']}</code>\n     ⏳ {b['expires_in'] // 60}m {b['expires_in'] % 60}s remaining"
                    for b in banned[:15]
                ])
                response = f"""
<b>🚫 Currently Banned IPs ({len(banned)})</b>

{banned_str}

<i>Bans expire after 1 hour</i>
"""
            else:
                response = """
<b>🚫 Banned IPs</b>

✅ No IPs are currently banned

<i>IPs get auto-banned for 1 hour on first malicious request</i>
"""
        else:
            response = "⚠️ IP ban tracker not available"
    
    elif text == "🧹 Clean Cache":
        response = "<b>🧹 Cleaning Cache...</b>\n\nPlease wait..."
        await send_telegram_message(chat_id, response, get_main_keyboard())
        
        # Run cleanup
        result = await cleanup_cache()
        
        # Get disk status
        try:
            disk = psutil.disk_usage('/')
            disk_info = f"{disk.percent}% used ({disk.free // (1024**3)}GB free)"
        except:
            disk_info = "Unknown"
        
        response = f"""
<b>🧹 Cache Cleanup Complete!</b>

<b>📊 Cleaned:</b>
  • Playwright temp: {result['playwright_temp']} files
  • Browser cache: {result['browser_cache']} files
  • Crash reports: {result['crash_reports']} files

<b>💾 Freed:</b> {result['total_freed_mb']} MB
<b>💿 Disk Status:</b> {disk_info}

<i>Auto cleanup runs every 12 hours</i>
"""
    
    elif text == "📋 Recent Errors":
        errors = traffic_monitor.errors[-10:]
        if errors:
            response = "<b>📋 Recent Errors:</b>\n" + "\n".join([
                f"  • {e['status']} {e['endpoint']} from {e['ip'][:15]}"
                for e in errors
            ])
        else:
            response = "✅ No recent errors"
    
    # Quick Action Commands
    elif text.startswith("/unban "):
        ip = text.replace("/unban ", "").strip()
        if ip_ban_tracker and ip_ban_tracker.unban_ip(ip):
            response = f"✅ <b>IP Unbanned:</b> <code>{ip}</code>"
        else:
            response = f"⚠️ IP <code>{ip}</code> was not in the ban list"
    
    elif text.startswith("/check "):
        ip = text.replace("/check ", "").strip()
        if ip_ban_tracker:
            if ip_ban_tracker.is_banned(ip):
                remaining = ip_ban_tracker.get_ban_remaining(ip)
                response = f"""
<b>🔍 IP Status: <code>{ip}</code></b>

🚫 <b>Status:</b> BANNED
⏳ <b>Time remaining:</b> {remaining // 60}m {remaining % 60}s
"""
            else:
                violations = ip_ban_tracker.get_violation_count(ip)
                response = f"""
<b>🔍 IP Status: <code>{ip}</code></b>

✅ <b>Status:</b> Not banned
⚠️ <b>Recent violations:</b> {violations}
"""
        else:
            response = "⚠️ IP ban tracker not available"
    
    elif text == "/clearlog":
        try:
            if os.path.exists("security_events.json"):
                os.remove("security_events.json")
                response = "✅ <b>Security log cleared!</b>"
            else:
                response = "ℹ️ Security log is already empty"
        except Exception as e:
            response = f"❌ Error clearing log: {str(e)}"
    
    elif text == "/stats":
        response = await get_threat_intel()
    
    else:
        response = "Unknown command. Use the buttons below or send /start for help."
    
    await send_telegram_message(chat_id, response, get_main_keyboard())


# ==================== ALERT FUNCTIONS ====================

async def send_alert(alert_type: str, data: dict):
    """Send an alert to admin"""
    if not ADMIN_CHAT_ID:
        return
    
    if alert_type == "rate_limit":
        message = f"""
⚠️ <b>RATE LIMIT ALERT</b>

<b>IP:</b> <code>{data.get('ip', 'unknown')}</code>
<b>Requests:</b> {data.get('count', 0)} in 1 minute
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Consider blocking this IP.
"""
    
    elif alert_type == "security_block":
        auto_banned = data.get('auto_banned', False)
        ban_msg = "\n\n🚫 <b>IP AUTO-BANNED FOR 1 HOUR!</b>" if auto_banned else ""
        message = f"""
🛑 <b>SECURITY BLOCK</b>

<b>IP:</b> <code>{data.get('ip', 'unknown')}</code>
<b>Path:</b> <code>{data.get('path', 'unknown')}</code>
<b>Query:</b> {data.get('query', '')[:50]}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>Attacker/Bot scanner blocked</i>{ban_msg}
"""
    
    elif alert_type == "brute_force":
        message = f"""
🚨 <b>BRUTE FORCE ALERT</b>

<b>IP:</b> <code>{data.get('ip', 'unknown')}</code>
<b>Failed Attempts:</b> {data.get('attempts', 0)}
<b>Target Email:</b> {data.get('email', 'unknown')}
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<b>Action:</b> IP has been flagged.
"""
    
    elif alert_type == "scrape_complete":
        message = f"""
✅ <b>SCRAPING COMPLETE</b>

<b>Query:</b> {data.get('query', 'unknown')}
<b>Results:</b> {data.get('count', 0)} contacts
<b>Duration:</b> {data.get('duration', 'unknown')}
"""
    
    elif alert_type == "scrape_error":
        message = f"""
❌ <b>SCRAPING ERROR</b>

<b>Query:</b> {data.get('query', 'unknown')}
<b>Error:</b> {data.get('error', 'unknown')}
"""
    
    elif alert_type == "server_start":
        message = f"""
🟢 <b>LeadMaps Server is Online!</b>

<b>⏰ Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>📡 Status:</b> All systems running

<b>🔧 Active Services:</b>
  • API Server: ✅ Running
  • Telegram Bot: ✅ Connected  
  • Traffic Monitor: ✅ Active
  • Auto Cleanup: ✅ Scheduled (12h)

<b>🌐 Endpoints:</b>
  • API: https://api.leadmaps.web.id
  • Docs: /docs

<i>Ready to extract leads! 🚀</i>
"""
    
    elif alert_type == "cache_cleanup":
        message = f"""
🧹 <b>SCHEDULED CACHE CLEANUP</b>

<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>Freed:</b> {data.get('freed_mb', 0)} MB
<b>Disk Status:</b> {data.get('disk_status', 'Unknown')}

<b>Cleaned:</b>
  • Playwright temp: {data.get('playwright', 0)} files
  • Browser cache: {data.get('browser_cache', 0)} files
  • Crash reports: {data.get('crash_reports', 0)} files

<i>Next cleanup in 12 hours</i>
"""
    
    else:
        message = f"ℹ️ Alert: {alert_type}\n{data}"
    
    await send_telegram_message(ADMIN_CHAT_ID, message)


# ==================== WEBHOOK HANDLER FOR FASTAPI ====================

async def telegram_webhook_handler(update: dict):
    """Handle webhook updates from Telegram"""
    try:
        await handle_telegram_update(update)
    except Exception as e:
        print(f"[TELEGRAM] Error handling update: {e}")


# ==================== POLLING MODE (for testing) ====================

async def start_polling():
    """Start polling for updates (for testing without webhook)"""
    print(f"[TELEGRAM] Starting bot polling...")
    print(f"[TELEGRAM] Admin Chat ID: {ADMIN_CHAT_ID}")
    print(f"[CLEANUP] Scheduled cleanup will run every 12 hours")
    
    offset = 0
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Clear any existing webhook to allow polling
        try:
            await client.get(f"{TELEGRAM_API}/deleteWebhook")
            print("[TELEGRAM] Webhook cleared")
        except Exception as e:
            print(f"[TELEGRAM] Warning: Could not clear webhook: {e}")

        while True:
            try:
                response = await client.get(
                    f"{TELEGRAM_API}/getUpdates",
                    params={"offset": offset, "timeout": 30}
                )
                data = response.json()
                
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        await handle_telegram_update(update)
                
            except Exception as e:
                print(f"[TELEGRAM] Polling error: {e}")
                await asyncio.sleep(5)


async def main():
    """Run both polling and scheduled cleanup"""
    # Start both tasks concurrently
    polling_task = asyncio.create_task(start_polling())
    cleanup_task = asyncio.create_task(scheduled_cleanup())
    
    # Send startup notification
    await send_alert("server_start", {})
    
    # Wait for both (they run forever)
    await asyncio.gather(polling_task, cleanup_task)


if __name__ == "__main__":
    print("=" * 50)
    print("LeadMaps Telegram Monitor Bot")
    print("=" * 50)
    print(f"Bot Token: {BOT_TOKEN[:20]}...")
    print(f"Admin Chat: {ADMIN_CHAT_ID}")
    print("Features: Traffic Monitor, Security Alerts, Cache Cleanup")
    print("=" * 50)
    asyncio.run(main())
