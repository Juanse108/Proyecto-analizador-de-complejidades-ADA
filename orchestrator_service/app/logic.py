from .clients import parser_client, analyzer_client


async def analyze_pipeline(code: str, objective="worst", cost_model=None):
    parsed = await parser_client.parse(code)
    ast = parsed["ast"]
    sem = await parser_client.semantic(ast)
    result = await analyzer_client.analyze_ast(sem["ast_sem"], objective, cost_model)
    return result
