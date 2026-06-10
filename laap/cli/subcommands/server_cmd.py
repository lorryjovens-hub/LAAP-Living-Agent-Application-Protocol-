"""Server — 启动SSE流式服务器"""
def run(args):
    port = getattr(args, 'port', 8765)
    from laap.agent_core.streaming_server import run_server
    print(f"Starting SSE server on :{port}...")
    run_server(port=port)
