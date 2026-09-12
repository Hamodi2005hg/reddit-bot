"""Flask Web Control Panel for Reddit Bot on Render/Railway with Cloud Interactive Browser."""

import os
import json
import threading
import subprocess
import sys
import time
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# Global log buffer
LOG_BUFFER = []
MAX_LOG_LINES = 500

# Global Interactive Selenium Driver Session
INTERACTIVE_DRIVER = None

def log_message(msg: str):
    print(msg, flush=True)
    LOG_BUFFER.append(msg)
    if len(LOG_BUFFER) > MAX_LOG_LINES:
        LOG_BUFFER.pop(0)

def get_accounts_info():
    username = ""
    password = ""
    accounts_file = Path("accounts.txt")
    if accounts_file.exists():
        try:
            line = accounts_file.read_text().strip()
            if "|" in line:
                username, password = line.split("|", 1)
        except Exception:
            pass
    return username, password

@app.route("/")
def index():
    username, password = get_accounts_info()
    logs = "\n".join(LOG_BUFFER) if LOG_BUFFER else "No logs yet. Click 'Run Bot Now' or wait for background execution."
    return render_template("index.html", username=username, password=password, logs=logs)

@app.route("/api/logs")
def api_logs():
    return jsonify({"logs": "\n".join(LOG_BUFFER) if LOG_BUFFER else "No logs yet."})

@app.route("/save_account", methods=["POST"])
def save_account():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    if username and password:
        accounts_file = Path("accounts.txt")
        accounts_file.write_text(f"{username}|{password}\n")
        log_message(f"[WEB] Updated account credentials for: {username}")
    return redirect(url_for("index"))

@app.route("/save_cookies", methods=["POST"])
def save_cookies():
    cookies_json = request.form.get("cookies_json", "").strip()
    username, _ = get_accounts_info()
    if not username:
        username = "AppropriateChance699"
        
    if cookies_json:
        try:
            cookies = json.loads(cookies_json)
            session_dir = Path("sessions")
            session_dir.mkdir(parents=True, exist_ok=True)
            session_file = session_dir / f"{username}.cookies"
            session_file.write_text(json.dumps(cookies, indent=2))
            log_message(f"[WEB] Successfully saved session cookies for {username}")
        except Exception as e:
            log_message(f"[WEB] Error parsing cookies JSON: {e}")
            
    return redirect(url_for("index"))

@app.route("/run_bot", methods=["POST"])
def run_bot_endpoint():
    log_message("[WEB] Manual bot execution triggered from Control Panel...")
    threading.Thread(target=execute_bot_subprocess, daemon=True).start()
    return redirect(url_for("index"))

# --- Cloud Interactive Browser Routes ---

@app.route("/start_interactive_login", methods=["POST"])
def start_interactive_login():
    global INTERACTIVE_DRIVER
    log_message("[WEB] Starting cloud interactive browser session...")
    try:
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        if INTERACTIVE_DRIVER:
            try:
                INTERACTIVE_DRIVER.quit()
            except Exception:
                pass
                
        INTERACTIVE_DRIVER = uc.Chrome(options=options, use_subprocess=True, version_main=None)
        INTERACTIVE_DRIVER.get("https://www.reddit.com/login/")
        time.sleep(3)
        
        os.makedirs("static", exist_ok=True)
        INTERACTIVE_DRIVER.save_screenshot("static/screenshot.png")
        log_message("[WEB] Cloud browser session booted and navigated to Reddit login.")
    except Exception as e:
        log_message(f"[WEB] Failed to start interactive browser: {e}")
        
    return redirect(url_for("interactive_login_page"))

@app.route("/interactive_login")
def interactive_login_page():
    global INTERACTIVE_DRIVER
    username, password = get_accounts_info()
    current_url = "Not started"
    screenshot_exists = os.path.exists("static/screenshot.png")
    
    if INTERACTIVE_DRIVER:
        try:
            current_url = INTERACTIVE_DRIVER.current_url
            INTERACTIVE_DRIVER.save_screenshot("static/screenshot.png")
            screenshot_exists = True
        except Exception:
            screenshot_exists = False
            
    return render_template(
        "interactive_login.html",
        username=username,
        password=password,
        current_url=current_url,
        screenshot_exists=screenshot_exists,
        timestamp=time.time()
    )

