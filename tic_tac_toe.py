import threading
import time
import webbrowser
from app import app

def open_browser():
    """Waits for the server to start, then automatically opens the web game in the default browser."""
    time.sleep(1.5)
    print("\nOpening game in your browser at http://127.0.0.1:5000/ ...\n")
    webbrowser.open("http://127.0.0.1:5000/")

if __name__ == "__main__":
    print("=========================================")
    print("      NEON TIC-TAC-TOE WEB LAUNCHER      ")
    print("=========================================")
    print("Starting local Flask web server...")
    
    # Start thread to open browser
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Start the server (debug=False avoids double loading thread)
    app.run(debug=False, port=5000)
