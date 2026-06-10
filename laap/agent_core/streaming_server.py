"""SSE流式HTTP服务器 — 支持实时Agent输出"""
import sys, os, time, json as _json, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from http.server import HTTPServer, BaseHTTPRequestHandler

# Global agent instance
_agent = None
def get_agent():
    global _agent
    if _agent is None:
        from laap.agent_core.agent import Agent, AgentConfig
        _agent = Agent(AgentConfig(
            name="LAAP-Stream", enable_memory=True, enable_tools=True,
            system_prompt="你是LAAP智能体，用中文回答，简洁准确。"))
        key = os.environ.get("LAAP_API_KEY", "")
        if key:
            _agent.llm.config.api_key = key
            _agent.llm.config.api_base = os.environ.get("LAAP_API_BASE", "https://api.deepseek.com/v1")
            _agent.llm.config.model = os.environ.get("LAAP_MODEL", "deepseek-v4-flash")
    return _agent

class SSEHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/stream'):
            import urllib.parse
            params = urllib.parse.parse_qs(self.path.split('?')[1] if '?' in self.path else '')
            msg = params.get('msg', [''])[0]
            if not msg:
                self._send_json({"error": "missing msg"})
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            agent = get_agent()
            for event_type, data in agent.stream_chat(msg):
                if event_type == "token":
                    payload = _json.dumps({"token": data}, ensure_ascii=False)
                    self.wfile.write(("data: " + payload + "\n\n").encode())
                elif event_type == "done":
                    payload = _json.dumps({"done": True, "content": data}, ensure_ascii=False)
                    self.wfile.write(("data: " + payload + "\n\n").encode())
                elif event_type == "error":
                    payload = _json.dumps({"error": data}, ensure_ascii=False)
                    self.wfile.write(("data: " + payload + "\n\n").encode())
                self.wfile.flush()
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html_path = os.path.join(os.path.dirname(__file__), 'chat.html')
            if os.path.exists(html_path):
                self.wfile.write(open(html_path, 'rb').read())
            else:
                self.wfile.write(b"<h1>chat.html not found</h1>")
        elif self.path == '/health':
            self._send_json({"status": "ok", "agent": str(get_agent().state.value)})
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(_json.dumps(data).encode())
    
    def log_message(self, format, *args):
        pass

def run_server(host='0.0.0.0', port=8765):
    server = HTTPServer((host, port), SSEHandler)
    print(f"SSE Streaming server: http://{host}:{port}")
    print(f"  Stream: http://localhost:{port}/stream?msg=你好")
    print(f"  Chat:   http://localhost:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == '__main__':
    run_server()
