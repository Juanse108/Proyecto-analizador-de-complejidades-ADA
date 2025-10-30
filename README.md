

# Analizador de Complejidades (Microservicios · Python · FastAPI)

Sistema en **microservicios** para analizar el orden de complejidad de algoritmos escritos en **pseudocódigo**.
MVP iterativo: soporta `assign`, `seq`, `if`, `for` (canónico) y `while` (patrones simples).
Incluye **parser con Lark**, **analyzer determinista** con IR algebraico y **orquestador**.




## Arquitectura

```
[ Client ]
    |
    v
[ Orchestrator (8000) ]  --->  [ Parser Service (8001) ]
           |                              |
           v                              v
     [ Analyzer Service (8002) ]   <---  AST
```

* **Orchestrator**: API pública `/analyze`. Orquesta: parsea → valida semántica → analiza.
* **Parser**: Lark + Transformer → genera **AST** (Pydantic).
* **Analyzer**: Motor determinista sobre **IR** (Const, Sym(n), Add, Mul, Log, …) → `O`, `Ω`, `Θ` (MVP devuelve `O`).

---

## Stack

* **Python 3.11**, **FastAPI**, **Uvicorn**
* **Lark** (gramática / parser)
* **Pydantic v2** (modelado AST)
* **Docker / Docker Compose**

---



## Arranque rápido

### Prerrequisitos

* **Docker Desktop** (Windows/macOS) o **Docker Engine** + **Compose**
* Windows: activar **WSL2** y asegurarte de que el **daemon** esté corriendo.

### Variables de entorno

Copia los `.env.example` a `.env` en cada servicio si deseas personalizar. Por defecto:

* Orchestrator:

  * `PARSER_URL=http://parser:8001`
  * `ANALYZER_URL=http://analyzer:8002`

### Levantar todo

```bash
docker compose up --build
```

> Si estás en Windows PowerShell y ves “daemon is not running”, abre **Docker Desktop** primero.

---

## Uso

### Swagger / OpenAPI

 abre:
 - Orchestrator: http://localhost:8000/docs
 - Parser:       http://localhost:8001/docs
 - Analyzer:     http://localhost:8002/docs



## API Reference

### Orchestrator

`POST /analyze`

**Request**

```json
{
  "code": "s <- 0\nfor i <- 1 to n do\n  s <- s + i\nend for\n",
  "language": "pseudocode",
  "objective": "worst",
  "cost_model": {}
}
```

**Response (MVP)**

```json
{
  "big_o": "n",
  "big_omega": null,
  "theta": null,
  "strong_bounds": null,
  "ir": { "terms": [ { "name": "n" }, { "k": 1 } ] },
  "notes": "Iterativo MVP (seq/assign/if/for/while canónico)."
}
```

### Parser

* `POST /parse` → `{ ast }`
* `POST /semantic` → `{ ast_sem }` (normalizaciones ligeras)

### Analyzer

* `POST /analyze-ast` → complejidad + IR

---




## Pruebas rápidas

1. **O(n)**

```json
{
  "code": "s <- 0\nfor i <- 1 to n do\n  s <- s + i\nend-for\n",
  "language": "pseudocode",
  "objective": "worst",
  "cost_model": {}
}
```

2. **O(n^2)**

```json
{
  "code": "for i <- 1 to n do\n  for j <- 1 to n do\n    x <- 1\n  end-for\nend-for\n",
  "language": "pseudocode",
  "objective": "worst",
  "cost_model": {}
}
```

3. **O(log n)**

```json
{
  "code": "i <- n\nwhile i > 1 do\n  i <- i / 2\nend-while\n",
  "language": "pseudocode",
  "objective": "worst",
  "cost_model": {}
}
```

---