import os, httpx

ANALYZER_URL = os.getenv("ANALYZER_URL", "http://localhost:8002")


async def analyze_ast(ast_sem: dict, objective: str = "worst", cost_model=None) -> dict:
    payload = {"ast": ast_sem, "objective": objective, "cost_model": cost_model}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(f"{ANALYZER_URL}/analyze-ast", json=payload)
        r.raise_for_status()
        return r.json()
