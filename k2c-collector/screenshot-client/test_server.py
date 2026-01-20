"""스크린샷 업로드를 받는 간단한 테스트 서버."""

import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler


class UploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        # 이미지 크기 계산
        size_kb = len(body) / 1024

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 스크린샷 수신: {size_kb:.1f} KB")

        # 성공 응답
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def log_message(self, format, *args):
        pass  # 기본 로그 비활성화


if __name__ == "__main__":
    port = 8000
    server = HTTPServer(("0.0.0.0", port), UploadHandler)
    print(f"테스트 서버 시작: http://localhost:{port}/upload")
    print("Ctrl+C로 종료\n")
    server.serve_forever()
