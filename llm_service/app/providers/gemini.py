# app/providers/gemini.py
import json, re, asyncio, time, random
from typing import Optional, List, Tuple
from google import genai

from ..schemas import (
    ToGrammarRequest, ToGrammarResponse,
    RecurrenceRequest, RecurrenceResponse,
    ClassifyRequest, ClassifyResponse,
    CompareRequest, CompareResponse,
)
from ..config import settings

# ---------- PROMPT (alineado con tu gramática tolerante) ----------
SYSTEM_RULES = r"""
Eres un convertidor a un dialecto ESTRICTO de pseudocódigo.
Devuelve SOLO un JSON minificado exactamente así:
{"pseudocode_normalizado":"<string>","issues":["<string>",...]}

### Formas top-level permitidas (elige UNA):
1) Bloque único:
   begin
     <statements>   // asignaciones, if/else/end-if, for/end-for, while/end-while, repeat/until, CALL(...)
   end

2) Definiciones de procedimiento (una o varias), SIN la palabra 'PROCEDURE':
   Nombre(params)
   begin
     <statements>
   end

### REGLAS DEL DIALECTO:
- NO uses 'PROCEDURE' ni 'END PROCEDURE'. NO declares tipos. NO uses llaves {}.
- Escribe 'begin' y 'end' SIEMPRE solos en su propia línea (no pegados a otras palabras).
- NO mezcles procedimientos con un begin/end global: o usas varios procedimientos top-level, o un solo bloque begin/end.
- NO declares arreglos/variables en líneas sueltas como `A[n]`; eso NO es una sentencia válida. Usa asignaciones y acceso por índice en sentencias válidas.
- Asignación con flecha UNICODE: '🡨' (preferida; también se acepta '<-').
- Palabras clave preferiblemente en minúsculas (la gramática acepta mayúsculas).
- Condiciones en if/while/repeat pueden ir con o SIN paréntesis; usa SIN paréntesis por brevedad.
  * if <cond> then ... end-if
  * while <cond> do ... end-while
  * repeat ... until <cond>
- for: for i 🡨 a to b do ... end-for   (opcionalmente con step)
- Llamadas:
  * Sentencia: CALL NombreProc(arg1, arg2)
  * En expresiones: NombreFunc(arg1, arg2)
- Comparadores: =, !=, <>, <, <=, >, >=, ≤, ≥, ≠
- Operadores: +, -, *, /, div, mod
- Comentarios con //.
- Sin explicaciones, sin ``` fences, sin texto fuera del JSON. Escapa saltos de línea con '\n'.
"""

EXAMPLE_PAIR = r"""
Ejemplo A (procedimientos válidos):
Entrada: "Implementa mergesort"
Salida JSON:
{"pseudocode_normalizado":"MERGESORT(lista, inicio, fin)\nbegin\n  if inicio < fin then\n    medio 🡨 (inicio + fin) / 2\n    CALL MERGESORT(lista, inicio, medio)\n    CALL MERGESORT(lista, medio + 1, fin)\n    CALL MERGE(lista, inicio, medio, fin)\n  end-if\nend\n\nMERGE(lista, inicio, medio, fin)\nbegin\n  n1 🡨 medio - inicio + 1\n  n2 🡨 fin - medio\n  i 🡨 0\n  j 🡨 0\n  k 🡨 inicio\n  // Copia y mezcla usando índices; no declares A[n]\n  while i < n1 and j < n2 do\n    if lista[inicio + i] <= lista[medio + 1 + j] then\n      lista[k] 🡨 lista[inicio + i]\n      i 🡨 i + 1\n    else\n      lista[k] 🡨 lista[medio + 1 + j]\n      j 🡨 j + 1\n    end-if\n    k 🡨 k + 1\n  end-while\n  while i < n1 do\n    lista[k] 🡨 lista[inicio + i]\n    i 🡨 i + 1\n    k 🡨 k + 1\n  end-while\n  while j < n2 do\n    lista[k] 🡨 lista[medio + 1 + j]\n    j 🡨 j + 1\n    k 🡨 k + 1\n  end-while\nend","issues":[]}

Ejemplo B (bloque único válido):
Entrada: "Sumar los n primeros números"
Salida JSON:
{"pseudocode_normalizado":"begin\ns 🡨 0\nfor i 🡨 1 to n do\n  s 🡨 s + i  // acumulador\nend-for\nend","issues":[]}

Ejemplo C (while y repeat/until sin paréntesis):
Entrada: "Mientras n sea mayor que 1, divide n entre 2 y cuenta pasos; luego repite hasta que x sea 0 restando 1."
Salida JSON:
{"pseudocode_normalizado":"begin\nc 🡨 0\nwhile n > 1 do\n  n 🡨 n / 2\n  c 🡨 c + 1\nend-while\n\nrepeat\n  x 🡨 x - 1\nuntil x = 0\nend","issues":[]}
"""


