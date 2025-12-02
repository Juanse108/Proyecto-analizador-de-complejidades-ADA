# Microservicio de Análisis de Pseudocódigo (Parser & Semantic) — v1.2

## Descripción general

Este microservicio implementa el análisis sintáctico y semántico de pseudocódigo dentro del ecosistema de análisis algorítmico.  
Convierte texto en pseudocódigo (definido por una gramática Lark) en un Árbol de Sintaxis Abstracta (AST) validado y serializable, detectando además inconsistencias semánticas básicas.

El servicio está construido con **FastAPI**, **Lark** y **Pydantic**, y forma parte del proyecto **“Analizador de Complejidades Algorítmicas”**.

---

## Novedades de la versión 1.2

- Refactor completo de la gramática `pseudocode.lark`:
  - Estilo Pascal unificado: cuerpos de `for`, `while` e `if` con `begin ... end` (sin `end-for`, `end-while`, `end-if`).
  - Soporte explícito para:
    - Comentarios de línea con `►` (ignorados por el parser).
    - Una sentencia por línea, con manejo robusto de líneas en blanco.
    - Arreglos y *slices* tipo `A[1..n]` tanto en parámetros como en accesos.
    - Clases top-level (`Casa {Area color propietario}`) y objetos (`Casa hogar`).
    - Llamadas a función con notación `f(...)` en expresiones.
    - Techo y piso con símbolos Unicode `⌈ ⌉` y `⌊ ⌋`.
  - Literales booleanos `T`/`F` en mayúscula, permitiendo variables `t`/`f` en minúscula.
- Transformer del AST reorganizado y documentado (`BuildAST` en `parser.py`), ignorando de forma controlada:
  - Declaraciones de objetos y clases (no afectan complejidad).
  - Sentencias de expresión usadas como “declaraciones” de arreglos (`A[n]`, `A[10][m]`).
- Suite de **20 pruebas de regresión** de la gramática y del parser (ver sección “Pruebas”).



## Características principales

- **Parser LALR (Lark)**: convierte pseudocódigo en un AST propio del dominio.
- **Verificador semántico**: normaliza y valida estructuras (condiciones, bucles, etc.).
- **AST basado en Pydantic**: modelo tipado, validado y JSON-serializable.
- **API REST FastAPI**: endpoints `/parse` y `/semantic` para análisis remoto.
- **Soporte Unicode extendido**:
  - Operadores relacionales: `≤`, `≥`, `≠`.
  - Techo/piso: `⌈ ⌉`, `⌊ ⌋`.
  - Asignación con `<-` o `🡨`.
- **Gramática modular** (estilo Pascal):
  - `for` / `while` / `if` con `begin ... end`.
  - `repeat ... until`.
  - Comentarios de línea con `►`.
  - Clases top-level y declaraciones de objetos.
  - Arreglos con índices y *slices* (`A[1]`, `A[1..j]`).

---

## Arquitectura del proyecto

