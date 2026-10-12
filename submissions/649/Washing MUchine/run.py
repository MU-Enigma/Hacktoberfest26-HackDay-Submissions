import os
import socket
import subprocess
import sys

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

if __name__ == "__main__":
    print("📦 Bootstrapping Washing MUchine Environment...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    local_ip = get_ip()
    print("\n" + "="*50)
    print("🚀 WASHING MUCHINE IS LIVE!")
    print(f"🖥️  Local Dashboard:  http://localhost:5000")
    print(f"📱 Dorm Network URL: http://{local_ip}:5000")
    print("="*50 + "\n")
    
    os.system(f"{sys.executable} app.py")