@app.route("/interactive_action", methods=["POST"])
def interactive_action():
    global INTERACTIVE_DRIVER
    action = request.form.get("action")
    
    if not INTERACTIVE_DRIVER:
        log_message("[WEB] No active interactive browser session.")
        return redirect(url_for("interactive_login_page"))
        
    try:
        if action == "refresh":
            INTERACTIVE_DRIVER.refresh()
            time.sleep(2)
        elif action == "navigate":
            target_url = request.form.get("url", "https://www.reddit.com/login/")
            INTERACTIVE_DRIVER.get(target_url)
            time.sleep(3)
        elif action == "type_credentials":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            
            # Find and fill username
            try:
                u_el = INTERACTIVE_DRIVER.find_element("name", "username")
                u_el.clear()
                u_el.send_keys(username)
            except Exception:
                try:
                    u_el = INTERACTIVE_DRIVER.find_element("id", "loginUsername")
                    u_el.clear()
                    u_el.send_keys(username)
                except Exception:
                    pass
                    
            # Find and fill password
            try:
                p_el = INTERACTIVE_DRIVER.find_element("name", "password")
                p_el.clear()
                p_el.send_keys(password)
                p_el.submit()
            except Exception:
                try:
                    p_el = INTERACTIVE_DRIVER.find_element("id", "loginPassword")
                    p_el.clear()
                    p_el.send_keys(password)
                    p_el.submit()
                except Exception:
                    pass
            time.sleep(4)
            
        INTERACTIVE_DRIVER.save_screenshot("static/screenshot.png")
    except Exception as e:
        log_message(f"[WEB] Error in interactive action: {e}")
        
    return redirect(url_for("interactive_login_page"))

@app.route("/interactive_click", methods=["POST"])
def interactive_click():
    global INTERACTIVE_DRIVER
    if not INTERACTIVE_DRIVER:
        return jsonify({"status": "error", "message": "No active driver"})
        
    try:
        x = int(request.form.get("x", 0))
        y = int(request.form.get("y", 0))
        
        INTERACTIVE_DRIVER.execute_script(f"""
            var el = document.elementFromPoint({x}, {y});
            if (el) {{
                el.click();
            }}
        """)
        
        time.sleep(2)
        INTERACTIVE_DRIVER.save_screenshot("static/screenshot.png")
        log_message(f"[WEB] Clicked interactive browser at ({x}, {y})")
        return jsonify({"status": "success"})
    except Exception as e:
        log_message(f"[WEB] Error in interactive click: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route("/interactive_save_cookies", methods=["POST"])
def interactive_save_cookies():
    global INTERACTIVE_DRIVER
    username, _ = get_accounts_info()
    if not username:
        username = "AppropriateChance699"
        
    if INTERACTIVE_DRIVER:
        try:
            cookies = INTERACTIVE_DRIVER.get_cookies()
            session_dir = Path("sessions")
            session_dir.mkdir(parents=True, exist_ok=True)
            session_file = session_dir / f"{username}.cookies"
            session_file.write_text(json.dumps(cookies, indent=2))
            log_message(f"[WEB] Successfully exported {len(cookies)} cookies from cloud browser for {username}")
            INTERACTIVE_DRIVER.quit()
            INTERACTIVE_DRIVER = None
        except Exception as e:
            log_message(f"[WEB] Error saving cookies from cloud browser: {e}")
            
    return redirect(url_for("index"))

# --- Subprocess Execution ---

def execute_bot_subprocess():
    try:
        cmd = [sys.executable, "-u", "main.py", "--verbose", "-a", "accounts.txt", "-l", "links.txt"]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            log_message(line.strip())
        process.wait()
        log_message(f"[WEB] Bot process finished with exit code {process.returncode}")
    except Exception as e:
        log_message(f"[WEB] Error running bot subprocess: {e}")

def run_web_dashboard(port=3000):
    log_message(f"Starting Flask Web Control Panel on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