# ---------- Sanitizador para ajustar al dialecto antes de enviar al parser ----------
def _strip_global_begin_end_if_procs(s: str) -> str:
    has_proc = re.search(r"(?m)^[A-Za-z_]\w*\s*\([^)]*\)\s*\nBEGIN\b", s) is not None \
               or re.search(r"(?m)^[A-Za-z_]\w*\s*\([^)]*\)\s*\nbegin\b", s) is not None
    if has_proc:
        s = re.sub(r"(?mis)^\s*BEGIN\s*\n", "", s, count=1)
        s = re.sub(r"(?mis)^\s*begin\s*\n", "", s, count=1)
        s = re.sub(r"(?mis)\nEND\s*$", "", s, count=1)
        s = re.sub(r"(?mis)\nend\s*$", "", s, count=1)
    return s.strip()


def _split_collapsed_keywords(s: str) -> str:
    """
    Inserta un salto de línea si 'BEGIN'/'begin' o 'END'/'end' están pegados al siguiente token.
    Ejemplos: 'BEGINif' -> 'BEGIN\\nif', 'BEGINn1' -> 'BEGIN\\nn1', 'ENDMERGE' -> 'END\\nMERGE'.
    """
    t = s
    # BEGIN seguido de NO espacio/nueva línea
    t = re.sub(r'(?im)\b(BEGIN|begin)(?=\S)', r'\1\n', t)
    # END seguido de NO espacio/nueva línea (por si acaso)
    t = re.sub(r'(?im)\b(END|end)(?=\S)', r'\1\n', t)
    return t


def _ensure_proc_blocks(s: str) -> str:
    t = s
    # Si hay header de proc y NO sigue BEGIN/begin, insertarlo
    t = re.sub(r'(?m)^([A-Za-z_]\w*\s*\([^)]*\))\s*(?!\n(?:BEGIN|begin)\b)', r'\1\nBEGIN', t)
    # Asegurar END antes del próximo proc o EOF
    block_re = re.compile(
        r'(?ms)^(?P<hdr>[A-Za-z_]\w*\s*\([^)]*\)\s*\n(?:BEGIN|begin)\b)(?P<body>.*?)(?=^[A-Za-z_]\w*\s*\(|\Z)')

    def _fix_end(m: re.Match) -> str:
        hdr = m.group('hdr')
        body = m.group('body').rstrip()
        if re.search(r'(?mi)\bEND\s*$', body) or re.search(r'(?mi)\bend\s*$', body):
            return hdr + body + '\n'
        else:
            return hdr + '\n' + body + '\nEND\n'

    t = block_re.sub(_fix_end, t)
    return t


def _ensure_begin_newline(s: str) -> str:
    """
    Si aparece 'BEGIN'/'begin' pegado al siguiente token (p.ej. 'BEGINif', 'BEGINn1'),
    inserta un salto de línea para dejar 'BEGIN\\n...'. Respeta la indentación.
    """
    return re.sub(
        r'(?m)^(?P<indent>\s*)(?P<kw>BEGIN|begin)(?=\S)',
        r'\g<indent>\g<kw>\n',
        s
    )


def _dialect_lint(s: str) -> str:
    t = s

    # 0) PROCEDURE -> quitar
    t = re.sub(r"(?mi)^\s*PROCEDURE\s+([A-Za-z_]\w*)\s*\(", r"\1(", t)
    t = re.sub(r"(?mi)^\s*END\s+PROCEDURE\s*$", "END", t)

    # 1) Quitar BEGIN/END global si hay procedimientos top-level
    t = _strip_global_begin_end_if_procs(t)

    # 2) ✅ NUEVO: dividir cualquier BEGIN/END pegado al siguiente token
    t = _split_collapsed_keywords(t)

    # 3) Asegurar que cada proc tenga BEGIN/END propios
    t = _ensure_proc_blocks(t)

    # 4) Comentar líneas sueltas tipo A[n] (no son sentencias válidas)
    t = re.sub(r"(?m)^\s*[A-Za-z_]\w*\s*\[[^\]\n]+\]\s*$", lambda m: "// " + m.group(0), t)

    # 5) Normalizar saltos
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    return t.strip()



# ---------- Utilidades de extracción ----------
_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(raw: str) -> dict:
    """
    Extrae el primer objeto JSON del texto del modelo.
    Lanza ValueError si no encuentra uno válido.
    """
    raw = (raw or "").strip()
    # Intento directo
    if raw.startswith("{") and raw.endswith("}"):
        try:
            return json.loads(raw)
        except Exception:
            pass
    # Búsqueda por regex
    m = _JSON_PATTERN.search(raw)
    if not m:
        raise ValueError(f"Respuesta no-JSON del LLM. raw={raw[:160]}...")
    return json.loads(m.group(0))


