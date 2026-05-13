import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
MCP_URL  = os.getenv("MCP_URL")


def _parse_sse(text: str) -> dict:
    try:
        if text.startswith("event:"):
            for line in text.splitlines():
                if line.startswith("data: "):
                    return json.loads(line[6:])
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}


def mcp(tool: str, arguments: dict | None = None) -> dict:
    if arguments is None:
        arguments = {}
    body = {
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    try:
        r = requests.post(
            MCP_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30,
        )
        return _parse_sse(r.text)
    except Exception as e:
        return {"error": str(e)}
