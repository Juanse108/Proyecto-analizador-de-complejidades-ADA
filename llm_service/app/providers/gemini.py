# app/providers/gemini.py
"""
Proveedor Gemini para normalizar lenguaje natural → pseudocódigo
compatible con la gramática de `pseudocode.lark`.

Responsabilidades principales:
- Construir el prompt de sistema con las reglas estrictas del dialecto
  de pseudocódigo soportado por el parser.
- Llamar al modelo Gemini 2.0 (con cadena de fallbacks y reintentos).
- Extraer y validar el JSON devuelto por el modelo.
- Postprocesar el pseudocódigo para alinearlo con el dialecto real
  esperado por la gramática (sin cambiar la lógica del algoritmo).
- Devolver un `ToGrammarResponse` con el pseudocódigo final y un
  registro de issues / decisiones tomadas.

Este módulo NO implementa todavía:
- recurrence
- classify
- compare

Esas operaciones están declaradas en la interfaz, pero levantan
`NotImplementedError`.
"""

import json
import re
import asyncio
import time
import random
from typing import Optional, List, Tuple

from google import genai

from ..schemas import (
    ToGrammarRequest, ToGrammarResponse,
    RecurrenceRequest, RecurrenceResponse,
    ClassifyRequest, ClassifyResponse,
    CompareRequest, CompareResponse,
)
from ..config import settings

# ============================================================================
# 1. PROMPT DEL SISTEMA (ALINEADO CON LA GRAMÁTICA FINAL)
# ============================================================================

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

c) Bloque principal (algoritmo “main” sin procedimiento):
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


# ============================================================================
# 2. SANITIZADORES / POST-PROCESADO DEL PSEUDOCÓDIGO
# ============================================================================

def _trim_trailing_orphan_ends(s: str) -> str:
    """
    Recorta 'end' huérfanos al final del texto cuando hay más END que BEGIN.

    Estrategia:
    - Cuenta cuántos BEGIN/begin y END/end hay en todas las líneas.
    - Mientras sobren END y la última línea sea un END/end aislado, se elimina
      esa última línea.
    - No modifica END que estén en medio del código.

    Args:
        s: Texto completo de pseudocódigo.

    Returns:
        El mismo texto pero sin 'end' sobrantes al final.
    """
    lines = s.rstrip().splitlines()

    def count_begin_end(ls):
        begins = 0
        ends = 0
        for ln in ls:
            begins += len(re.findall(r'\b(BEGIN|begin)\b', ln))
            ends += len(re.findall(r'\b(END|end)\b', ln))
        return begins, ends

    begins, ends = count_begin_end(lines)

    # Mientras sobren END y la última línea sea solo un END/end, recórtala
    while ends > begins and lines and re.match(r'^\s*(END|end)\s*$', lines[-1]):
        lines.pop()
        begins, ends = count_begin_end(lines)

    return "\n".join(lines)


def _split_collapsed_keywords(s: str) -> str:
    """
    Inserta un salto de línea si 'BEGIN'/'begin' o 'END'/'end' están pegados
    al siguiente token.

    Ejemplos:
        'BEGINif'  -> 'BEGIN\\nif'
        'BEGINn1'  -> 'BEGIN\\nn1'
        'ENDMERGE' -> 'END\\nMERGE'

    Args:
        s: Texto de pseudocódigo posiblemente colapsado.

    Returns:
        Texto con BEGIN/END garantizados como tokens separados.
    """
    t = s
    t = re.sub(r'(?im)\b(BEGIN|begin)(?=\S)', r'\1\n', t)
    t = re.sub(r'(?im)\b(END|end)(?=\S)', r'\1\n', t)
    return t


def _clean_whitespace(s: str) -> str:
    """
    Limpia espacios en blanco innecesarios en el pseudocódigo.
    
    - Remueve espacios múltiples dentro de líneas (excepto en comentarios)
    - Remueve espacios al final de líneas
    - Asegura un solo espacio entre tokens clave
    
    Args:
        s: Pseudocódigo potencialmente con espacios extras.
        
    Returns:
        Pseudocódigo con espacios normalizados.
    """
    lines = s.split('\n')
    cleaned = []
    
    for line in lines:
        # Si es un comentario, conservar como está
        if line.strip().startswith('►'):
            cleaned.append(line.rstrip())
        else:
            # Reemplazar múltiples espacios con uno solo (excepto indentación al inicio)
            # Capturar la indentación inicial
            match = re.match(r'^(\s*)', line)
            indent = match.group(1) if match else ''
            
            # Limpiar el contenido removiendo espacios múltiples
            content = line[len(indent):].rstrip()
            content = re.sub(r'\s{2,}', ' ', content)
            
            cleaned.append(indent + content)
    
    return '\n'.join(cleaned)


