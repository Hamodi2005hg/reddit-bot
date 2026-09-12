import os
import sys
import threading
import http.server
import socketserver
import subprocess
import time

PORT = int(os.environ.get("PORT", 3000))

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Reddit Bot is running and healthy!")

def run_server():
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), HealthHandler) as httpd:
            print(f"Health check server running on port {PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Health check server error: {e}")

def run_bot():
    while True:
        print("Starting Reddit bot runner in verbose mode...")
        # Use python unbuffered (-u), verbose mode, and default accounts/links files
        cmd = [sys.executable, "-u", "main.py", "--verbose", "-a", "accounts.txt", "-l", "links.txt"]
        # If user passed arguments to start.py, pass them along
        if len(sys.argv) > 1:
            cmd.extend(sys.argv[1:])
        
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("Reddit bot execution completed successfully.")
            # Sleep 1 hour before re-running if it completed successfully
            time.sleep(3600)
        else:
            print(f"Reddit bot exited with code {result.returncode}. Retrying in 60 seconds...")
            time.sleep(60)

if __name__ == "__main__":
    # Start health check server in background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Run bot loop
    run_bot()
