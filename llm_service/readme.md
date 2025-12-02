# llm_service (Gemini) — Esqueleto

Servicio FastAPI que expone un proveedor LLM basado en **Google Gemini 2.0** para tareas de apoyo al análisis algorítmico.

Endpoints:

- `GET  /health`
- `POST /llm/to-grammar`
- `POST /llm/recurrence`
- `POST /llm/classify`
- `POST /llm/compare`

Notas de estado:

- `to-grammar` (**implementado**): convierte texto en lenguaje natural → pseudocódigo normalizado compatible con la gramática de pseudocódigo (estilo Pascal con `begin/end`).
- `recurrence`, `classify`, `compare` (**esqueleto**): los métodos del proveedor levantan actualmente `NotImplementedError`.

---

## Descripción general

Este microservicio forma parte del ecosistema **Analizador de Complejidades Algorítmicas** y actúa como capa LLM:

- Recibe descripciones en lenguaje natural de algoritmos.
- Construye un **prompt estricto de sistema** para forzar un dialecto de pseudocódigo compatible con la gramática Lark del parser.
- Llama a modelos de la familia **Gemini 2.0** con:
  - Modelo principal configurable.
  - Cadena de *fallbacks*.
  - Reintentos con *backoff* exponencial para errores 429 / 5xx / `UNAVAILABLE`.
- Extrae el JSON producido por el LLM y hace un **postprocesado ligero** del pseudocódigo:
  - Normalización de `begin` / `end` y bloques de procedimientos.
  - Ajuste de patrones `end` + salto de línea + `else` → `end else`.
  - Comentado de líneas sueltas inválidas (`A[n]`, etc.).
- Devuelve un `ToGrammarResponse` con:
  - `pseudocode_normalizado`: pseudocódigo listo para el parser.
  - `issues`: lista de advertencias, decisiones y metadatos (modelo usado, fallbacks, etc.).

Las demás operaciones (`recurrence`, `classify`, `compare`) están definidas a nivel de esquemas y endpoints, pero su lógica de negocio aún no está implementada.



## Ejecución local

```bash
uvicorn app.routes:app --reload --port 8003
````

Por defecto, el servicio expondrá la documentación interactiva en:

* Swagger UI: [http://localhost:8003/docs](http://localhost:8003/docs)

---

## Arquitectura

Estructura principal del proyecto:

```txt
app/
│
├── main.py          # create_app() y punto de entrada principal (FastAPI)
├── routes.py        # instancia alternativa de FastAPI: app.routes:app
├── config.py        # Configuración (Pydantic Settings, variables de entorno)
├── schemas.py       # Esquemas Pydantic de entrada/salida (ToGrammar, etc.)
├── providers/
│   └── gemini.py    # GeminiProvider: lógica de integración con Google Gemini
└── routers/
    ├── health.py    # /health: endpoints de estado/heartbeat
    └── llm.py       # /llm: endpoints to-grammar, recurrence, classify, compare
