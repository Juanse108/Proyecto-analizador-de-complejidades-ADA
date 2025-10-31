# Microservicio de Análisis de Pseudocódigo (Parser & Semantic)

## Descripción general

Este microservicio implementa el análisis sintáctico y semántico de pseudocódigo dentro del ecosistema de análisis algorítmico.  
Convierte texto en pseudocódigo (definido por una gramática Lark) en un Árbol de Sintaxis Abstracta (AST) validado y serializable, detectando además inconsistencias semánticas básicas.

El servicio está construido con FastAPI, Lark y Pydantic, y forma parte del proyecto "Analizador de Complejidades Algorítmicas".

---

## Características principales

- Parser LALR (Lark): convierte pseudocódigo en AST.
- Verificador semántico: normaliza y valida estructuras (condiciones, bucles, etc.).
- AST basado en Pydantic: modelo tipado, validado y JSON-serializable.
- API REST FastAPI: endpoints `/parse` y `/semantic` para análisis remoto.
- Soporte Unicode: admite símbolos ≤, ≥, ≠ y operadores extendidos.
- Gramática modular: definida en `pseudocode.lark`.

---

## Arquitectura del proyecto
```txt
app/
│
├── ast_models.py       # Definición del AST (Program, For, If, Expr, etc.)
├── parser.py           # Parser: transforma pseudocódigo → AST
├── semantic_pass.py    # Análisis semántico: normalización y chequeos
├── schemas.py          # Modelos Pydantic de entrada/salida (FastAPI)
├── routes.py           # Rutas del microservicio (FastAPI)
└── grammar/
    └── pseudocode.lark # Gramática formal del pseudocódigo
```
---

## Flujo de procesamiento

1. Entrada: texto en pseudocódigo (por ejemplo, un algoritmo con `for`, `if`, `while`, etc.).
2. Parser (`parser.py`): genera un AST Pydantic según la gramática definida en `pseudocode.lark`.
3. Análisis semántico (`semantic_pass.py`):
   - Asigna valores por defecto (por ejemplo, `step = 1` en bucles `for`).
   - Verifica condiciones booleanas.
   - Devuelve advertencias o errores (`issues`).
4. Salida: un JSON con el AST normalizado y la lista de `issues`.

---

## Endpoints disponibles

| Método | Ruta | Descripción | Modelo de entrada | Modelo de salida |
|---------|------|--------------|-------------------|------------------|
| POST | `/parse` | Analiza sintácticamente pseudocódigo → AST | `ParseReq` | `ParseResp` |
| POST | `/semantic` | Ejecuta análisis semántico sobre un AST | `SemReq` | `SemResp` |

---

## Ejemplo de uso (FastAPI / JSON)

### 1. Endpoint `/parse`

**Request**
```json
{
  "code": "NestedLoops(n)\nbegin\n  for i <- 1 to n do begin\n    for j <- 1 to n do begin\n      a <- 1\n    end end-for\n  end end-for\nend"
}
```

**Response**
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
              "line": 3,
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
                  "line": 4,
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
                      "line": 5,
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
        "start": {"kind": "num", "value": 1},
        "end": {"kind": "num", "value": 5},
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
## Créditos y mantenimiento


Autores:  
Juan Sebastian Martinez Jimenez y Santiago Garcia Medina.  
Versión: 1.1 — Octubre 2025


