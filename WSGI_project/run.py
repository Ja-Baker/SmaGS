from wsgiref.simple_server import make_server
from app import application
import os

def start_dev_server():
    host = "127.0.0.1"
    port = 5001
    
    print("-" * 30)
    print(" SmaGS DEVELOPMENT SERVER ")
    print(f" Listening at: http://{host}:{port}")
    print(" Press Ctrl+C to shut down.")
    print("-" * 30)
    
    # Ensure your static and template directories exist locally
    if not os.path.exists('static\css'):
        

        print("Warning: 'static/css' directory not found. Themes may not load.")
    try:
        httpd = make_server(host, port, application)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")

if __name__ == "__main__":
    start_dev_server()