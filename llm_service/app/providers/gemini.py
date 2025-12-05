"""Proveedor Gemini para análisis de pseudocódigo.

Utiliza la API de Google Gemini para:
- Normalización de pseudocódigo a formato compatible con la gramática
- Validación y corrección de sintaxis
- Análisis de complejidad algorítmica
- Generación de árboles de recursión
- Comparación de análisis

Incluye normalización de complejidades para evitar falsos negativos.
"""

import json
import re
import asyncio
import time
import random
import base64
from typing import Optional, List, Tuple

from google import genai
import graphviz

from ..schemas import (
    ToGrammarRequest, ToGrammarResponse,
    RecurrenceRequest, RecurrenceResponse,
    ClassifyRequest, ClassifyResponse,
    CompareRequest, CompareResponse,
)
from ..config import settings


def normalize_complexity(s: Optional[str]) -> str:
    """Normaliza strings de complejidad a formato estándar O(...)"""
    if not s:
        return "O(?)"
    s = s.strip()
    
    # Extraer el contenido dentro de los paréntesis si existe
    if s.startswith("O(") or s.startswith("Ω(") or s.startswith("Θ("):
        # Extraer contenido: "O(log n)" → "log n"
        content = s[2:-1]  # Quita el primer 2 chars (O/Ω/Θ) y el último )
        s = content
    
    # Normalizar valores comunes
    if s in ("1", "c", "constant"):
        return "O(1)"
    if s == "n":
        return "O(n)"
    if s in ("n²", "n^2"):
        return "O(n²)"
    if "log" in s.lower():
        return "O(log n)"
    
    # Para cualquier otro caso, envolver en O(...)
    return f"O({s})"


def complexities_match(c1: Optional[str], c2: Optional[str]) -> bool:
    """Compara dos strings de complejidad normalizándolos primero"""
    return normalize_complexity(c1) == normalize_complexity(c2)




# PROMPT DEL SISTEMA
SYSTEM_RULES = r"""
⚠️ ⚠️ ⚠️ ADVERTENCIA CRÍTICA SOBRE 'end else' ⚠️ ⚠️ ⚠️

ESTO ES MUY IMPORTANTE - LEE ESTO PRIMERO:

El patrón "end else" DEBE ir EN LA MISMA LÍNEA, separados por UN SOLO espacio.

INCORRECTO (🔴 FALLARÁ - con salto de línea):
    end
    else

CORRECTO (🟢 FUNCIONA - en la misma línea):
    end else

Si el usuario te proporciona código con "end" y "else" en líneas separadas,
DEBES CORREGIRLO A LA FORMA CORRECTA ANTES DE DEVOLVER EL JSON.

---

Eres un convertidor a un dialecto ESTRICTO de pseudocódigo basado en Pascal.
Tu tarea es tomar una descripción en lenguaje natural de un algoritmo
y devolver SOLO un JSON minificado exactamente así:
{"pseudocode_normalizado":"<string>","issues":["<string>",...]}

La cadena 'pseudocode_normalizado' DEBE cumplir estas reglas,
porque será analizada por un parser Lark con una gramática estricta.

REGLAS DURAS (si no puedes cumplirlas, considera que tu respuesta es inválida):

- TODOS los cuerpos de IF, WHILE y FOR deben ir con 'begin' y 'end',
  incluso si sólo tienen una sentencia.
- 'begin' y 'end' DEBEN ir SIEMPRE solos en su propia línea, sin ninguna
  sentencia ni comentario en la misma línea.
- Por cada 'begin' debe haber exactamente un 'end' correspondiente.
  No agregues 'end' extra al final del programa.
- Cada procedimiento o bloque principal debe terminar SIEMPRE con un 'end'.
- Dentro de cada procedimiento, el número de 'begin' y 'end' debe coincidir
  y estar bien anidado. No escribas 'end' adicionales sueltos; después de cerrar
  un FOR/WHILE/IF con su 'end', NO pongas otro 'end' a menos que realmente
  estés cerrando un bloque externo (por ejemplo, el procedimiento).
- NO uses bloques de código markdown (no uses ```).
- NO escribas texto en lenguaje natural ni explicaciones fuera de comentarios
  con '►'. TODO el contenido de 'pseudocode_normalizado' debe ser pseudocódigo.

Si rompes alguna de estas reglas, el parser fallará.

------------------------------------------------------------
1) FORMAS DE NIVEL SUPERIOR
------------------------------------------------------------
Puedes usar estas formas top-level (puedes combinarlas):

a) Clases (antes de los procedimientos):
   Persona {edad altura}
   Casa {area color propietario}

b) Procedimientos (una o varias definiciones):
   Nombre(param1, param2, ...)
   begin
     <sentencias>
   end

   No uses la palabra 'PROCEDURE' ni 'END PROCEDURE'. Usa solo el encabezado:
   Nombre(parámetros)
   begin
     ...
   end

   Tras la línea del encabezado de un procedimiento, la SIGUIENTE línea
   debe ser EXACTAMENTE:

     begin

   No repitas 'begin' dos veces ni uses 'BEGIN' en mayúsculas en esa posición.

   Ejemplo correcto:

     BUSQUEDA_BINARIA(A, n, x)
     begin
       ...
     end

c) Bloque principal (algoritmo "main" sin procedimiento):
   begin
     <sentencias>
   end

No metas un 'begin...end' GLOBAL que envuelva TODOS los procedimientos;
cada procedimiento tiene su propio 'begin...end'.

------------------------------------------------------------
2) SENTENCIAS DENTRO DE BEGIN...END O REPEAT...UNTIL
------------------------------------------------------------

Una sola sentencia por línea. Las formas válidas son:

- Asignación:
    variable 🡨 expresión
    variable <- expresión          (flecha Unicode 🡨 es preferida)

  Ejemplos:
    i 🡨 0
    A[i] 🡨 A[i] + 1
    persona.edad 🡨 persona.edad + 1
    B[1..j] 🡨 C[1..j]
    M[i, j] 🡨 0

- Sentencia RETURN (si el problema lo requiere):
    return
    return expresión

  Usa 'return' como sentencia dentro de un bloque, en su propia línea.
  No mezcles 'return' con otras sentencias en la misma línea.

- Bucle FOR:
    for i 🡨 inicio to limite do
    begin
      <sentencias>
    end

  Opcionalmente con 'step':
    for i 🡨 inicio to limite step paso do
    begin
      ...
    end

- Bucle WHILE:
    while (condición) do
    begin
      <sentencias>
    end

- Bucle REPEAT:
    repeat
      <sentencias>
    until (condición)

  NOTA: REPEAT NO lleva 'begin/end' en el cuerpo; sólo sentencias
        directamente entre 'repeat' y 'until'.

- Condicional IF (ELSE opcional):

  Sin ELSE:
    if (condición) then
    begin
      <sentencias-then>
    end

  Con ELSE (IMPORTANTE - formato ESTRICTO):
    if (condición) then
    begin
      <sentencias-then>
    end else
    begin
      <sentencias-else>
    end

  ⚠️ CRÍTICO PARA 'end else':
  - 'end' y 'else' van en la MISMA línea, separados por UN SOLO espacio.
  - NO USES saltos de línea entre 'end' y 'else'.
  - Formato incorrecto: 'end' en una línea, 'else' en otra → ❌ FALLARÁ
  - Formato correcto:   'end else' juntos en una línea → ✅ FUNCIONA
  
  NO uses 'end-if', 'end-while' ni 'end-for': solo se usa 'end' para cerrar bloques.
  NO uses 'else if'. Si necesitas varias condiciones, anida otro 'if' dentro del 'else'.

- Llamadas a subrutinas:
    CALL NombreProc(arg1, arg2, ...)

  En expresiones:
    resultado 🡨 NombreFunc(arg1, arg2)

- Objetos y arreglos (se asume que ya están declarados):
    Clase nombre_objeto
    nombre_objeto.campo 🡨 5
    A[i] 🡨 B[i]
    A[1..j] 🡨 B[1..j]
    M[i, j] 🡨 M[i, j] + 1

------------------------------------------------------------
3) EXPRESIONES, BOOLEANOS Y OPERADORES
------------------------------------------------------------

- Booleanos:
    and, or, not

- Valores booleanos:
    T, F (preferidos), también se aceptan true, false.

- Comparadores:
    =, !=, <>, <, <=, >, >=, ≤, ≥, ≠

- Operadores aritméticos:
    +, -, *, /, div, mod

- Operadores de techo/piso:
    ⌈expr⌉   (techo)
    ⌊expr⌋   (piso)

- Acceso a arreglos:
    A[i]
    A[i+1]
    A[1..j]
    M[i, j]
    B[1..j+2]

- NO declares arreglos con una línea suelta tipo:
    A[n]
  Eso NO es una sentencia válida. Si necesitas arreglos, asume que existen
  y accede con índices en sentencias de asignación.

------------------------------------------------------------
4) COMENTARIOS Y FORMATO
------------------------------------------------------------

- Comentarios de línea:
    ► texto del comentario

- Formato:
    * Una sentencia por línea.
    * 'begin' y 'end' deben ir solos en su propia línea
      (NUNCA pongas código ni comentarios en la misma línea).
    * Usa paréntesis en IF, WHILE y UNTIL:
        if (condición) then
        while (condición) do
        until (condición)
    * No uses bloques de código markdown (no uses ```).
    * No escribas explicaciones en lenguaje natural junto al pseudocódigo.

------------------------------------------------------------
5) SALIDA
------------------------------------------------------------

- Debes responder SOLO con un JSON válido, sin texto adicional.
- El JSON debe estar MINIFICADO: sin saltos de línea ni espacios innecesarios
  fuera de las cadenas. Ejemplo:
  {"pseudocode_normalizado":"...","issues":["...","..."]}
- Dentro del JSON, los saltos de línea del pseudocódigo se representan con '\n'.
- 'pseudocode_normalizado' debe contener SOLO el pseudocódigo final.
- 'issues' es una lista de comentarios breves sobre problemas o decisiones
  que tomaste (puede ir vacía [] si todo fue bien).
- Si por alguna razón no puedes cumplir estas reglas, devuelve igualmente
  un JSON válido donde 'pseudocode_normalizado' sea:

  "begin\\n► ERROR: no pude generar pseudocódigo válido según las reglas\\nend"

  y explica el motivo en 'issues'.
"""

