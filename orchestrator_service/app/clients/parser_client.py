import os, httpx

PARSER_URL = os.getenv("PARSER_URL", "http://localhost:8001")


async def parse(code: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(f"{PARSER_URL}/parse", json={"code": code})
        r.raise_for_status()
        return r.json()


async def semantic(ast: dict) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(f"{PARSER_URL}/semantic", json={"ast": ast})
        r.raise_for_status()
        return r.json()
