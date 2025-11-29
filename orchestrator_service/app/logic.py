from .clients import parser_client, analyzer_client

async def analyze_pipeline(code: str, objective: str = "worst", cost_model=None):
    # 1. Llamar al Parser
    parsed_res = await parser_client.parse(code)
    
    if not parsed_res.get("ok"):
        # Manejo básico de error si el parser falla
        raise ValueError(f"Error de sintaxis: {parsed_res.get('errors')}")

    ast = parsed_res["ast"]

    # 2. Llamar al análisis semántico
    sem_res = await parser_client.semantic(ast)
    # Aquí podrías validar 'issues' en sem_res si quisieras

    ast_sem = sem_res["ast_sem"]

    # 3. Llamar al Core Analyzer
    result = await analyzer_client.analyze_ast(ast_sem, objective, cost_model)
    
    return result