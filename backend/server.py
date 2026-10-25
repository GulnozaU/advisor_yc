import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response

# Preview-only bridge: ingress sends /api/* here, forward to the Express app on the frontend port.
EXPRESS_URL = os.environ.get("EXPRESS_URL", "http://127.0.0.1:3000")
app = FastAPI()


@app.api_route("/api/{path:path}", methods=["GET", "POST"])
async def proxy(path: str, request: Request):
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.request(request.method, f"{EXPRESS_URL}/api/{path}", content=await request.body(),
                                 headers={"content-type": request.headers.get("content-type", "application/json")})
    headers = {k: v for k, v in r.headers.items() if k.lower() == "cache-control"}
    return Response(content=r.content, status_code=r.status_code, headers=headers,
                    media_type=r.headers.get("content-type"))
