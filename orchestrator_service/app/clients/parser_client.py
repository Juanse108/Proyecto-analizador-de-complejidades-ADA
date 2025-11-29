import os
import httpx

PARSER_URL = os.getenv("PARSER_URL", "http://localhost:8001")

async def parse(code: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{PARSER_URL}/parse", json={"code": code})
        resp.raise_for_status()
        return resp.json()

async def semantic(ast: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{PARSER_URL}/semantic", json={"ast": ast})
        resp.raise_for_status()
        return resp.json()