def _collapse_end_else(s: str) -> str:
    """
    Une patrones del tipo:

        end
        else

    en:

        end else

    para que la gramática (que espera ELSE en la misma línea) lo pueda parsear.

    Solo actúa cuando 'end' y 'else' están en líneas consecutivas con posible
    espacio en blanco intermedio.

    Args:
        s: Texto de pseudocódigo.

    Returns:
        Texto con los patrones end/else normalizados a una sola línea.
    """
    return re.sub(
        r"(?mi)^(\s*end)\s*\n\s*(else)\b",
        r"\1 \2",
        s,
    )


def _ensure_proc_blocks(s: str) -> str:
    """
    Asegura únicamente que cada definición de procedimiento tenga un END de cierre.

    No inserta BEGIN automáticamente (eso se exige en el prompt del sistema).

    Detecta bloques de la forma:

        Nombre(params)
        begin / BEGIN
        ... cuerpo ...

    hasta el siguiente encabezado de procedimiento o EOF. Si el cuerpo no termina
    en END/end, se agrega un END extra en una nueva línea.

    Args:
        s: Texto de pseudocódigo.

    Returns:
        Texto con procedimientos cerrados correctamente con END.
    """
    t = s

    # Detecta bloques de la forma:
    #   Nombre(params)
    #   begin / BEGIN
    #   ...cuerpo...
    # (hasta el siguiente proc o EOF)
    block_re = re.compile(
        r'(?ms)^(?P<hdr>[A-Za-z_]\w*\s*\([^)]*\)\s*\n(?:BEGIN|begin)\b)(?P<body>.*?)(?=^[A-Za-z_]\w*\s*\(|\Z)'
    )

    def _fix_end(m: re.Match) -> str:
        hdr = m.group('hdr')
        body = m.group('body').rstrip()

        # Si ya termina en END/end, lo dejamos tal cual
        if re.search(r'(?mi)\bEND\s*$', body) or re.search(r'(?mi)\bend\s*$', body):
            return hdr + body + "\n"

        # Si no, le agregamos un END de cierre
        return hdr + "\n" + body + "\nEND\n"

    return block_re.sub(_fix_end, t)


def _normalize_end_else(s: str) -> str:
    """
    Normaliza patrones donde 'end' y 'else' están en líneas separadas
    para que queden en la misma línea: 'end else'.
    
    También limpia espacios múltiples entre 'end' y 'else'.
    
    Antes:
        end
        else
    
    Después:
        end else
    
    Variantes manejadas:
    - end\nelse (salto simple)
    - end   \n  else (espacios antes/después del salto)
    - end  else (espacios múltiples)
    
    Args:
        s: Pseudocódigo con posibles patrones end/else separados.
    
    Returns:
        Pseudocódigo con 'end else' normalizado.
    """
    # Patrón 1: 'end' seguido de saltos de línea y luego 'else'
    # Captura espacios opcionales y reemplaza con 'end else'
    t = re.sub(
        r'(?m)^\s*(end)\s*\n\s*(else)\b',
        r'\1 \2',
        s,
        flags=re.MULTILINE | re.IGNORECASE
    )
    
    # Patrón 2: 'end' seguido de múltiples espacios y luego 'else' en la misma línea
    # Reemplaza múltiples espacios con un solo espacio
    t = re.sub(
        r'(?i)(end)\s{2,}(else)\b',
        r'\1 \2',
        t,
        flags=re.IGNORECASE
    )
    
    return t