EXAMPLE_PAIR = r"""
Ejemplo A (procedimientos válidos):
Entrada: "Implementa mergesort"
Salida JSON:
{"pseudocode_normalizado":"MERGESORT(lista, inicio, fin)\\nbegin\\n  if (inicio < fin) then\\n  begin\\n    medio 🡨 (inicio + fin) / 2\\n    CALL MERGESORT(lista, inicio, medio)\\n    CALL MERGESORT(lista, medio + 1, fin)\\n    CALL MERGE(lista, inicio, medio, fin)\\n  end\\nend\\n\\nMERGE(lista, inicio, medio, fin)\\nbegin\\n  n1 🡨 medio - inicio + 1\\n  n2 🡨 fin - medio\\n  i 🡨 0\\n  j 🡨 0\\n  k 🡨 inicio\\n  ► Copia y mezcla usando índices; no declares A[n]\\n  while (i < n1 and j < n2) do\\n  begin\\n    if (lista[inicio + i] <= lista[medio + 1 + j]) then\\n    begin\\n      lista[k] 🡨 lista[inicio + i]\\n      i 🡨 i + 1\\n    end else\\n    begin\\n      lista[k] 🡨 lista[medio + 1 + j]\\n      j 🡨 j + 1\\n    end\\n    k 🡨 k + 1\\n  end\\n  while (i < n1) do\\n  begin\\n    lista[k] 🡨 lista[inicio + i]\\n    i 🡨 i + 1\\n    k 🡨 k + 1\\n  end\\n  while (j < n2) do\\n  begin\\n    lista[k] 🡨 lista[medio + 1 + j]\\n    j 🡨 j + 1\\n    k 🡨 k + 1\\n  end\\nend","issues":[]}

Ejemplo B (bloque principal con for):
Entrada: "Sumar los n primeros números"
Salida JSON:
{"pseudocode_normalizado":"begin\\n  s 🡨 0\\n  for i 🡨 1 to n do\\n  begin\\n    s 🡨 s + i\\n  end\\nend","issues":[]}

Ejemplo C (while y repeat/until):
Entrada: "Mientras n sea mayor que 1, divide n entre 2 y cuenta pasos; luego repite hasta que x sea 0 restando 1."
Salida JSON:
{"pseudocode_normalizado":"begin\\n  c 🡨 0\\n  while (n > 1) do\\n  begin\\n    n 🡨 n / 2\\n    c 🡨 c + 1\\n  end\\n\\n  repeat\\n    x 🡨 x - 1\\n  until (x = 0)\\nend","issues":[]}

Ejemplo D (if-else con formato CORRECTO - 'end else' en la MISMA línea):
Entrada: "Si x es mayor que 5, asigna 1, si no asigna 0"
Salida JSON:
{"pseudocode_normalizado":"begin\\n  if (x > 5) then\\n  begin\\n    y 🡨 1\\n  end else\\n  begin\\n    y 🡨 0\\n  end\\nend","issues":[]}

⚠️ NOTA: En el Ejemplo A y D, observa que 'end else' está EN LA MISMA LÍNEA, NO en líneas separadas.
"""