```txt
app/
│
├── ast_models.py       # Definición del AST (Program, For, If, Expr, etc.)
├── parser.py           # Parser: transforma pseudocódigo → AST (Lark + BuildAST)
├── semantic_pass.py    # Análisis semántico: normalización y chequeos
├── schemas.py          # Modelos Pydantic de entrada/salida (FastAPI)
├── routes.py           # Rutas del microservicio (FastAPI)
└── grammar/
    └── pseudocode.lark # Gramática formal del pseudocódigo
````

---

## Flujo de procesamiento

1. **Entrada**: texto en pseudocódigo
   (algoritmos con `for`, `while`, `if`, `repeat`, arreglos, llamadas a función, etc.).
2. **Parser (`parser.py`)**:

   * Usa Lark + gramática `pseudocode.lark`.
   * Construye un AST Pydantic (`Program`, `Block`, `For`, `If`, `Assign`, etc.) mediante `BuildAST`.
3. **Análisis semántico (`semantic_pass.py`)**:

   * Normaliza estructuras (por ejemplo, `step = 1` por defecto en bucles `for` sin `step`).
   * Verifica condiciones booleanas y otros invariantes.
   * Devuelve advertencias o errores en la lista `issues`.
4. **Salida**: un JSON con el AST normalizado y la lista de `issues`.

---

## Endpoints disponibles

| Método | Ruta        | Descripción                                | Modelo de entrada | Modelo de salida |
| ------ | ----------- | ------------------------------------------ | ----------------- | ---------------- |
| POST   | `/parse`    | Analiza sintácticamente pseudocódigo → AST | `ParseReq`        | `ParseResp`      |
| POST   | `/semantic` | Ejecuta análisis semántico sobre un AST    | `SemReq`          | `SemResp`        |

---

## Ejemplo de uso (FastAPI / JSON)

### 1. Endpoint `/parse`

**Request**

```json
{
  "code": "NestedLoops(n) begin\n  for i <- 1 to n do begin\n    for j <- 1 to n do begin\n      a <- 1\n    end\n  end\nend"
}
```

**Response** (ejemplo abreviado)

```json
{
  "ok": true,
  "ast": {
    "kind": "program",
    "body": [
      {
        "kind": "proc",
        "name": "NestedLoops",
        "params": [
          "n"
        ],
        "body": [
          {
            "loc": {
              "line": 2,
              "column": 3
            },
            "kind": "for",
            "var": "i",
            "start": {
              "kind": "num",
              "value": 1
            },
            "end": {
              "kind": "var",
              "name": "n"
            },
            "step": null,
            "inclusive": true,
            "body": [
              {
                "loc": {
                  "line": 2,
                  "column": 22
                },
                "kind": "block",
                "stmts": [
                  {
                    "loc": {
                      "line": 3,
                      "column": 5
                    },
                    "kind": "for",
                    "var": "j",
                    "start": {
                      "kind": "num",
                      "value": 1
                    },
                    "end": {
                      "kind": "var",
                      "name": "n"
                    },
                    "step": null,
                    "inclusive": true,
                    "body": [
                      {
                        "loc": {
                          "line": 3,
                          "column": 24
                        },
                        "kind": "block",
                        "stmts": [
                          {
                            "loc": {
                              "line": 4,
                              "column": 9
                            },
                            "kind": "assign",
                            "target": {
                              "kind": "var",
                              "name": "a"
                            },
                            "expr": {
                              "kind": "num",
                              "value": 1
                            }
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  },
  "errors": []
}
```

---

### 2. Endpoint `/semantic`

**Request**

```json
{
  "ast": {
    "kind": "program",
    "body": [
      {
        "kind": "for",
        "var": "i",
        "start": { "kind": "num", "value": 1 },
        "end":   { "kind": "num", "value": 5 },
        "inclusive": true,
        "body": []
      }
    ]
  }
}
```

**Response**

```json
{
  "ast_sem": {
    "kind": "program",
    "body": [
      {
        "loc": null,
        "kind": "for",
        "var": "i",
        "start": {
          "kind": "num",
          "value": 1
        },
        "end": {
          "kind": "num",
          "value": 5
        },
        "step": {
          "kind": "num",
          "value": 1
        },
        "inclusive": true,
        "body": []
      }
    ]
  },
  "issues": []
}
```

---

## Pruebas (regresión de gramática y parser)

Las siguientes **20 entradas de pseudocódigo** se utilizan como conjunto de regresión para garantizar que la gramática y el parser aceptan correctamente:

* Asignaciones simples.
* Bucles `for`, `while`, `repeat`.
* Condicionales `if` con `else`.
* Arreglos, *slices* y matrices.
* Clases y objetos (`Casa { ... }`).
* Llamadas a función y procedimientos.
* Comentarios con `►`.
* Operadores y símbolos Unicode especiales.

```json
[
  {
    "code": "begin\nx 🡨 1\ny 🡨 x + 2\nz 🡨 x * y - 3\nend"
  },
  {
    "code": "begin\ns 🡨 0\nfor i 🡨 1 to n do begin\n  s 🡨 s + i\nend\nend"
  },
  {
    "code": "begin\nwhile (n > 1) do begin\n  n 🡨 n div 2\nend\nend"
  },
  {
    "code": "begin\nrepeat\n  x 🡨 x - 1\nuntil (x = 0)\nend"
  },
  {
    "code": "begin\nif (a ≤ b) then begin\n  m 🡨 a\nend\nelse begin\n  m 🡨 b\nend\nend"
  },
  {
    "code": "Suma(a, b) begin\n  r 🡨 a + b\nend\n\nbegin\nCALL Suma(2, 3)\nend"
  },
  {
    "code": "begin\nA[n]\nA[10][m]\nA[1] 🡨 5\nA[i] 🡨 A[1..j]\nend"
  },
  {
    "code": "Casa {Area color propietario}\n\nbegin\nCasa hogar\nhogar.Area 🡨 120\nhogar.color 🡨 1\nend"
  },
  {
    "code": "begin\nq 🡨 (a + b) / 3\nr 🡨 a mod 2\ns 🡨 a div 2\nt 🡨 ⌈(a + b) / 2⌉\nu 🡨 ⌊(a + b) / 2⌋\nend"
  },
  {
    "code": "begin\nif ((x ≠ NULL) and (x.valor ≥ 10)) then begin\n  y 🡨 x.valor\nend\nelse begin\n  y 🡨 0\nend\nend"
  },
  {
    "code": "MaxSub(a[1..n]) begin\n  best 🡨 -1\n  cur 🡨 0\n  for i 🡨 1 to n do begin\n    cur 🡨 cur + a[i]\n    if (cur > best) then begin\n      best 🡨 cur\n    end\n    else begin\n      best 🡨 best\n    end\n    if (cur < 0) then begin\n      cur 🡨 0\n    end else begin\n      cur 🡨 cur\n      end\nend"
  },
  {
    "code": "BusquedaBinaria(A[1..n], x) begin\n  l 🡨 1\n  r 🡨 n\n  while (l ≤ r) do begin\n    m 🡨 (l + r) div 2\n    if (A[m] = x) then begin\n      r 🡨 m\n    end\n    else begin\n      r 🡨 r\n    end\n    if (A[m] < x) then begin\n      l 🡨 m + 1\n    end\n    else begin\n      r 🡨 m - 1\n    end\n  end\nend"
  },
  {
    "code": "Merge(lista, inicio, medio, fin) begin\n  n1 🡨 medio - inicio + 1\n  n2 🡨 fin - medio\n  i 🡨 0\n  j 🡨 0\n  k 🡨 inicio\n  while ((i < n1) and (j < n2)) do begin\n    if (lista[inicio + i] ≤ lista[medio + 1 + j]) then begin\n      lista[k] 🡨 lista[inicio + i]\n      i 🡨 i + 1\n    end\n    else begin\n      lista[k] 🡨 lista[medio + 1 + j]\n      j 🡨 j + 1\n    end\n    k 🡨 k + 1\n  end\n  while (i < n1) do begin\n    lista[k] 🡨 lista[inicio + i]\n    i 🡨 i + 1\n    k 🡨 k + 1\n  end\n  while (j < n2) do begin\n    lista[k] 🡨 lista[medio + 1 + j]\n    j 🡨 j + 1\n    k 🡨 k + 1\n  end\nend"
  },
  {
    "code": "MergeSort(lista, inicio, fin) begin\n  if (inicio < fin) then begin\n    medio 🡨 (inicio + fin) div 2\n    CALL MergeSort(lista, inicio, medio)\n    CALL MergeSort(lista, medio + 1, fin)\n    CALL Merge(lista, inicio, medio, fin)\n  end\n  else begin\n    medio 🡨 medio\n  end\nend"
  },
  {
    "code": "begin\n► comentario con flecha al inicio\nx 🡨 1\n► otro comentario\ny 🡨 x + 2\nend"
  },
  {
    "code": "begin\ns 🡨 0\nfor i 🡨 1 to n step 2 do begin\n  s 🡨 s + i\nend\nend"
  },
  {
    "code": "begin\nM[n][m]\nfor i 🡨 1 to n do begin\n  for j 🡨 1 to m do begin\n    M[i][j] 🡨 i * j\n  end\nend\nend"
  },
  {
    "code": "begin\nA[n]\nB[n]\nfor i 🡨 1 to n do begin\n  A[i] 🡨 B[1..i]\nend\nend"
  },
  {
    "code": "Concatenar(A[1..n], B[1..m]) begin\n  C[n + m]\n  k 🡨 1\n  for i 🡨 1 to n do begin\n    C[k] 🡨 A[i]\n    k 🡨 k + 1\n  end\n  for j 🡨 1 to m do begin\n    C[k] 🡨 B[j]\n    k 🡨 k + 1\n  end\nend"
  },
  {
    "code": "begin\nx 🡨 f(3) + g(2, 5)\ny 🡨 ⌈x / 3⌉ - ⌊x / 3⌋\nif ((x ≥ 10) or (y ≠ 0)) then begin\n  z 🡨 T\nend\nelse begin\n  z 🡨 F\nend\nend"
  }
]
```

---

## Créditos y mantenimiento

**Autores**
Juan Sebastian Martinez Jimenez y Santiago Garcia Medina.

**Versión**: 1.2 — Noviembre 2025