def _dialect_lint(s: str) -> str:
    """
    Aplica una serie de normalizaciones ligeras al pseudocódigo generado
    por el LLM para acercarlo al dialecto aceptado por `pseudocode.lark`.

    Importante:
    - No cambia la lógica del algoritmo.
    - Solo corrige detalles de sintaxis y formato que el modelo suele
      equivocarse (BEGIN/END duplicados, end-if, líneas sueltas de arreglos, etc.).

    Pasos principales (EN ORDEN):
    1. Normalizar saltos de línea.
    2. Limpiar espacios en blanco innecesarios.
    3. Eliminar palabras clave tipo PROCEDURE / END PROCEDURE.
    4. Separar BEGIN/END pegados a otros tokens.
    5. Normalizar 'end-if' / 'end-while' / 'end-for' a 'end'.
    6. Normalizar 'end' y 'else' a la misma línea: 'end else'.
    7. Comentar líneas sueltas tipo A[n] que no son sentencias válidas.
    8. Colapsar BEGIN BEGIN duplicados tras encabezados de procedimiento.
    9. Asegurar que cada procedimiento tenga BEGIN/END de cierre.

    Args:
        s: Pseudocódigo generado por el modelo.

    Returns:
        Pseudocódigo normalizado, listo para ser parseado.
    """
    t = s

    # 0) Normalizar saltos de línea primero
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    
    # 0b) Limpiar espacios en blanco innecesarios
    t = _clean_whitespace(t)

    # 1) PROCEDURE -> quitar
    t = re.sub(r"(?mi)^\s*PROCEDURE\s+([A-Za-z_]\w*)\s*\(", r"\1(", t)
    t = re.sub(r"(?mi)^\s*END\s+PROCEDURE\s*$", "END", t)

    # 2) Dividir cualquier BEGIN/END pegado al siguiente token
    t = _split_collapsed_keywords(t)

    # 3) end-if / end-while / end-for → end (por seguridad)
    t = re.sub(r"(?mi)\bend-(if|while|for)\b", "end", t)

    # 4) ⭐ CRÍTICO: Normalizar 'end' y 'else' en la misma línea
    # Este paso debe ser ANTES de _ensure_proc_blocks
    t = _normalize_end_else(t)
    t = _collapse_end_else(t)

    # 5) Comentar líneas sueltas tipo A[n]
    t = re.sub(
        r"(?m)^\s*[A-Za-z_]\w*\s*\[[^\]\n]+\]\s*$",
        lambda m: "► " + m.group(0),
        t,
    )

    # 6) Colapsar BEGIN BEGIN duplicados tras encabezado de proc
    t = re.sub(
        r'(?mis)^([A-Za-z_]\w*\s*\([^)]*\)\s*\n)\s*(BEGIN|begin)\s*\n\s*(BEGIN|begin)\b',
        r'\1begin\n',
        t
    )

    # 7) Asegurar que cada proc tenga BEGIN/END propios
    t = _ensure_proc_blocks(t)

    # 8) Aplicar una segunda pasada de _normalize_end_else por si acaso
    # (a veces el _ensure_proc_blocks puede crear nuevas líneas)
    t = _normalize_end_else(t)

    return t.strip()


# ============================================================================
# 3. UTILIDADES DE EXTRACCIÓN / LIMPIEZA
# ============================================================================

_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(raw: str) -> dict:
    """
    Extrae el primer objeto JSON del texto devuelto por el modelo.

    Intenta primero parsear toda la respuesta como JSON; si falla, busca
    el primer patrón `{ ... }` con una regex y lo intenta parsear.

    Args:
        raw: Texto bruto devuelto por el LLM.

    Returns:
        Diccionario Python correspondiente al JSON encontrado.

    Raises:
        ValueError: Si no se encuentra ningún objeto JSON válido.
        json.JSONDecodeError: Si el contenido `{...}` encontrado no es JSON válido.
    """
    raw = (raw or "").strip()

    # Intento directo: la respuesta completa es un JSON
    if raw.startswith("{") and raw.endswith("}"):
        try:
            return json.loads(raw)
        except Exception:
            pass

    # Búsqueda por regex del primer {...}
    m = _JSON_PATTERN.search(raw)
    if not m:
        raise ValueError(f"Respuesta no-JSON del LLM. raw={raw[:160]}...")
    return json.loads(m.group(0))


def _clean(s: str) -> str:
    """
    Normaliza saltos de línea y convierte los escapes literales '\\n'
    en saltos de línea reales.

    Útil porque el modelo devuelve el pseudocódigo dentro de un JSON,
    donde los saltos aparecen como '\\n'.

    Args:
        s: Texto con posibles '\\n' literales y terminadores CRLF/CR.

    Returns:
        Texto limpio, con saltos de línea '\n' y sin espacios extra en extremos.
    """
    s = s or ""
    # 1) Pasar los '\\n' que vienen dentro del JSON del modelo a saltos reales
    s = s.replace("\\n", "\n")
    # 2) Normalizar CRLF/CR
    return s.replace("\r\n", "\n").replace("\r", "\n").strip()


# ============================================================================
# 4. PROVIDER GEMINI
# ============================================================================