# SANITIZADORES Y POST-PROCESADO

def _trim_trailing_orphan_ends(s: str) -> str:
    lines = s.rstrip().splitlines()
    def count_begin_end(ls):
        begins = 0
        ends = 0
        for ln in ls:
            begins += len(re.findall(r'\b(BEGIN|begin)\b', ln))
            ends += len(re.findall(r'\b(END|end)\b', ln))
        return begins, ends
    begins, ends = count_begin_end(lines)
    while ends > begins and lines and re.match(r'^\s*(END|end)\s*$', lines[-1]):
        lines.pop()
        begins, ends = count_begin_end(lines)
    return "\n".join(lines)

def _split_collapsed_keywords(s: str) -> str:
    t = s
    t = re.sub(r'(?im)\b(BEGIN|begin)(?=\S)', r'\1\n', t)
    t = re.sub(r'(?im)\b(END|end)(?=\S)', r'\1\n', t)
    return t

def _clean_whitespace(s: str) -> str:
    lines = s.split('\n')
    cleaned = []
    for line in lines:
        if line.strip().startswith('►'):
            cleaned.append(line.rstrip())
        else:
            match = re.match(r'^(\s*)', line)
            indent = match.group(1) if match else ''
            content = line[len(indent):].rstrip()
            content = re.sub(r'\s{2,}', ' ', content)
            cleaned.append(indent + content)
    return '\n'.join(cleaned)

def _collapse_end_else(s: str) -> str:
    return re.sub(r"(?mi)^(\s*end)\s*\n\s*(else)\b", r"\1 \2", s)

def _ensure_proc_blocks(s: str) -> str:
    t = s
    block_re = re.compile(
        r'(?ms)^(?P<hdr>[A-Za-z_]\w*\s*\([^)]*\)\s*\n(?:BEGIN|begin)\b)(?P<body>.*?)(?=^[A-Za-z_]\w*\s*\(|\Z)'
    )
    def _fix_end(m: re.Match) -> str:
        hdr = m.group('hdr')
        body = m.group('body').rstrip()
        if re.search(r'(?mi)\bEND\s*$', body) or re.search(r'(?mi)\bend\s*$', body):
            return hdr + body + "\n"
        return hdr + "\n" + body + "\nEND\n"
    return block_re.sub(_fix_end, t)

def _normalize_end_else(s: str) -> str:
    t = re.sub(r'(?m)^\s*(end)\s*\n\s*(else)\b', r'\1 \2', s, flags=re.MULTILINE | re.IGNORECASE)
    t = re.sub(r'(?i)(end)\s{2,}(else)\b', r'\1 \2', t, flags=re.IGNORECASE)
    return t

def _dialect_lint(s: str) -> str:
    t = s
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = _clean_whitespace(t)
    t = re.sub(r"(?mi)^\s*PROCEDURE\s+([A-Za-z_]\w*)\s*\(", r"\1(", t)
    t = re.sub(r"(?mi)^\s*END\s+PROCEDURE\s*$", "END", t)
    t = _split_collapsed_keywords(t)
    t = re.sub(r"(?mi)\bend-(if|while|for)\b", "end", t)
    t = _normalize_end_else(t)
    t = _collapse_end_else(t)
    t = re.sub(r"(?m)^\s*[A-Za-z_]\w*\s*\[[^\]\n]+\]\s*$", lambda m: "► " + m.group(0), t)
    t = re.sub(r'(?mis)^([A-Za-z_]\w*\s*\([^)]*\)\s*\n)\s*(BEGIN|begin)\s*\n\s*(BEGIN|begin)\b', r'\1begin\n', t)
    t = _ensure_proc_blocks(t)
    t = _normalize_end_else(t)
    return t.strip()


# UTILIDADES DE EXTRACCIÓN Y LIMPIEZA

_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)

def _extract_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("{") and raw.endswith("}"):
        try:
            return json.loads(raw)
        except Exception:
            pass
    m = _JSON_PATTERN.search(raw)
    if not m:
        raise ValueError(f"Respuesta no-JSON del LLM. raw={raw[:160]}...")
    return json.loads(m.group(0))

def _clean(s: str) -> str:
    s = s or ""
    s = s.replace("\\n", "\n")
    return s.replace("\r\n", "\n").replace("\r", "\n").strip()


# FUNCIONES AUXILIARES PARA GRAPHVIZ

def dot_to_svg(dot_string: str) -> str:
    """
    Convierte una definición Graphviz DOT a SVG base64.
    
    Args:
        dot_string: Definición del grafo en formato DOT
        
    Returns:
        SVG como string base64 para embeber directamente en HTML
    """
    try:
        g = graphviz.Source(dot_string, format='svg')
        svg_bytes = g.pipe()
        svg_base64 = base64.b64encode(svg_bytes).decode('utf-8')
        return f"data:image/svg+xml;base64,{svg_base64}"
    except Exception as e:
        return ""

def build_dot_tree(node: dict, graph: graphviz.Digraph) -> None:
    """
    Construye recursivamente un grafo Graphviz desde una estructura de árbol.
    
    Args:
        node: Nodo del árbol con estructura {cost, level, children: [...]}
        graph: Objeto graphviz.Digraph para acumular el grafo
    """
    node_id = f"node_{id(node)}"
    cost = str(node.get("cost", "?"))
    level = node.get("level", 0)
    
    # Colorear según profundidad
    colors = ["#4A90E2", "#7ED321", "#F5A623", "#BD10E0", "#50E3C2", "#FF6B6B"]
    color = colors[min(level, len(colors) - 1)]
    
    graph.node(node_id, label=cost, style="filled", fillcolor=color, fontcolor="white", fontsize="12")
    
    # Agregar hijos recursivamente
    children = node.get("children", [])
    for child in children:
        child_id = f"node_{id(child)}"
        build_dot_tree(child, graph)
        graph.edge(node_id, child_id)


