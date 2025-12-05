# Implementación de Seguimiento de Ejecución del Pseudocódigo (Iterativo)

## 📋 Resumen

Se ha implementado exitosamente el **Diagrama de Seguimiento del Pseudocódigo** para algoritmos iterativos, equivalente al árbol de recursión usado para algoritmos recursivos.

### ✅ Requisito Cumplido
- **Peso en evaluación**: 15%
- **Tipo de diagrama**: Tabla de Traza de Ejecución
- **Aplicación**: Algoritmos iterativos (for, while)

---

## 🏗️ Arquitectura de la Solución

### Backend (Python/FastAPI)

#### 1. **Módulo de Traza de Ejecución** (`execution_trace.py`)

**Ubicación**: `core_analyzer_service/app/iterative/execution_trace.py`

**Funcionalidades**:
- Genera tablas de seguimiento paso a paso del pseudocódigo
- Simula la ejecución con valores concretos (n=5, n=16, etc.)
- Rastrea el estado de variables en cada iteración
- Calcula costo acumulado en cada paso

**Clases principales**:
```python
@dataclass
class TraceStep:
    """Representa un paso en la traza de ejecución"""
    step: int                    # Número de paso
    line: int                    # Línea de código
    kind: str                    # Tipo de sentencia
    condition: Optional[str]     # Condición evaluada
    variables: Dict[str, Any]    # Estado de variables
    operation: str               # Operación realizada
    cost: str                    # Costo de este paso
    cumulative_cost: str         # Costo acumulado

@dataclass
class ExecutionTrace:
    """Resultado completo de la traza"""
    steps: List[TraceStep]
    total_iterations: int
    max_depth: int               # Profundidad de anidamiento
    variables_tracked: List[str]
    complexity_formula: str
    description: str
```

**Funciones de generación**:
1. `generate_trace_for_simple_loop()` - Bucles simples O(n)
2. `generate_trace_for_nested_loops()` - Bucles anidados O(n²)
3. `generate_trace_for_binary_search()` - Búsqueda binaria O(log n)
4. `generate_execution_trace()` - Detección automática

#### 2. **Integración con el Analizador**

**Modificaciones en `api.py`**:
```python
def analyze_iterative_program(ast: dict) -> ProgramCost:
    # ... análisis existente ...
    
    # 🆕 Generar traza de ejecución
    big_o_complexity = big_o_str_from_expr(worst)
    execution_trace = generate_execution_trace(ast, big_o_complexity, "n")
    
    return ProgramCost(
        # ... campos existentes ...
        execution_trace=execution_trace,  # 🆕
    )
```

**Modificaciones en `combined_analyzer.py`**:
```python
# Serializar traza para la respuesta API
if hasattr(result, 'execution_trace') and result.execution_trace:
    execution_trace_dict = ExecutionTraceSchema(
        steps=[...],
        total_iterations=trace.total_iterations,
        # ...
    )
```

#### 3. **Esquemas de Datos** (`schemas.py`)

Nuevos modelos Pydantic:
```python
class TraceStep(BaseModel):
    step: int
    line: int
    kind: str
    condition: Optional[str]
    variables: Dict[str, Any]
    operation: str
    cost: str
    cumulative_cost: str

class ExecutionTrace(BaseModel):
    steps: List[TraceStep]
    total_iterations: int
    max_depth: int
    variables_tracked: List[str]
    complexity_formula: str
    description: str

class analyzeAstResp(BaseModel):
    # ... campos existentes ...
    execution_trace: Optional[ExecutionTrace]  # 🆕
```

### Frontend (Angular/TypeScript)

#### 1. **Servicio Orchestrator** (`orchestrator.service.ts`)

Interfaces actualizadas:
```typescript
export interface TraceStep {
  step: number;
  line: number;
  kind: string;
  condition?: string;
  variables: { [key: string]: any };
  operation: string;
  cost: string;
  cumulative_cost: string;
}

export interface ExecutionTrace {
  steps: TraceStep[];
  total_iterations: number;
  max_depth: number;
  variables_tracked: string[];
  complexity_formula: string;
  description: string;
}

export interface AnalyzeResponse {
  // ... campos existentes ...
  execution_trace?: ExecutionTrace;  // 🆕
}
```

#### 2. **Componente de Visualización** (`complexity-visualizer.component.ts`)

