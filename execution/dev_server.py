import http.server
import socketserver
import os
import sys

# public 폴더 경로 설정 (상대 경로 기준)
# 이 스크립트가 실행될 때, `execution` 폴더 밖에서 `python execution/dev_server.py`로 실행됨을 상정합니다.
PUBLIC_DIR = os.path.join(os.getcwd(), 'public')
PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

def start_server():
    if not os.path.exists(PUBLIC_DIR):
        print(f"Error: {PUBLIC_DIR} does not exist.")
        sys.exit(1)

    print(f"Starting server at http://localhost:{PORT}")
    print(f"Serving from: {PUBLIC_DIR}")
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()
            sys.exit(0)

if __name__ == "__main__":
    start_server()