```

Resumen de responsabilidades:

* **`config.py`**
  Define la clase `Settings` con todos los parámetros configurables (modelo, API key, timeouts, reintentos, etc.) usando `pydantic-settings`.

* **`schemas.py`**
  Esquemas Pydantic para las distintas operaciones:

  * `ToGrammarRequest` / `ToGrammarResponse`
  * `RecurrenceRequest` / `RecurrenceResponse`
  * `ClassifyRequest` / `ClassifyResponse`
  * `CompareRequest` / `CompareResponse` + `BigBounds`

* **`providers/gemini.py`**
  Implementa `GeminiProvider`:

  * Construye el prompt de sistema para el dialecto de pseudocódigo.
  * Llama a `google.genai` (Gemini 2.0).
  * Maneja *fallbacks* de modelos y reintentos.
  * Aplica sanitizadores sobre el pseudocódigo (`_dialect_lint`, etc.).

* **`routers/llm.py`**
  Expone los endpoints `/llm/*` y delega en `GeminiProvider`.

* **`routers/health.py`**
  Endpoints simples de salud (`/health`, `/health/live`, `/health/ready`).

---

## Configuración (variables de entorno)

La configuración se gestiona con `pydantic-settings` en `app/config.py`.
Principales variables:

* `APP_NAME`
  Nombre de la aplicación.
  **Por defecto:** `llm_service`

* `ENV`
  Entorno de ejecución (`dev`, `prod`, `test`, etc.).
  **Por defecto:** `dev`

* `GEMINI_MODEL`
  Modelo principal de la familia Gemini 2.0.
  **Por defecto:** `gemini-2.0-flash`

* `GEMINI_API_KEY`
  API key para la API de Google Gemini.
  **Obligatoria** para usar el proveedor; si falta, `to-grammar` devuelve un bloque mínimo `begin ... end` como *fallback*.

* `GEMINI_TIMEOUT`
  Timeout (en segundos) para las llamadas al modelo.
  **Por defecto:** `30`

* `LLM_RETRY_MAX`
  Número máximo de reintentos ante errores reintentables.
  **Por defecto:** `4`

* `LLM_RETRY_BASE`
  Base del *backoff* exponencial en segundos.
  **Por defecto:** `0.7`

* `LLM_FALLBACK_MODELS`
  Lista de modelos de fallback de la familia `gemini-2.0-*`, separados por comas.
  **Por defecto:** `"gemini-2.0-pro"`

Ejemplo de `.env`:

```env
APP_NAME=llm_service
ENV=dev

GEMINI_MODEL=gemini-2.0-flash
GEMINI_API_KEY=tu_api_key

GEMINI_TIMEOUT=60
LLM_RETRY_MAX=4
LLM_RETRY_BASE=0.7
LLM_FALLBACK_MODELS=gemini-2.0-pro
```

---

## Contratos de API

### `GET /health`

Endpoint de *healthcheck*.
El contenido exacto depende de la implementación en `routers/health.py`, pero en general se usa para monitoreo (Kubernetes, Docker, etc.).

---

### `POST /llm/to-grammar`

Normaliza texto en lenguaje natural a pseudocódigo estricto.

**Request — `ToGrammarRequest`**

```json
{
  "text": "Descripción en lenguaje natural de un algoritmo...",
  "hints": "Pistas opcionales para el LLM (tipo de algoritmo, parámetros, etc.)"
}
```

* `text` (string, requerido): descripción del algoritmo o pseudocódigo informal.
* `hints` (string, opcional): contexto adicional para guiar al modelo (nombres de procedimientos, estilos, restricciones).

**Response — `ToGrammarResponse`**

```json
{
  "pseudocode_normalizado": "MERGESORT(lista, inicio, fin)\nbegin\n  ...\nend",
  "issues": [
    "modelo_usado=gemini-2.0-flash, intentos=1",
    "fallbacks_intentados=[...]",
    "Avisos adicionales del modelo o del postprocesado..."
  ]
}
```

* `pseudocode_normalizado`: pseudocódigo ajustado al dialecto esperado por la gramática (estilo Pascal con `begin/end`, `end else`, etc.).
* `issues`: lista de comentarios/advertencias/metadatos.

---

### `POST /llm/recurrence`

**Estado**: Esqueleto (levanta `NotImplementedError`).

Pensado para, en el futuro:

* Extraer la recurrencia T(n) a partir de pseudocódigo.
* Identificar parámetros de la Master Theorem (`a`, `b`, `f(n)`).
* Proponer `O`, `Ω` y `Θ` junto con una explicación textual.

Modelos:

* Request: `RecurrenceRequest`
* Response: `RecurrenceResponse`

---

### `POST /llm/classify`

**Estado**: Esqueleto (levanta `NotImplementedError`).

Objetivo futuro:

* Clasificar el patrón de un algoritmo (divide & conquer, DP, greedy, etc.).
* Indicar confianza y pistas que llevaron a esa clasificación.

Modelos:

* Request: `ClassifyRequest`
* Response: `ClassifyResponse`

---

### `POST /llm/compare`

**Estado**: Esqueleto (levanta `NotImplementedError`).

En el futuro:

* Comparar cotas de complejidad provenientes del núcleo clásico (`core`) y del LLM (`llm`).
* Señalar si coinciden, dónde difieren y sugerir próximos pasos (más tests, revisión manual, etc.).

Modelos:

* Request: `CompareRequest` (envolviendo dos `BigBounds`).
* Response: `CompareResponse`.

---

## Pruebas de `llm/to-grammar`

A continuación se listan **10 pruebas de entrada** (texto + pistas) para el endpoint `POST /llm/to-grammar`.
Estas pruebas están pensadas para forzar distintos patrones y verificar que:

* El modelo genere pseudocódigo con `begin` / `end` bien balanceados.
* Los bloques `if ... then` con `else` usen la forma `end else` (mismo renglón).
* Se use `return` en algunos casos (factorial, etc.) y efectos por asignación en otros.


---

### 1. Suma de los n primeros números (for sencillo)

```json
{
  "text": "Implementa un algoritmo que reciba un entero n y calcule la suma de los números de 1 hasta n. Usa un acumulador llamado s que empieza en 0. Recorre desde 1 hasta n y ve sumando i a s. Al final, s queda con el resultado.",
  "hints": "Usa un procedimiento SUMAR_HASTA_N(n). Dentro del cuerpo principal, declara s y úsalo como acumulador. Recorre con un bucle for i <- 1 to n do begin ... end. No uses return; deja s listo al final en el ámbito del procedimiento. Asegúrate de que cada for tenga su begin/end y que begin y end estén solos en su línea."
}
```

---

### 2. Factorial iterativo (while con return)

```json
{
  "text": "Implementa el cálculo iterativo del factorial de un número entero positivo n. Usa una variable resultado que comienza en 1 y un contador k que empieza en 1. Mientras k sea menor o igual que n, multiplica resultado por k y aumenta k en 1. Al final devuelve resultado.",
  "hints": "Usa un procedimiento FACTORIAL(n). Dentro del begin/end declara resultado y k. Emplea while (k <= n) do begin ... end. Al terminar el bucle, usa una sentencia return resultado en su propia línea. No uses else en este algoritmo. Respeta que begin y end vayan solos en su línea."
}
```

---

### 3. Máximo común divisor (Euclides, while sin return)

```json
{
  "text": "Diseña un algoritmo para hallar el máximo común divisor de dos enteros positivos a y b utilizando el algoritmo de Euclides. Mientras b sea diferente de 0, guarda en t el valor de b, reemplaza b por a mod b y a por t. Al finalizar, a contiene el MCD.",
  "hints": "Usa un procedimiento MCD(a, b). Dentro del begin/end declara una variable t para el intercambio. Usa while (b != 0) do begin ... end. No uses return; deja a con el valor del MCD al finalizar. Cada while debe tener un bloque begin/end, sin código compartido en la misma línea que begin o end."
}
```

---

### 4. Quicksort recursivo (dos procedimientos)

```json
{
  "text": "Implementa el algoritmo quicksort recursivo sobre un arreglo A de enteros. El procedimiento principal QUICKSORT(A, inicio, fin) debe: si inicio es menor que fin, escoger un pivote, particionar el arreglo en torno al pivote y luego llamar recursivamente a QUICKSORT en la parte izquierda y derecha. Usa un procedimiento PARTIR(A, inicio, fin, pivotePos) que reorganice los elementos menores o iguales al pivote a la izquierda y los mayores a la derecha, actualizando la posición final del pivote.",
  "hints": "Usa dos procedimientos: QUICKSORT(A, inicio, fin) y PARTIR(A, inicio, fin, pivotePos). En QUICKSORT usa if (inicio < fin) then begin ... end sin else, con llamadas CALL QUICKSORT y CALL PARTIR dentro del bloque. En PARTIR recorre con while o for anidados, siempre con begin/end, y usa asignaciones con la flecha o '<-'. No uses return en ninguna de las dos rutinas; trabaja por efectos sobre el arreglo A."
}
```

---

### 5. Contar elementos positivos en una matriz (for anidado)

```json
{
  "text": "Implementa un algoritmo que cuente cuántos elementos de una matriz M de enteros de tamaño m por n son mayores que cero. Usa una variable cont que comienza en 0 y recorre toda la matriz con dos bucles anidados, uno para las filas y otro para las columnas.",
  "hints": "Usa un procedimiento CONTAR_POSITIVOS(M, m, n). Dentro del begin/end, inicializa cont en 0. Usa for i <- 0 to m - 1 do begin ... end, y dentro otro for j <- 0 to n - 1 do begin ... end. La condición para sumar es if (M[i, j] > 0) then begin cont <- cont + 1 end sin else. No uses return; deja cont con la cantidad final. Asegúrate de que todos los begin y end estén bien balanceados."
}
```

---

### 6. Uso de repeat/until (restar hasta cero)

```json
{
  "text": "Diseña un algoritmo que reciba un entero positivo n y una variable pasos inicializada en 0. El algoritmo debe ir restando 1 a n hasta que llegue a 0, contando cuántas veces se hizo la operación en la variable pasos. Usa una estructura repeat hasta que n sea igual a 0.",
  "hints": "Usa un bloque principal begin ... end. Declara n y pasos. Usa repeat ... until (n = 0). Dentro del repeat haz n <- n - 1 y pasos <- pasos + 1. No uses while para este bucle. REPEAT no debe usar begin/end; las sentencias van directamente entre repeat y until, una por línea."
}
```

---

### 7. Búsqueda lineal con variable resultado

```json
{
  "text": "Implementa una búsqueda lineal en un arreglo A de tamaño n para encontrar un valor x. Usa una variable posicion que comienza en -1. Recorre el arreglo de 0 a n-1 y, si encuentras x, guarda el índice en posicion y termina el recorrido.",
  "hints": "Usa un procedimiento BUSQUEDA_LINEAL(A, n, x). Dentro del begin/end inicializa posicion en -1. Recorre con for i <- 0 to n - 1 do begin ... end. Dentro usa if (A[i] = x) then begin posicion <- i; i <- n end sin else, para simular salir del for. No uses return; el resultado queda en posicion. Respeta begin y end solos en su línea."
}
```

---

### 8. Clase y objeto sencillo (Persona con if–else)

```json
{
  "text": "Define una clase Persona con atributos edad y altura. Luego diseña un procedimiento que reciba una persona p y un entero deltaEdad, sume deltaEdad a la edad de p y marque una variable mayorDeEdad en T si la nueva edad es mayor o igual a 18, o en F en caso contrario.",
  "hints": "Primero define la clase Persona {edad altura}. Luego usa un procedimiento ACTUALIZAR_EDAD(p, deltaEdad). Dentro del begin/end usa asignaciones del tipo p.edad <- p.edad + deltaEdad y una variable booleana mayorDeEdad. Usa un if con else, donde el else se escribe en la misma línea que el end del then, así:\n\nif (p.edad >= 18) then\nbegin\n  mayorDeEdad <- T\nend else\nbegin\n  mayorDeEdad <- F\nend\n\nNo uses return en este procedimiento. Asegúrate de que cada bloque IF, y el procedimiento, tengan sus begin/end bien balanceados."
}
```

---

### 9. Uso de techo y piso (división de tareas)

```json
{
  "text": "Diseña un algoritmo que reciba un número de tareas totales T y un número de trabajadores k, y calcule cuántas tareas debe hacer cada trabajador si se quiere repartir la carga lo más equilibrada posible. Usa una variable minimo y otra maximo: minimo es el piso de T/k y maximo es el techo de T/k.",
  "hints": "Usa un procedimiento REPARTIR_TAREAS(T, k). Dentro del begin/end, asigna minimo <- ⌊T / k⌋ y maximo <- ⌈T / k⌉ usando los símbolos Unicode de piso y techo. No uses bucles ni if; solo asignaciones. No uses return; el resultado queda en minimo y maximo."
}
```

---

### 10. Combinación de while y repeat (contador doble)

```json
{
  "text": "Implementa un algoritmo que, dado un entero n, primero use un bucle while para dividir n entre 2 mientras n sea mayor que 1, contando en pasos1 cuántas veces se hizo la división. Luego use un bucle repeat para restar 1 a n hasta que n sea 0, contando en pasos2 cuántas veces se hizo la resta.",
  "hints": "Usa un bloque principal begin ... end. Declara n, pasos1 y pasos2. Inicializa n con algún valor (por ejemplo 20), pasos1 <- 0 y pasos2 <- 0. Primero usa while (n > 1) do begin n <- n / 2; pasos1 <- pasos1 + 1 end. Después usa repeat ... until (n = 0), restando 1 a n y sumando 1 a pasos2 en cada iteración. No uses else ni return. Respeta la regla de una sentencia por línea."
}
```

---

## Créditos

* **Autores / Mantenimiento**

  * Juan Sebastian Martinez Jimenez - Santiago Garcia Medina
* **Stack principal**

  * FastAPI · Pydantic · pydantic-settings · Google Gemini 2.0 (`google.genai`)