**Template HTML**: Nueva sección para tabla de traza
```html
<div *ngIf="complexityType === 'iterative' && response.execution_trace" 
     class="trace-container">
  <h3>📊 Seguimiento de Ejecución del Pseudocódigo</h3>
  
  <div class="trace-description">
    <p><strong>Total de Iteraciones:</strong> {{ response.execution_trace.total_iterations }}</p>
    <p><strong>Variables Rastreadas:</strong> {{ response.execution_trace.variables_tracked.join(', ') }}</p>
  </div>

  <table class="trace-table">
    <thead>
      <tr>
        <th>Paso</th>
        <th>Línea</th>
        <th>Condición</th>
        <th>Variables</th>
        <th>Operación</th>
        <th>Costo</th>
        <th>Acumulado</th>
      </tr>
    </thead>
    <tbody>
      <tr *ngFor="let step of response.execution_trace.steps" 
          [ngClass]="getTraceStepClass(step)">
        <td>{{ step.step }}</td>
        <td>{{ step.line }}</td>
        <td>{{ step.condition || '—' }}</td>
        <td>{{ formatVariables(step.variables) }}</td>
        <td>{{ step.operation }}</td>
        <td>{{ step.cost }}</td>
        <td>{{ step.cumulative_cost }}</td>
      </tr>
    </tbody>
  </table>
</div>
```

**Métodos TypeScript**:
```typescript
formatVariables(variables: { [key: string]: any }): string {
  return Object.entries(variables)
    .map(([key, value]) => `${key}=${value}`)
    .join(', ');
}

getExampleSize(): number {
  // Extrae el valor de n usado en la simulación
}

getTraceStepClass(step: any): string {
  // Aplica clases CSS según el tipo de paso
}
```

**Estilos CSS**: Tabla profesional con gradientes y colores
- Fondo verde suave para sección iterativa
- Tabla responsive con scroll horizontal
- Colores distintos para cada columna (condición, variables, etc.)
- Resaltado en hover
- Clases especiales para pasos de inicialización y salida

---

## 🎨 Diseño Visual

### Tabla de Traza de Ejecución

La tabla muestra:

| Paso | Línea | Condición | Variables | Operación | Costo | Acumulado |
|------|-------|-----------|-----------|-----------|-------|-----------|
| 0    | 1     | —         | n=5       | Inicializar n=5 | 1 | 1 |
| 1    | 2     | i ≤ n     | i=1, n=5  | Ejecutar cuerpo | 1 | 2 |
| 2    | 2     | i ≤ n     | i=2, n=5  | Ejecutar cuerpo | 1 | 3 |
| ... | ... | ... | ... | ... | ... | ... |

**Características**:
- **Paso**: Número secuencial de la ejecución
- **Línea**: Línea del pseudocódigo ejecutada
- **Condición**: Expresión evaluada (for/while/if)
- **Variables**: Estado actual de todas las variables
- **Operación**: Descripción de lo que se ejecuta
- **Costo**: Operaciones en este paso
- **Acumulado**: Costo total hasta este paso

---

## 📊 Ejemplos de Salida

### 1. Bucle Simple (O(n))

```
Descripción: Bucle simple que ejecuta n iteraciones
Total de iteraciones: 5
Variables rastreadas: n, i

Paso 0: Inicializar n=5
Paso 1: i=1, n=5 | Ejecutar cuerpo (iteración 1)
Paso 2: i=2, n=5 | Ejecutar cuerpo (iteración 2)
...
Complejidad derivada: O(n)
```

### 2. Bucles Anidados (O(n²))

```
Descripción: Bucles anidados: externo n veces, interno n veces
Total de iteraciones: 16
Profundidad máxima: 2
Variables rastreadas: n, i, j

Paso 0: Inicializar n=4
Paso 1: Iteración externa i=1
Paso 2: Operación en (i=1, j=1)
Paso 3: Operación en (i=1, j=2)
...
Complejidad derivada: O(n²)
```

### 3. Búsqueda Binaria (O(log n))

```
Descripción: En cada iteración se divide el espacio a la mitad
Total de iteraciones: 4
Variables rastreadas: n, left, right, mid

Paso 0: Inicializar búsqueda: left=0, right=15
Paso 1: mid=7, espacio=16 → dividir
Paso 2: mid=3, espacio=7 → dividir
Paso 3: mid=5, espacio=3 → dividir
Paso 4: mid=4, espacio=1 → encontrado

Complejidad derivada: O(log n)
```

