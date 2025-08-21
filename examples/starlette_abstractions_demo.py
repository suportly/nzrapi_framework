"""
Starlette Abstractions Demo

This example demonstrates how nzrapi abstracts Starlette components
so users don't need to import from Starlette directly.

Key benefits:
1. Cleaner imports - everything from nzrapi
2. Framework independence - easier to switch implementations
3. Consistent API - nzrapi controls the interface
4. Future-proof - internal changes don't affect user code
"""

from nzrapi import (  # Core framework; Request/Response abstractions (no starlette imports needed!); WebSocket abstractions; Middleware abstractions; Type safety
    CORSMiddleware,
    FileResponse,
    HTMLResponse,
    JSONResponse,
    Middleware,
    NzrApiApp,
    Path,
    PlainTextResponse,
    Query,
    RedirectResponse,
    Router,
    StreamingResponse,
    WebSocket,
    WebSocketEndpoint,
    WebSocketManager,
)

# Create app with CORS middleware using abstractions
app = NzrApiApp(
    title="Starlette Abstractions Demo",
    description="Demonstrates nzrapi abstractions over Starlette",
    version="1.0.0",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ],
)

router = Router(prefix="/api", tags=["demo"])


@router.get("/json")
async def json_response_demo():
    """Demonstrates JSONResponse abstraction"""
    return JSONResponse(
        {
            "message": "This JSONResponse comes from nzrapi, not Starlette!",
            "abstraction": "nzrapi.JSONResponse",
            "underlying": "starlette.responses.JSONResponse",
            "benefit": "Users don't need to know about Starlette",
        }
    )


@router.get("/html")
async def html_response_demo():
    """Demonstrates HTMLResponse abstraction"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>nzrapi HTMLResponse Demo</title>
    </head>
    <body>
        <h1>🎉 HTML Response from nzrapi!</h1>
        <p>This HTMLResponse is abstracted from Starlette.</p>
        <p>Users import from <code>nzrapi</code>, not <code>starlette.responses</code>.</p>
    </body>
    </html>
    """
    return HTMLResponse(html_content)


@router.get("/text")
async def text_response_demo():
    """Demonstrates PlainTextResponse abstraction"""
    return PlainTextResponse("This is plain text from nzrapi.PlainTextResponse!")


@router.get("/redirect")
async def redirect_demo():
    """Demonstrates RedirectResponse abstraction"""
    return RedirectResponse("/api/json")


@router.get("/stream")
async def streaming_demo():
    """Demonstrates StreamingResponse abstraction"""

    def generate_data():
        for i in range(10):
            yield f"data chunk {i}\n"

    return StreamingResponse(generate_data(), media_type="text/plain")


# WebSocket abstractions demo
ws_manager = WebSocketManager()


class EchoWebSocketEndpoint(WebSocketEndpoint):
    """Demonstrates WebSocketEndpoint abstraction"""

    async def on_receive(self, websocket: WebSocket, connection_id: str, data):
        """Echo received messages"""
        try:
            message = f"Echo from nzrapi WebSocket: {data}"
            await self.manager.send_personal_message(
                connection_id,
                {
                    "type": "echo",
                    "message": message,
                    "abstraction_info": {
                        "websocket_class": "nzrapi.WebSocket",
                        "endpoint_class": "nzrapi.WebSocketEndpoint",
                        "manager_class": "nzrapi.WebSocketManager",
                        "no_starlette_imports": True,
                    },
                },
            )
        except Exception as e:
            await websocket.send_json({"type": "error", "message": f"Error: {e}"})


# Register WebSocket endpoint
app.websocket("/ws")(EchoWebSocketEndpoint(ws_manager))

# Include router
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint explaining the demo"""
    return JSONResponse(
        {
            "title": "🎯 Starlette Abstractions Demo",
            "description": "nzrapi provides clean abstractions over Starlette components",
            "benefits": [
                "No direct Starlette imports needed",
                "Framework independence",
                "Consistent nzrapi API",
                "Future-proof applications",
                "Cleaner code organization",
            ],
            "endpoints": {
                "GET /": "This endpoint - demo info",
                "GET /api/json": "JSONResponse abstraction demo",
                "GET /api/html": "HTMLResponse abstraction demo",
                "GET /api/text": "PlainTextResponse abstraction demo",
                "GET /api/redirect": "RedirectResponse abstraction demo",
                "GET /api/stream": "StreamingResponse abstraction demo",
                "WS /ws": "WebSocket abstractions demo",
            },
            "abstractions_provided": [
                "JSONResponse",
                "HTMLResponse",
                "PlainTextResponse",
                "RedirectResponse",
                "FileResponse",
                "StreamingResponse",
                "WebSocket",
                "WebSocketDisconnect",
                "WebSocketManager",
                "WebSocketEndpoint",
                "Middleware",
                "CORSMiddleware",
            ],
            "code_comparison": {
                "before": "from starlette.responses import JSONResponse",
                "after": "from nzrapi import JSONResponse",
                "benefit": "Cleaner imports, framework independence",
            },
        }
    )


@app.get("/health")
async def health():
    """Health check using abstractions"""
    return JSONResponse(
        {"status": "healthy", "framework": "nzrapi", "abstraction_layer": "active", "starlette_hidden": True}
    )


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Starlette Abstractions Demo")
    print("📍 Key improvement: No direct Starlette imports needed!")
    print("")
    print("🎯 Benefits achieved:")
    print("  ✅ Framework independence")
    print("  ✅ Cleaner imports (everything from nzrapi)")
    print("  ✅ Consistent API surface")
    print("  ✅ Future-proof applications")
    print("")
    print("🔗 Try these endpoints:")
    print("  - GET  / - Demo overview")
    print("  - GET  /api/json - JSONResponse demo")
    print("  - GET  /api/html - HTMLResponse demo")
    print("  - WS   /ws - WebSocket demo")
    print("")
    print("Visit http://localhost:8000/docs for full API docs")

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
