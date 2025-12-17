"""
Start the web-based recommendation system server
"""
import subprocess
import sys
from pathlib import Path

def start_server():
    """Start Flask server"""
    web_dir = Path(__file__).parent / "web"
    app_file = web_dir / "app.py"

    print("Starting web-based recommendation system...")
    print(f"Server will be available at: http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")

    # Run Flask app
    subprocess.run([sys.executable, str(app_file)])

if __name__ == "__main__":
    start_server()