---

## 🧪 Pruebas Realizadas

### Tests Unitarios
✅ `test_execution_trace.py` - Todas las funciones de generación
- Bucles simples
- Bucles anidados
- Búsqueda binaria
- Detección automática

### Tests de Integración
✅ `test_integration_trace.py` - Pipeline completo
- Pseudocódigo → Parser → Analizador → Traza → Frontend
- Verificación de respuesta API con campo `execution_trace`

---

## 📦 Archivos Modificados/Creados

### Backend
1. **NUEVO**: `core_analyzer_service/app/iterative/execution_trace.py` (320 líneas)
2. **MODIFICADO**: `core_analyzer_service/app/iterative/api.py`
3. **MODIFICADO**: `core_analyzer_service/app/domain/cost_model.py`
4. **MODIFICADO**: `core_analyzer_service/app/schemas.py`
5. **MODIFICADO**: `core_analyzer_service/app/services/combined_analyzer.py`

### Frontend
1. **MODIFICADO**: `frontend_service/src/app/services/orchestrator.service.ts`
2. **MODIFICADO**: `frontend_service/src/app/components/complexity-visualizer.component.ts`
   - Template HTML (+60 líneas)
   - Estilos CSS (+150 líneas)
   - Métodos TypeScript (+40 líneas)

### Tests
1. **NUEVO**: `core_analyzer_service/test_execution_trace.py`
2. **NUEVO**: `core_analyzer_service/test_integration_trace.py`

---

## 🚀 Cómo Usar

### 1. Analizar un Algoritmo Iterativo

**Backend automáticamente genera la traza cuando detecta código iterativo**:

```python
# El analizador detecta automáticamente bucles y genera la traza
result = analyze_iterative_program(ast)
# result.execution_trace contiene la tabla de seguimiento
```

### 2. Visualizar en el Frontend

La tabla aparece automáticamente bajo "Seguimiento de Ejecución del Pseudocódigo" cuando:
- El algoritmo es iterativo
- Se ha generado una traza válida
- Hay al menos un bucle for/while en el código

### 3. Personalizar el Tamaño de Simulación

Por defecto se usan valores pequeños (n=4, n=5, n=16) para que la tabla sea legible. Esto se puede ajustar en `execution_trace.py`:

```python
def generate_trace_for_simple_loop(ast, param_name="n"):
    n_value = 5  # Cambiar aquí para simular con otros valores
    # ...
```

---

## 🎯 Comparación con Árbol de Recursión

| Aspecto | Recursivo | Iterativo |
|---------|-----------|-----------|
| **Diagrama** | Árbol de recursión (SVG) | Tabla de traza |
| **Visualiza** | Llamadas recursivas anidadas | Iteraciones secuenciales |
| **Muestra** | Subproblemas y combinación | Estado de variables paso a paso |
| **Generación** | LLM (Graphviz) | Simulación directa |
| **Complejidad** | Altura del árbol | Número de iteraciones |

**Ambos cumplen el requisito de "Diagrama de Seguimiento del Pseudocódigo"** pero adaptados al tipo de algoritmo.

---

## 💡 Mejoras Futuras (Opcionales)

1. **Interactividad**: Permitir al usuario ajustar el valor de n en la UI
2. **Visualización gráfica**: Agregar gráficos de barras del costo acumulado
3. **Animación**: Mostrar paso a paso con delays
4. **Exportar**: Descargar tabla como CSV o PDF
5. **Comparación**: Mostrar trazas de mejor/peor caso lado a lado

---

## ✅ Conclusión

Se ha implementado exitosamente el **seguimiento de ejecución del pseudocódigo para algoritmos iterativos**, cumpliendo con el requisito del 15% de la evaluación.

**Características principales**:
- ✅ Generación automática de tablas de traza
- ✅ Simulación con valores concretos
- ✅ Rastreo de estado de variables
- ✅ Cálculo de costo acumulado
- ✅ Visualización profesional en frontend
- ✅ Tests unitarios e integración
- ✅ Documentación completa

**Equivalencia con recursivo**:
- Recursivo: Árbol de recursión (visual con Graphviz)
- Iterativo: Tabla de traza de ejecución (tabular con estado)

Ambos proporcionan un **diagrama de seguimiento** que permite entender cómo se ejecuta el algoritmo paso a paso, facilitando el análisis de complejidad.