class GeminiProvider:
    """
    Proveedor concreto que usa Google Gemini 2.0 para:

    - `to_grammar`: convertir texto en lenguaje natural a pseudocódigo
      compatible con la gramática `pseudocode.lark`.

    Notas:
    - Usa una cadena de modelos de la familia `gemini-2.0-*` definida en
      variables de entorno (modelo principal + fallbacks).
    - Implementa reintentos exponenciales ante errores 429 / 5xx / UNAVAILABLE.
    - Si no hay api key configurada, retorna un pseudocódigo mínimo con
      `begin/end` envolviendo el texto original.

    Los métodos `recurrence`, `classify` y `compare` están declarados pero
    todavía no implementados.
    """

    def __init__(self) -> None:
        # Modelo principal tomado de settings, restringido a familia Gemini 2.0
        self.model_name = settings.GEMINI_MODEL
        self.api_key: Optional[str] = settings.GEMINI_API_KEY
        self.timeout = settings.GEMINI_TIMEOUT

        # Cadena de modelos: principal + fallbacks (desde .env), SOLO gemini-2.0-*
        fb = [m.strip() for m in (settings.LLM_FALLBACK_MODELS or "").split(",") if m.strip()]
        seen = set()
        all_models: List[str] = []
        for m in [self.model_name, *fb]:
            if m not in seen:
                seen.add(m)
                all_models.append(m)

        # Filtrar cualquier cosa que no sea familia 2.0
        self.models_chain: List[str] = [m for m in all_models if m.startswith("gemini-2.0")]
        if not self.models_chain:
            # Fallback duro por si alguien pasa un modelo incorrecto por env
            self.models_chain = ["gemini-2.0-flash"]

        # Aseguramos que model_name también sea 2.0
        self.model_name = self.models_chain[0]

        self.retry_max = settings.LLM_RETRY_MAX
        self.retry_base = settings.LLM_RETRY_BASE

        self.client: Optional[genai.Client] = genai.Client(api_key=self.api_key) if self.api_key else None

    # ----------------------------------------------------------------------
    # 4.1. Conversión a gramática (texto → pseudocódigo)
    # ----------------------------------------------------------------------

    async def to_grammar(self, req: ToGrammarRequest) -> ToGrammarResponse:
        """
        Convierte lenguaje natural en pseudocódigo que respete la gramática
        `pseudocode.lark`, usando el modelo Gemini 2.0.

        Flujo:
        1. Si no hay `GEMINI_API_KEY`, retorna un bloque mínimo con begin/end
           alrededor del texto original (fallback "bruto").
        2. Si hay cliente, delega en `_to_grammar_sync` ejecutado en un thread
           para no bloquear el event loop.

        Args:
            req: Petición con el texto original y pistas opcionales (`hints`).

        Returns:
            `ToGrammarResponse` con:
            - `pseudocode_normalizado`: pseudocódigo final postprocesado.
            - `issues`: lista de strings con decisiones, errores y metadatos.
        """
        if not self.client:
            return ToGrammarResponse(
                pseudocode_normalizado=f"begin\n{req.text.strip()}\nend",
                issues=["GEMINI_API_KEY no configurada: usando fallback begin/end bruto"],
            )
        return await asyncio.to_thread(self._to_grammar_sync, req)

    def _to_grammar_sync(self, req: ToGrammarRequest) -> ToGrammarResponse:
        """
        Implementación síncrona de `to_grammar`.

        Construye el prompt final con:
        - Reglas del sistema (`SYSTEM_RULES`).
        - Ejemplos (`EXAMPLE_PAIR`).
        - Entrada real + pistas del usuario.
        - Instrucción de responder SOLO con JSON.

        Recorre la cadena de modelos (`self.models_chain`) hasta que uno
        responda con un JSON válido. Si todos fallan, devuelve un bloque
        mínimo begin/end con issues explicando cada fallo.

        Args:
            req: Petición original.

        Returns:
            `ToGrammarResponse` con pseudocódigo normalizado e issues.
        """
        issues: List[str] = []
        user_hints = f"\nPistas: {req.hints}\n" if req.hints else ""

        # Prompt final enviado al modelo
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
                    # Fallback mínimo si el JSON no trae el campo esperado
                    pseudo = f"begin\n{req.text.strip()}\nend"
                    issues.append(f"[{model_name}] JSON sin 'pseudocode_normalizado'. Se aplicó fallback.")
                else:
                    # Ajustes ligeros para acercar al dialecto definido por la gramática
                    pseudo = _dialect_lint(pseudo)

                # issues devueltos por el modelo (si alguno)
                issues.extend(data.get("issues") or [])
                issues.insert(0, f"modelo_usado={model_name}, intentos={attempts}")
                if len(attempted) > 1:
                    issues.insert(1, f"fallbacks_intentados={attempted[:-1]}")

                return ToGrammarResponse(
                    pseudocode_normalizado=_clean(pseudo),
                    issues=issues,
                )

            except Exception as e:
                # Guardamos el error pero seguimos con el siguiente modelo de fallback
                issues.append(f"[{model_name}] {type(e).__name__}: {e}")

        # Si TODOS los modelos fallan, devolvemos una envoltura segura + reporte
        issues.insert(0, f"todos_fallaron_intentados={attempted}")
        return ToGrammarResponse(
            pseudocode_normalizado=f"begin\n{req.text.strip()}\nend",
            issues=["Todos los modelos fallaron (reintentos agotados)."] + issues,
        )

    def _call_with_retries(self, model_name: str, prompt: str) -> Tuple[str, int]:
        """
        Llama al modelo Gemini con reintentos exponenciales ante fallos.

        Se considera reintentable cuando el mensaje de error contiene:
        - " 429", " 500", " 502", " 503", " 504" o "UNAVAILABLE"
        - o texto que indique indisponibilidad temporal ("temporarily")

        Para cada intento:
        - Si hay texto de respuesta, se devuelve.
        - Si la respuesta está vacía o el error no es reintentable, se aborta
          y se lanza la excepción.

        Args:
            model_name: Nombre del modelo Gemini 2.0 a usar.
            prompt: Prompt completo a enviar.

        Returns:
            Tupla `(texto_respuesta, intentos_usados)`.

        Raises:
            La última excepción capturada si todos los reintentos fallan.
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
    # 4.2. Otros endpoints (todavía no implementados)
    # ----------------------------------------------------------------------

    async def recurrence(self, req: RecurrenceRequest) -> RecurrenceResponse:
        """
        (Pendiente de implementación).

        En el futuro este método podrá usar Gemini para:
        - Analizar recurrencias y sugerir soluciones (T(n), etc.).
        - Clasificar el tipo de recurrencia (divide & conquer, DP, etc.).

        Actualmente lanza NotImplementedError.
        """
        raise NotImplementedError("recurrence (Gemini) pendiente")

    async def classify(self, req: ClassifyRequest) -> ClassifyResponse:
        """
        (Pendiente de implementación).

        En el futuro este método podrá usar Gemini para:
        - Clasificar el tipo de algoritmo / patrón con base en su pseudocódigo.
        - Identificar si es recursivo, iterativo, divide & conquer, DP, etc.

        Actualmente lanza NotImplementedError.
        """
        raise NotImplementedError("classify (Gemini) pendiente")

    async def compare(self, req: CompareRequest) -> CompareResponse:
        """
        (Pendiente de implementación).

        En el futuro este método podrá usar Gemini para:
        - Comparar dos algoritmos (en pseudocódigo) y describir diferencias.
        - Evaluar ventajas / desventajas a alto nivel.

        Actualmente lanza NotImplementedError.
        """
        raise NotImplementedError("compare (Gemini) pendiente")

    async def compare_analysis(self, pseudocode: str, analyzer_result: dict) -> dict:
        """
        Compara el análisis del LLM con el del analyzer del backend.
        
        El LLM analiza el pseudocódigo de forma independiente y compara
        sus resultados con los del analyzer automático.
        
        Args:
            pseudocode: Pseudocódigo a analizar
            analyzer_result: Dict con {big_o, big_omega, theta} del analyzer
            
        Returns:
            Dict con análisis LLM, comparación y resumen
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
        Implementación síncrona de compare_analysis.
        """
        # Extraer líneas del pseudocódigo
        lines = pseudocode.strip().split('\n')
        
        comparison_prompt = f"""Eres un experto en análisis de complejidad algorítmica. 
Tu tarea es analizar el siguiente pseudocódigo y comparar tu análisis con el resultado 
proporcionado por un analyzer automático.

IMPORTANTE: DEBES RESPONDER SIEMPRE EN ESPAÑOL, sin excepciones.

PSEUDOCÓDIGO A ANALIZAR:
```
{pseudocode.strip()}
```

RESULTADO DEL ANALYZER (que queremos verificar):
- O(n): {analyzer_result.get('big_o', 'N/A')}
- Ω(n): {analyzer_result.get('big_omega', 'N/A')}
- Θ(n): {analyzer_result.get('theta', 'N/A')}

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