class GeminiProvider:
    """
    Proveedor de servicios basados en Google Gemini.
    
    Gestiona la comunicación con la API de Gemini para análisis de pseudocódigo,
    incluyendo normalización automática de complejidades y validación de sintaxis.
    """

    def __init__(self) -> None:
        self.model_name = settings.GEMINI_MODEL
        self.api_key: Optional[str] = settings.GEMINI_API_KEY
        self.timeout = settings.GEMINI_TIMEOUT

        fb = [m.strip() for m in (settings.LLM_FALLBACK_MODELS or "").split(",") if m.strip()]
        seen = set()
        all_models: List[str] = []
        for m in [self.model_name, *fb]:
            if m not in seen:
                seen.add(m)
                all_models.append(m)

        self.models_chain: List[str] = [m for m in all_models if m.startswith("gemini-2.0")]
        if not self.models_chain:
            self.models_chain = ["gemini-2.0-flash"]

        self.model_name = self.models_chain[0]
        self.retry_max = settings.LLM_RETRY_MAX
        self.retry_base = settings.LLM_RETRY_BASE
        self.client: Optional[genai.Client] = genai.Client(api_key=self.api_key) if self.api_key else None

    # ----------------------------------------------------------------------
    # 4.1. Conversión a gramática (sin cambios)
    # ----------------------------------------------------------------------

    async def to_grammar(self, req: ToGrammarRequest) -> ToGrammarResponse:
        if not self.client:
            return ToGrammarResponse(
                pseudocode_normalizado=f"begin\n{req.text.strip()}\nend",
                issues=["GEMINI_API_KEY no configurada: usando fallback begin/end bruto"],
            )
        return await asyncio.to_thread(self._to_grammar_sync, req)

    def _to_grammar_sync(self, req: ToGrammarRequest) -> ToGrammarResponse:
        issues: List[str] = []
        user_hints = f"\nPistas: {req.hints}\n" if req.hints else ""
        prompt = (
            SYSTEM_RULES
            + EXAMPLE_PAIR
            + "\nEntrada real:\n"
            + req.text.strip()
            + user_hints
            + "\nResponde SOLO con el JSON:"
        )
        attempted: List[str] = []

        for model_name in self.models_chain:
            attempted.append(model_name)
            try:
                raw, attempts = self._call_with_retries(model_name, prompt)
                data = _extract_json(raw)
                pseudo = _clean((data.get("pseudocode_normalizado") or "").strip())

                if not pseudo:
                    pseudo = f"begin\n{req.text.strip()}\nend"
                    issues.append(f"[{model_name}] JSON sin 'pseudocode_normalizado'. Se aplicó fallback.")
                else:
                    pseudo = _dialect_lint(pseudo)

                issues.extend(data.get("issues") or [])
                issues.insert(0, f"modelo_usado={model_name}, intentos={attempts}")
                if len(attempted) > 1:
                    issues.insert(1, f"fallbacks_intentados={attempted[:-1]}")

                return ToGrammarResponse(
                    pseudocode_normalizado=_clean(pseudo),
                    issues=issues,
                )

            except Exception as e:
                issues.append(f"[{model_name}] {type(e).__name__}: {e}")

        issues.insert(0, f"todos_fallaron_intentados={attempted}")
        return ToGrammarResponse(
            pseudocode_normalizado=f"begin\n{req.text.strip()}\nend",
            issues=["Todos los modelos fallaron (reintentos agotados)."] + issues,
        )

    def _call_with_retries(self, model_name: str, prompt: str) -> Tuple[str, int]:
        attempts = 0
        last_err: Optional[Exception] = None

        for attempt in range(self.retry_max + 1):
            attempts = attempt + 1
            try:
                resp = self.client.models.generate_content(model=model_name, contents=prompt)
                text = (resp.text or "").strip()
                if not text:
                    raise RuntimeError("Respuesta vacía del modelo")
                return text, attempts

            except Exception as e:
                last_err = e
                msg = str(e)
                retryable = any(
                    code in msg
                    for code in (" 429", " 500", " 502", " 503", " 504", "UNAVAILABLE", "temporarily")
                )
                if attempt < self.retry_max and retryable:
                    sleep = settings.LLM_RETRY_BASE * (2 ** attempt) + random.uniform(0, 0.25)
                    time.sleep(sleep)
                    continue
                break

        raise last_err or RuntimeError("Fallo desconocido en llamada al modelo")

    # ----------------------------------------------------------------------
    # 4.2. Comparación con Normalización (CORREGIDO) 🔧
    # ----------------------------------------------------------------------

    async def compare_analysis(self, pseudocode: str, analyzer_result: dict) -> dict:
        """
        Compara el análisis del LLM con el del analyzer del backend.
        
        🔧 CORRECCIÓN: Normaliza valores antes de enviar y después de recibir.
        """
        if not self.client:
            return {
                "llm_analysis": {
                    "big_o": "N/A",
                    "big_omega": "N/A",
                    "theta": "N/A",
                    "reasoning": "API key no configurada"
                },
                "comparison": {
                    "big_o_match": False,
                    "big_omega_match": False,
                    "theta_match": False,
                    "overall_agreement": 0,
                    "differences": [],
                    "recommendations": []
                },
                "summary": "No disponible: API key no configurada"
            }
        
        return await asyncio.to_thread(self._compare_analysis_sync, pseudocode, analyzer_result)

    def _compare_analysis_sync(self, pseudocode: str, analyzer_result: dict) -> dict:
        """
        Implementación síncrona con normalización integrada.
        
        🔧 CORRECCIONES APLICADAS:
        1. Normaliza big_o, big_omega, theta ANTES de construir el prompt
        2. Compara usando complexities_match() DESPUÉS de recibir respuesta
        3. Recalcula porcentaje de acuerdo correctamente
        """
        # Normalizar valores del analyzer
        big_o_raw = analyzer_result.get('big_o', 'N/A')
        big_omega_raw = analyzer_result.get('big_omega', 'N/A')
        theta_raw = analyzer_result.get('theta', 'N/A')
        
        big_o_norm = normalize_complexity(big_o_raw)
        big_omega_norm = normalize_complexity(big_omega_raw)
        theta_norm = normalize_complexity(theta_raw)
        
        # Construir prompt con valores NORMALIZADOS
        comparison_prompt = f"""Eres un experto en análisis de complejidad algorítmica. 
Tu tarea es analizar el siguiente pseudocódigo y comparar tu análisis con el resultado 
proporcionado por un analyzer automático.

IMPORTANTE: DEBES RESPONDER SIEMPRE EN ESPAÑOL, sin excepciones.

PSEUDOCÓDIGO A ANALIZAR:
```
{pseudocode.strip()}
```

RESULTADO DEL ANALYZER (que queremos verificar):
- O(n): {big_o_norm}
- Ω(n): {big_omega_norm}
- Θ(n): {theta_norm}

ANÁLISIS LÍNEA POR LÍNEA DEL ANALYZER (si disponible):
"""
        
        # Agregar análisis línea por línea si está disponible
        if 'lines' in analyzer_result and analyzer_result['lines']:
            comparison_prompt += "\n- Línea | Tipo | Multiplicador | Costo(peor)\n"
            for line_info in analyzer_result['lines'][:10]:  # Primeras 10 líneas
                line_num = line_info.get('line', 0)
                kind = line_info.get('kind', 'unknown')
                mult = line_info.get('multiplier', '1')
                cost = line_info.get('cost_worst', '-')
                comparison_prompt += f"  {line_num} | {kind} | {mult} | {cost}\n"
        
        comparison_prompt += """

Por favor:
1. Analiza el pseudocódigo independientemente
2. Calcula la complejidad: O(n), Ω(n), Θ(n)
3. Compara tus resultados con los del analyzer
4. Estima el costo de las primeras líneas (si las hay)
5. Explica las diferencias (si las hay) EN ESPAÑOL

Responde SOLO con un JSON válido, sin explicaciones adicionales. Estructura exacta:
{
  "llm_analysis": {
    "big_o": "O(...)",
    "big_omega": "Ω(...)",
    "theta": "Θ(...)",
    "reasoning": "Explicación del análisis en español"
  },
  "comparison": {
    "big_o_match": true/false,
    "big_omega_match": true/false,
    "theta_match": true/false,
    "overall_agreement": 85,
    "differences": ["Diferencia 1 en español", "Diferencia 2 en español"],
    "recommendations": ["Recomendación 1 en español", "Recomendación 2 en español"]
  },
  "line_analysis": [
    {"line": 3, "kind": "assign", "multiplier": "1", "analyzer_cost_worst": "1", "llm_cost_worst": "1", "cost_match": true},
    {"line": 5, "kind": "while", "multiplier": "log n", "analyzer_cost_worst": "log n", "llm_cost_worst": "log n", "cost_match": true}
  ],
  "summary": "Resumen de la comparación en español"
}
"""

        system_instruction = """Eres un experto en complejidad algorítmica con profundo conocimiento de notación O, Ω, Θ.

⚠️ INSTRUCCIÓN CRÍTICA: SIEMPRE RESPONDE EN ESPAÑOL.
- No importa qué idioma use el usuario, tu respuesta debe estar completamente en español.
- Utiliza términos técnicos en español: cota superior, cota inferior, cota ajustada, etc.
- No mezcles idiomas: TODO debe ser en español."""

        issues = []

        for model_name in self.models_chain:
            try:
                raw, attempts = self._call_with_retries(model_name, system_instruction + "\n\n" + comparison_prompt)
                data = _extract_json(raw)

                result = {
                    "llm_analysis": data.get("llm_analysis", {}),
                    "comparison": data.get("comparison", {}),
                    "summary": data.get("summary", "")
                }
                
                # Incluir análisis línea por línea si está disponible
                if "line_analysis" in data:
                    result["line_analysis"] = data.get("line_analysis", [])

                # Validar estructura
                if not result["llm_analysis"] or not result["comparison"]:
                    raise ValueError("Estructura incompleta en respuesta")
                
                # 🔧 CORRECCIÓN CRÍTICA: Re-calcular matches normalizados
                # El LLM podría devolver "O(n²)" pero analyzer "n^2"
                # complexities_match() normaliza ambos antes de comparar
                llm_big_o = result["llm_analysis"].get("big_o", "N/A")
                llm_big_omega = result["llm_analysis"].get("big_omega", "N/A")
                llm_theta = result["llm_analysis"].get("theta", "N/A")
                
                # Actualizar los flags de match usando comparación normalizada
                result["comparison"]["big_o_match"] = complexities_match(big_o_norm, llm_big_o)
                result["comparison"]["big_omega_match"] = complexities_match(big_omega_norm, llm_big_omega)
                result["comparison"]["theta_match"] = complexities_match(theta_norm, llm_theta)
                
                # Recalcular overall_agreement
                matches = sum([
                    result["comparison"]["big_o_match"],
                    result["comparison"]["big_omega_match"],
                    result["comparison"]["theta_match"] if result["comparison"].get("theta_match") is not None else 0
                ])
                total = 3 if result["comparison"].get("theta_match") is not None else 2
                result["comparison"]["overall_agreement"] = int((matches / total) * 100) if total > 0 else 0

                return result

            except Exception as e:
                issues.append(f"[{model_name}] {type(e).__name__}: {e}")

        # Si todos fallan, retornar estructura por defecto
        return {
            "llm_analysis": {
                "big_o": "Error",
                "big_omega": "Error",
                "theta": "Error",
                "reasoning": f"Error al analizar: {'; '.join(issues[:2])}"
            },
            "comparison": {
                "big_o_match": False,
                "big_omega_match": False,
                "theta_match": False,
                "overall_agreement": 0,
                "differences": ["Error en la comparación"],
                "recommendations": ["Revisa el pseudocódigo o intenta nuevamente"]
            },
            "summary": "Error al completar la comparación"
        }

    async def analyze_recursion_tree(
        self,
        pseudocode: str,
        big_o: str,
        recurrence_equation: Optional[str] = None,
        ir_worst: Optional[dict] = None
    ) -> dict:
        """
        Genera un árbol de recursión profundo y completo analizando el pseudocódigo.
        """
        if not pseudocode.strip():
            raise ValueError("El pseudocódigo no puede estar vacío")

        issues: List[str] = []
        
        # Detectar tipo de recursión para dar contexto mejor
        is_fibonacci = 'fib' in pseudocode.lower()
        is_factorial = 'fact' in pseudocode.lower()
        is_mergesort = 'merge' in pseudocode.lower()
        is_quicksort = 'quick' in pseudocode.lower()
        is_binary_search = 'binarysearch' in pseudocode.lower() or 'binary_search' in pseudocode.lower()
        is_backtracking = 'backtrack' in pseudocode.lower()
        
        tree_prompt = f"""🌳 GENERADOR DE ÁRBOLES DE RECURSIÓN - PROFUNDIDAD OBLIGATORIA

Eres un experto en visualización de algoritmos. Tu ÚNICA tarea es generar un árbol de recursión 
COMPLETAMENTE EXPANDIDO mostrando TODOS los niveles hasta las hojas.

ALGORITMO A ANALIZAR:
```
{pseudocode.strip()}
```

COMPLEJIDAD: {big_o}
RECURRENCIA: {recurrence_equation if recurrence_equation else 'No disponible'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSTRUCCIONES OBLIGATORIAS - CUMPLE TODAS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 DETECTA EL PATRÓN Y SIGUE ESTAS REGLAS AL PIE DE LA LETRA:

🔴 FIBONACCI (fib(n) = fib(n-1) + fib(n-2)):
   ✓ MÍNIMO 5-6 NIVELES (no 2!)
   ✓ Cada nodo SIEMPRE tiene 2 hijos EXCEPTO hojas (fib(0), fib(1))
   ✓ Estructura: fib(5) → [fib(4), fib(3)] → [fib(3), fib(2), fib(2), fib(1)] → ...
   ✓ Expandir TODAS las ramas: fib(4)→fib(3), fib(3)→fib(2), fib(2)→fib(1), etc.
   ✓ Altura REAL: ~5 para fib(5), ~6 para fib(6)
   ✓ EJEMPLO CORRECTO (mínimo 4 niveles):
     fib(5)
     ├─ fib(4)
     │  ├─ fib(3)
     │  │  ├─ fib(2)
     │  │  │  ├─ fib(1)
     │  │  │  └─ fib(0)
     │  │  └─ fib(1)
     │  └─ fib(2)
     │     ├─ fib(1)
     │     └─ fib(0)
     └─ fib(3)
        ├─ fib(2)
        │  ├─ fib(1)
        │  └─ fib(0)
        └─ fib(1)

🔴 FACTORIAL, QUICKSORT PEOR CASO (cadena lineal n→n-1→n-2):
   ✓ MÍNIMO 5-6 NIVELES (no 2!)
   ✓ Cada nodo SOLO 1 hijo (cadena vertical)
   ✓ fact(5) → fact(4) → fact(3) → fact(2) → fact(1) → fact(0)
   ✓ Altura: ~5-6 (el número inicial)
   ✓ NUNCA dejes children vacías si hay más niveles

🔴 MERGESORT, QUICKSORT BALANCEADO (divide en 2):
   ✓ MÍNIMO 4-5 NIVELES (no 2!)
   ✓ Cada nodo tiene 2 hijos hasta log₂(n) niveles
   ✓ Nivel 0: n → Nivel 1: n/2, n/2 → Nivel 2: n/4, n/4, n/4, n/4 → ...
   ✓ Continúa hasta elementos de tamaño 1
   ✓ Altura: log₂(n) ≈ 4-5 para n=32

🔴 BÚSQUEDA BINARIA (cadena logarítmica):
   ✓ MÍNIMO 4-5 NIVELES (no 2!)
   ✓ Cada nodo SOLO 1 hijo (similar a factorial)
   ✓ BS(n) → BS(n/2) → BS(n/4) → BS(n/8) → ... → BS(1)
   ✓ Altura: log₂(n) ≈ 4-5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO JSON OBLIGATORIO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESPONDE SOLO CON ESTE JSON (SIN EXPLICACIONES ADICIONALES):

{{
  "tree": {{
    "root": {{
      "level": 0,
      "cost": "fib(5)",
      "width": 100,
      "children": [
        {{
          "level": 1,
          "cost": "fib(4)",
          "width": 50,
          "children": [
            {{
              "level": 2,
              "cost": "fib(3)",
              "width": 30,
              "children": [
                {{
                  "level": 3,
                  "cost": "fib(2)",
                  "width": 15,
                  "children": [
                    {{"level": 4, "cost": "fib(1)", "width": 7, "children": []}},
                    {{"level": 4, "cost": "fib(0)", "width": 7, "children": []}}
                  ]
                }},
                {{
                  "level": 3,
                  "cost": "fib(1)",
                  "width": 15,
                  "children": []
                }}
              ]
            }},
            {{
              "level": 2,
              "cost": "fib(2)",
              "width": 20,
              "children": [
                {{"level": 3, "cost": "fib(1)", "width": 10, "children": []}},
                {{"level": 3, "cost": "fib(0)", "width": 10, "children": []}}
              ]
            }}
          ]
        }},
        {{
          "level": 1,
          "cost": "fib(3)",
          "width": 50,
          "children": [
            {{
              "level": 2,
              "cost": "fib(2)",
              "width": 25,
              "children": [
                {{"level": 3, "cost": "fib(1)", "width": 12, "children": []}},
                {{"level": 3, "cost": "fib(0)", "width": 12, "children": []}}
              ]
            }},
            {{
              "level": 2,
              "cost": "fib(1)",
              "width": 25,
              "children": []
            }}
          ]
        }}
      ]
    }},
    "height": "5",
    "totalCost": "O(2^n)",
    "description": "Árbol recursivo completo con todos los niveles expandidos"
  }},
  "analysis": "Explicación de la estructura del árbol y cómo refleja la recursión"
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDACIÓN FINAL - ANTES DE RESPONDER:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ INCORRECTO: 2 niveles, pocas ramas
✅ CORRECTO: 5-6 niveles, todas las ramas expandidas

❌ INCORRECTO: children: [] cuando hay más niveles por generar
✅ CORRECTO: children siempre tienen nodos hasta las hojas

❌ INCORRECTO: "height": "5" pero solo 2 niveles en JSON
✅ CORRECTO: height coincide con profundidad real del JSON

❌ INCORRECTO: Respuesta con explicaciones o comentarios
✅ CORRECTO: SOLO JSON válido, nada más

RECUERDA: Tu árbol debe ser VISUALMENTE PROFUNDO cuando se renderice. 
5-6 niveles MÍNIMO, completamente expandido. NO ABREVIES.

¡AHORA GENERA EL JSON!
"""

        for model_name in self.models_chain:
            try:
                raw, attempts = self._call_with_retries(model_name, tree_prompt)
                
                data = _extract_json(raw)
                
                if "tree" in data and "analysis" in data:
                    # Validar que el árbol realmente sea profundo
                    if self._validate_tree_depth(data["tree"]["root"]):
                        # Extraer descripción del árbol generado por el LLM
                        tree_description = data["tree"].get("description", data.get("analysis", ""))
                        
                        # Generar SVG desde el árbol JSON
                        graph = graphviz.Digraph(comment='Recursion Tree', format='svg')
                        graph.attr(rankdir='TB')
                        graph.attr('node', shape='box', style='filled', fillcolor='lightblue')
                        build_dot_tree(data["tree"]["root"], graph)
                        svg_data = graph.pipe(format='svg').decode('utf-8')
                        
                        # Si el árbol no tiene descripción, generar una basada en el tipo
                        if not tree_description or tree_description == data.get("analysis", ""):
                            tree_description = self._generate_tree_description(
                                pseudocode, big_o, 
                                is_fibonacci, is_factorial, is_mergesort, is_quicksort, is_binary_search
                            )
                            data["tree"]["description"] = tree_description
                        
                        data["svg"] = svg_data
                        return data
                    
            except Exception as e:
                issues.append(f"[{model_name}] {type(e).__name__}: {str(e)}")

        # Fallback con árbol genérico si falla el LLM
        fallback_response = self._generate_fallback_tree(
            pseudocode, big_o, is_fibonacci, is_factorial, is_mergesort, is_quicksort, is_binary_search
        )
        
        # Generar SVG para fallback
        try:
            graph = graphviz.Digraph(comment='Recursion Tree Fallback', format='svg')
            graph.attr(rankdir='TB')
            graph.attr('node', shape='box', style='filled', fillcolor='#FFB6C1')
            build_dot_tree(fallback_response["tree"]["root"], graph)
            svg_data = graph.pipe(format='svg').decode('utf-8')
            fallback_response["svg"] = svg_data
        except Exception as svg_error:
            fallback_response["svg"] = None
        
        return fallback_response
    
    def _validate_tree_depth(self, root: dict, min_depth: int = 3) -> bool:
        """Valida que el árbol tenga suficiente profundidad"""
        def get_depth(node):
            if not node.get("children"):
                return 1
            return 1 + max(get_depth(child) for child in node["children"])
        
        depth = get_depth(root)
        return depth >= min_depth

    def _generate_tree_description(
        self, pseudocode: str, big_o: str,
        is_fib: bool, is_fact: bool, is_merge: bool, is_quick: bool, is_bsearch: bool
    ) -> str:
        """Genera una descripción del árbol basada en el tipo de algoritmo"""
        if is_fib:
            return "Fibonacci recursivo: Árbol binario donde cada nodo T(n) se divide en T(n-1) y T(n-2). Altura ≈ n. Número de nodos ≈ Φ(φ^n) ≈ O(2^n), donde φ ≈ 1.618 (razón áurea). Por tanto, costo total Θ(φ^n) ≈ O(2^n)."
        elif is_fact:
            return "Factorial recursivo: Cadena lineal n → n-1 → n-2 → ... → 1. Altura: n. Trabajo por nivel: O(1). Costo total: O(n)."
        elif is_merge:
            return "MergeSort: División balanceada en 2 subproblemas de tamaño n/2. Cada nivel cuesta Θ(n). Con log₂(n) niveles, el costo total es Θ(n log n)."
        elif is_quick:
            if 'n²' in big_o or 'n^2' in big_o:
                return "QuickSort (peor caso): Pivote siempre es el mínimo/máximo. Genera una cadena lineal n → n-1 → n-2 → ... → 1 con altura n. Costo por nivel ≈ n, total Θ(n²)."
            else:
                return "QuickSort (mejor/promedio caso): Pivote divide razonablemente. Árbol balanceado con 2 subproblemas de tamaño ≈ n/2. Altura log₂(n). Costo por nivel ≈ n, total Θ(n log n)."
        elif is_bsearch:
            return "Binary Search recursivo: Una única rama que reduce el espacio búsqueda a la mitad en cada nivel (n → n/2 → n/4 → ... → 1). Altura: log₂(n). Trabajo por nivel: O(1). Costo total: O(log n)."
        else:
            return f"Árbol de recursión generado para algoritmo con complejidad {big_o}."

    def _generate_fallback_tree(self, pseudocode: str, big_o: str, is_fib: bool, is_fact: bool, 
                                 is_merge: bool, is_quick: bool, is_bsearch: bool) -> dict:
        """Genera un árbol de fallback realista según el tipo de algoritmo"""
        
        if is_fib:
            # Fibonacci: árbol binario profundo
            return {
                "tree": {
                    "root": {
                        "level": 0, "cost": "fib(5)", "width": 100,
                        "children": [
                            {
                                "level": 1, "cost": "fib(4)", "width": 50,
                                "children": [
                                    {"level": 2, "cost": "fib(3)", "width": 25, "children": [
                                        {"level": 3, "cost": "fib(2)", "width": 12, "children": [
                                            {"level": 4, "cost": "fib(1)", "width": 6, "children": []},
                                            {"level": 4, "cost": "fib(0)", "width": 6, "children": []}
                                        ]},
                                        {"level": 3, "cost": "fib(1)", "width": 12, "children": []}
                                    ]},
                                    {"level": 2, "cost": "fib(2)", "width": 25, "children": [
                                        {"level": 3, "cost": "fib(1)", "width": 12, "children": []},
                                        {"level": 3, "cost": "fib(0)", "width": 12, "children": []}
                                    ]}
                                ]
                            },
                            {
                                "level": 1, "cost": "fib(3)", "width": 50,
                                "children": [
                                    {"level": 2, "cost": "fib(2)", "width": 25, "children": [
                                        {"level": 3, "cost": "fib(1)", "width": 12, "children": []},
                                        {"level": 3, "cost": "fib(0)", "width": 12, "children": []}
                                    ]},
                                    {"level": 2, "cost": "fib(1)", "width": 25, "children": []}
                                ]
                            }
                        ]
                    },
                    "height": "5", "totalCost": "O(2^n)",
                    "description": "Fibonacci recursivo: Árbol binario donde cada nodo T(n) se divide en T(n-1) y T(n-2). Altura ≈ n. Número de nodos ≈ Φ(φ^n) ≈ O(2^n), donde φ ≈ 1.618 (razón áurea). Por tanto, costo total Θ(φ^n) ≈ O(2^n)."
                },
                "analysis": "Fibonacci genera un árbol binario donde cada nodo (excepto hojas) se divide en dos llamadas recursivas. Altura ≈ n, nodos ≈ 2^n"
            }
        
        elif is_fact:
            # Factorial: cadena lineal
            return {
                "tree": {
                    "root": {
                        "level": 0, "cost": "fact(5)", "width": 100,
                        "children": [{
                            "level": 1, "cost": "fact(4)", "width": 100,
                            "children": [{
                                "level": 2, "cost": "fact(3)", "width": 100,
                                "children": [{
                                    "level": 3, "cost": "fact(2)", "width": 100,
                                    "children": [{
                                        "level": 4, "cost": "fact(1)", "width": 100,
                                        "children": [{
                                            "level": 5, "cost": "fact(0)", "width": 100,
                                            "children": []
                                        }]
                                    }]
                                }]
                            }]
                        }]
                    },
                    "height": "6", "totalCost": "O(n)",
                    "description": "Factorial recursivo: Cadena lineal n → n-1 → n-2 → ... → 1. Altura: n. Trabajo por nivel: O(1). Costo total: O(n)."
                },
                "analysis": "Factorial es una cadena lineal de recursión donde cada llamada invoca una sola función. Altura = n, trabajo por nivel = O(1)"
            }
        
        elif is_merge:
            # MergeSort: árbol balanceado
            return {
                "tree": {
                    "root": {
                        "level": 0, "cost": "ms(n)", "width": 100,
                        "children": [
                            {
                                "level": 1, "cost": "ms(n/2)", "width": 50,
                                "children": [
                                    {"level": 2, "cost": "ms(n/4)", "width": 25, "children": []},
                                    {"level": 2, "cost": "ms(n/4)", "width": 25, "children": []}
                                ]
                            },
                            {
                                "level": 1, "cost": "ms(n/2)", "width": 50,
                                "children": [
                                    {"level": 2, "cost": "ms(n/4)", "width": 25, "children": []},
                                    {"level": 2, "cost": "ms(n/4)", "width": 25, "children": []}
                                ]
                            }
                        ]
                    },
                    "height": "log n", "totalCost": "O(n log n)",
                    "description": "MergeSort: División balanceada en 2 subproblemas de tamaño n/2. Cada nivel cuesta Θ(n). Con log₂(n) niveles, el costo total es Θ(n log n)."
                },
                "analysis": "MergeSort divide recursivamente en 2 partes iguales. Altura = log n, trabajo por nivel = O(n)"
            }
        
        elif is_quick:
            # QuickSort: mejor caso balanceado, peor caso lineal
            return {
                "tree": {
                    "root": {
                        "level": 0, "cost": "qs(n)", "width": 100,
                        "children": [
                            {
                                "level": 1, "cost": "qs(n-1)", "width": 90,
                                "children": [{
                                    "level": 2, "cost": "qs(n-2)", "width": 80,
                                    "children": [{
                                        "level": 3, "cost": "qs(n-3)", "width": 70,
                                        "children": []
                                    }]
                                }]
                            }
                        ]
                    },
                    "height": "n", "totalCost": "O(n²) worst",
                    "description": "QuickSort (peor caso): Pivote siempre es el mínimo/máximo. Genera una cadena lineal n → n-1 → n-2 → ... → 1 con altura n. Costo por nivel ≈ n, total Θ(n²)."
                },
                "analysis": "En el peor caso (pivote siempre extremo), QuickSort genera una cadena lineal. Altura = n"
            }
        
        elif is_bsearch:
            # Binary Search: cadena logarítmica
            return {
                "tree": {
                    "root": {
                        "level": 0, "cost": "bs(n)", "width": 100,
                        "children": [{
                            "level": 1, "cost": "bs(n/2)", "width": 100,
                            "children": [{
                                "level": 2, "cost": "bs(n/4)", "width": 100,
                                "children": [{
                                    "level": 3, "cost": "bs(n/8)", "width": 100,
                                    "children": [{
                                        "level": 4, "cost": "bs(1)", "width": 100,
                                        "children": []
                                    }]
                                }]
                            }]
                        }]
                    },
                    "height": "log₂ n", "totalCost": "O(log n)",
                    "description": "Binary Search recursivo: Una única rama que reduce el espacio búsqueda a la mitad en cada nivel (n → n/2 → n/4 → ... → 1). Altura: log₂(n). Trabajo por nivel: O(1). Costo total: O(log n)."
                },
                "analysis": "Binary Search reduce el espacio a la mitad en cada nivel. Altura = log₂ n"
            }
        
        else:
            # Fallback genérico
            return {
                "tree": {
                    "root": {
                        "level": 0, "cost": big_o, "width": 100,
                        "children": [{
                            "level": 1, "cost": "T(...)", "width": 100,
                            "children": []
                        }]
                    },
                    "height": "?", "totalCost": big_o,
                    "description": f"Árbol genérico para {big_o}"
                },
                "analysis": f"Complejidad: {big_o}"
            }

    async def validate_grammar(self, pseudocode: str) -> dict:
        """
        Valida y corrige pseudocódigo existente basándose en la gramática.
        
        Si el pseudocódigo es válido, devuelve el mismo.
        Si tiene errores, lo corrige automáticamente.
        
        Args:
            pseudocode: Pseudocódigo a validar/corregir
            
        Returns:
            Dict con:
            - corrected_pseudocode: Pseudocódigo corregido
            - is_valid: bool indicando si estaba válido
            - issues: Lista de correcciones realizadas
        """
        if not self.client:
            return {
                "corrected_pseudocode": pseudocode,
                "is_valid": True,
                "issues": ["GEMINI_API_KEY no configurada: se retorna pseudocódigo original"]
            }
        
        return await asyncio.to_thread(self._validate_grammar_sync, pseudocode)

    def _validate_grammar_sync(self, pseudocode: str) -> dict:
        """
        Implementación síncrona de validación de gramática.
        """
        issues: List[str] = []
        
        validation_prompt = f"""{SYSTEM_RULES}

Tu tarea AHORA es validar si el siguiente pseudocódigo cumple la gramática estricta.

PSEUDOCÓDIGO A VALIDAR:
```
{pseudocode.strip()}
```

Si el pseudocódigo es correcto, devuelve JSON:
{{"is_valid": true, "corrected_pseudocode": "<el mismo pseudocódigo>", "issues": []}}

Si tiene errores, devuelve JSON:
{{"is_valid": false, "corrected_pseudocode": "<pseudocódigo corregido>", "issues": ["error1", "error2", ...]}}

Responde SOLO con JSON válido, sin explicaciones adicionales.
"""

        try:
            for model_name in self.models_chain:
                try:
                    raw, attempts = self._call_with_retries(model_name, validation_prompt)
                    data = _extract_json(raw)

                    corrected = _clean((data.get("corrected_pseudocode") or pseudocode).strip())
                    is_valid = data.get("is_valid", True)
                    validation_issues = data.get("issues", [])

                    # Postprocesar el pseudocódigo corregido
                    corrected = _dialect_lint(corrected)

                    return {
                        "corrected_pseudocode": corrected,
                        "is_valid": is_valid,
                        "issues": [f"[{model_name}]"] + validation_issues,
                    }

                except Exception as e:
                    issues.append(f"[{model_name}] {type(e).__name__}: {e}")

            # Si todos fallan, retornamos el pseudocódigo original
            return {
                "corrected_pseudocode": pseudocode,
                "is_valid": False,
                "issues": ["Validación fallida, retornando pseudocódigo original"] + issues,
            }

        except Exception as e:
            return {
                "corrected_pseudocode": pseudocode,
                "is_valid": False,
                "issues": [f"Error inesperado: {str(e)}"],
            }