def _clean(s: str) -> str:
    return (s or "").replace("\r\n", "\n").replace("\r", "\n").strip()


# ---------- Provider ----------
class GeminiProvider:
    def __init__(self) -> None:
        self.model_name = settings.GEMINI_MODEL
        self.api_key: Optional[str] = settings.GEMINI_API_KEY
        self.timeout = settings.GEMINI_TIMEOUT

        # Cadena de modelos: principal + fallbacks (desde .env)
        fb = [m.strip() for m in (settings.LLM_FALLBACK_MODELS or "").split(",") if m.strip()]
        seen = set()
        self.models_chain: List[str] = []
        for m in [self.model_name, *fb]:
            if m not in seen:
                self.models_chain.append(m);
                seen.add(m)

        self.retry_max = settings.LLM_RETRY_MAX
        self.retry_base = settings.LLM_RETRY_BASE

        self.client: Optional[genai.Client] = genai.Client(api_key=self.api_key) if self.api_key else None

    async def to_grammar(self, req: ToGrammarRequest) -> ToGrammarResponse:
        if not self.client:
            return ToGrammarResponse(
                pseudocode_normalizado=f"BEGIN\n{req.text.strip()}\nEND",
                issues=["GEMINI_API_KEY no configurada: usando fallback BEGIN/END"]
            )
        return await asyncio.to_thread(self._to_grammar_sync, req)

    def _to_grammar_sync(self, req: ToGrammarRequest) -> ToGrammarResponse:
        issues: List[str] = []
        user_hints = f"\nPistas: {req.hints}\n" if req.hints else ""
        prompt = (
                SYSTEM_RULES + EXAMPLE_PAIR +
                "\nEntrada real:\n" + req.text.strip() + user_hints +
                "\nResponde SOLO con el JSON:"
        )

        attempted: List[str] = []
        for model_name in self.models_chain:
            attempted.append(model_name)
            try:
                raw, attempts = self._call_with_retries(model_name, prompt)
                data = _extract_json(raw)
                pseudo = _clean((data.get("pseudocode_normalizado") or "").strip())

                if not pseudo:
                    pseudo = f"BEGIN\n{req.text.strip()}\nEND"
                    issues.append(f"[{model_name}] JSON sin 'pseudocode_normalizado'. Se aplicó fallback.")
                else:
                    pseudo = _dialect_lint(pseudo)

                issues.extend(data.get("issues") or [])
                issues.insert(0, f"modelo_usado={model_name}, intentos={attempts}")
                if len(attempted) > 1:
                    issues.insert(1, f"fallbacks_intentados={attempted[:-1]}")
                return ToGrammarResponse(pseudocode_normalizado=_clean(pseudo), issues=issues)

            except Exception as e:
                issues.append(f"[{model_name}] {type(e).__name__}: {e}")

        # Si TODOS fallan, devolvemos envoltura segura + reporte
        issues.insert(0, f"todos_fallaron_intentados={attempted}")
        return ToGrammarResponse(
            pseudocode_normalizado=f"BEGIN\n{req.text.strip()}\nEND",
            issues=["Todos los modelos fallaron (reintentos agotados)."] + issues
        )

    def _call_with_retries(self, model_name: str, prompt: str) -> Tuple[str, int]:
        """
        Intenta la llamada N veces. Reintenta en 429/5xx/UNAVAILABLE o respuesta vacía.
        Devuelve (texto, intentos_usados).
        """
        attempts = 0
        last_err: Optional[Exception] = None
        for attempt in range(self.retry_max + 1):
            attempts = attempt + 1
            try:
                resp = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                text = (resp.text or "").strip()
                if not text:
                    raise RuntimeError("Respuesta vacía del modelo")
                return text, attempts
            except Exception as e:
                last_err = e
                msg = str(e)
                retryable = any(
                    code in msg for code in (" 429", " 500", " 502", " 503", " 504", "UNAVAILABLE", "temporarily"))
                if attempt < self.retry_max and retryable:
                    sleep = settings.LLM_RETRY_BASE * (2 ** attempt) + random.uniform(0, 0.25)
                    time.sleep(sleep)
                    continue
                break
        raise last_err or RuntimeError("Fallo desconocido en llamada al modelo")

    # Pendientes (a implementar luego)
    async def recurrence(self, req: RecurrenceRequest) -> RecurrenceResponse:
        raise NotImplementedError("recurrence (Gemini) pendiente")

    async def classify(self, req: ClassifyRequest) -> ClassifyResponse:
        raise NotImplementedError("classify (Gemini) pendiente")

    async def compare(self, req: CompareRequest) -> CompareResponse:
        raise NotImplementedError("compare (Gemini) pendiente")
