import { Component, Input, OnInit, OnChanges, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AnalyzeResponse } from '../services/orchestrator.service';
import { RecursionTreeService, RecursionTree, TraceTable } from '../services/complexity_visualizer.service';

@Component({
  selector: 'app-complexity-visualizer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="visualizer-container" *ngIf="response">
      <!-- Ecuaciones y Cotas -->
      <div class="equations-container">
        <h3>📐 Análisis de Complejidad</h3>
        
        <!-- Cotas -->
        <div class="bounds-section">
          <p><strong>Cota Superior:</strong> <span class="complexity-value">O({{ response.big_o }})</span></p>
          <p><strong>Cota Inferior:</strong> <span class="complexity-value">Ω({{ response.big_omega }})</span></p>
          <p *ngIf="response.theta"><strong>Cota Exacta:</strong> <span class="complexity-value">Θ({{ response.theta }})</span></p>
          <p *ngIf="response.method_used"><strong>Método Utilizado:</strong> {{ methodName }}</p>
        </div>

        <!-- Fórmula Explícita de Cotas Ajustadas -->
        <div *ngIf="response.strong_bounds" class="formula-section">
          <h4>🔢 Fórmula Explícita con Cotas Ajustadas</h4>
          <div class="equation-box">
            <p>{{ response.strong_bounds.formula }}</p>
          </div>
          <div class="formula-details" *ngIf="response.strong_bounds.dominant_term">
            <p><strong>Término Dominante:</strong> <code>{{ response.strong_bounds.dominant_term }}</code></p>
            <p *ngIf="response.strong_bounds.constant"><strong>Constante Aditiva:</strong> <code>{{ response.strong_bounds.constant }}</code></p>
          </div>
        </div>

        <!-- Ecuación de Recurrencia (Recursivos) -->
        <div *ngIf="response.algorithm_kind === 'recursive' && response.ir_worst" class="recurrence-section">
          <h4>🔄 Ecuación de Recurrencia</h4>
          <div class="equation-box">
            <p>{{ irExpression }}</p>
          </div>
          <p class="equation-note">Peor caso: {{ response.big_o }}</p>
        </div>

        <!-- Ecuación Explícita (Iterativos) -->
        <div *ngIf="response.algorithm_kind === 'iterative' && response.ir_worst" class="explicit-section">
          <h4>📊 Expresión del Peor Caso</h4>
          <div class="equation-box">
            <p>{{ irExpression }}</p>
          </div>
          <p class="equation-note">Complejidad: {{ response.big_o }}</p>
        </div>
      </div>

      <!-- Análisis Línea por Línea -->
      <div *ngIf="response.lines && response.lines.length > 0" class="line-analysis-container">
        <h3>📝 Análisis Línea por Línea</h3>
        <div class="line-analysis-summary">
          <p><strong>Total de líneas analizadas:</strong> {{ response.lines.length }}</p>
          <p><strong>Costo acumulado (peor caso):</strong> <code>{{ response.big_o }}</code></p>
        </div>
        <table class="line-cost-table">
          <thead>
            <tr>
              <th>Línea</th>
              <th>Tipo</th>
              <th>Multiplicador</th>
              <th>Peor Caso</th>
              <th>Mejor Caso</th>
              <th>Caso Promedio</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let line of response.lines" [ngClass]="'kind-' + line.kind">
              <td class="line-number">{{ line.line > 0 ? line.line : '—' }}</td>
              <td class="line-kind" [title]="getKindDescription(line.kind)">{{ formatKindName(line.kind) }}</td>
              <td class="line-multiplier">{{ line.multiplier || '1' }}</td>
              <td class="cost-value">{{ line.cost_worst || '—' }}</td>
              <td class="cost-value">{{ line.cost_best || '—' }}</td>
              <td class="cost-value">{{ line.cost_avg || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Árbol de Recursión -->
      <div *ngIf="complexityType === 'recursive'" class="tree-container">
        <h3>🌳 Árbol de Recursión</h3>
        <div class="tree" *ngIf="recursionTree">
          <div class="tree-node">
            <div class="node-box">{{ recursionTree.root.cost }}</div>
            <div class="node-children" *ngIf="recursionTree.root.children.length > 0">
              <div *ngFor="let child of recursionTree.root.children" class="child-node">
                {{ child.cost }}
              </div>
            </div>
          </div>
          <div class="tree-summary">
            <p><strong>Altura:</strong> {{ recursionTree.height }}</p>
            <p><strong>Costo Total:</strong> {{ recursionTree.totalCost }}</p>
            <p><strong>Descripción:</strong> {{ recursionTree.description }}</p>
          </div>
        </div>
      </div>

      <!-- Tabla de Rastreo -->
      <div *ngIf="complexityType === 'iterative'" class="table-container">
        <h3>📊 Tabla de Rastreo</h3>
        <table *ngIf="traceTable" class="trace-table">
          <thead>
            <tr>
              <th>Iteración</th>
              <th>Condición</th>
              <th>Variable</th>
              <th>Costo</th>
              <th>Costo Acumulado</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let row of traceTable.iterations">
              <td>{{ row.iteration }}</td>
              <td>{{ row.condition }}</td>
              <td>{{ row.variable }}</td>
              <td>{{ row.cost }}</td>
              <td>{{ row.cumulativeCost }}</td>
            </tr>
            <tr class="summary-row">
              <td colspan="5"><strong>Total:</strong> {{ traceTable.totalCost }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Desconocido -->
      <div *ngIf="complexityType === 'unknown'" class="unknown-container">
        <p>ℹ️ No se pudo determinar si el algoritmo es recursivo o iterativo.</p>
        <p>Verifica que el análisis incluya información suficiente.</p>
      </div>
    </div>
  `,
  styles: [`
    .visualizer-container {
      margin: 20px 0;
      padding: 20px;
      background: #f9f9f9;
      border-radius: 8px;
      border: 1px solid #ddd;
    }

    /* Fórmula Explícita */
    .formula-section {
      margin-top: 15px;
      padding: 15px;
      background: white;
      border-radius: 6px;
      border-left: 4px solid #d32f2f;
    }

    .formula-section h4 {
      margin-top: 0;
      color: #b71c1c;
      margin-bottom: 10px;
    }

    .formula-details {
      margin-top: 12px;
      padding: 10px;
      background: #ffebee;
      border-radius: 4px;
      border-left: 3px solid #d32f2f;
    }

    .formula-details p {
      margin: 6px 0;
      font-size: 0.95em;
      color: #c62828;
    }

    .formula-details code {
      background: #fff5f5;
      padding: 2px 6px;
      border-radius: 3px;
      font-weight: bold;
      color: #b71c1c;
    }
    .equations-container {
      margin-bottom: 30px;
      padding: 20px;
      background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
      border-radius: 8px;
      border-left: 5px solid #7c4dff;
    }

    .equations-container h3 {
      color: #4a148c;
      margin-top: 0;
    }

    .bounds-section {
      padding: 15px;
      background: white;
      border-radius: 6px;
      margin-bottom: 15px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .bounds-section p {
      margin: 8px 0;
      font-size: 1em;
    }

    .complexity-value {
      background: #fff3e0;
      padding: 4px 8px;
      border-radius: 4px;
      font-weight: bold;
      color: #e65100;
      font-family: 'Courier New', monospace;
    }

    .recurrence-section, .explicit-section {
      margin-top: 15px;
      padding: 15px;
      background: white;
      border-radius: 6px;
      border-left: 4px solid #7c4dff;
    }

    .recurrence-section h4, .explicit-section h4 {
      margin-top: 0;
      color: #4a148c;
      margin-bottom: 10px;
    }

    .equation-box {
      background: #f5f5f5;
      padding: 15px;
      border-radius: 4px;
      border-left: 3px solid #7c4dff;
      font-family: 'Courier New', monospace;
      font-size: 1.1em;
      overflow-x: auto;
      min-height: 40px;
      display: flex;
      align-items: center;
    }

    .equation-box p {
      margin: 0;
      color: #333;
      font-weight: 500;
    }

    .equation-note {
      margin-top: 8px;
      font-size: 0.9em;
      color: #666;
      font-style: italic;
    }

    /* Análisis Línea por Línea */
    .line-analysis-container {
      margin-bottom: 30px;
      padding: 20px;
      background: #f0f4c3;
      border-radius: 8px;
      border-left: 5px solid #827717;
    }

    .line-analysis-container h3 {
      color: #33691e;
      margin-top: 0;
    }

    .line-analysis-summary {
      padding: 12px 15px;
      background: white;
      border-radius: 6px;
      margin-bottom: 15px;
      border-left: 3px solid #827717;
    }

    .line-analysis-summary p {
      margin: 6px 0;
      font-size: 0.95em;
      color: #558b2f;
    }

    .line-analysis-summary code {
      background: #f1f8e9;
      padding: 2px 6px;
      border-radius: 3px;
      font-weight: bold;
      color: #33691e;
      font-family: 'Courier New', monospace;
    }

    .line-cost-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 15px;
      background: white;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      border-radius: 4px;
      overflow: hidden;
    }

    .line-cost-table th {
      background: linear-gradient(135deg, #827717 0%, #558b2f 100%);
      color: white;
      padding: 12px;
      text-align: left;
      font-weight: bold;
      font-size: 0.95em;
    }

    .line-cost-table td {
      padding: 10px 12px;
      border-bottom: 1px solid #e0e0e0;
      font-size: 0.9em;
    }

    .line-cost-table tbody tr {
      transition: background-color 0.2s;
    }

    .line-cost-table tbody tr:hover {
      background: #fffde7;
    }

    .line-number {
      font-weight: bold;
      color: #558b2f;
      width: 60px;
      text-align: center;
    }

    .line-kind {
      font-size: 0.85em;
      text-transform: uppercase;
      font-weight: bold;
      width: 90px;
    }

    .kind-assign { color: #1976d2; background: #e3f2fd; padding: 4px 6px; border-radius: 3px; }
    .kind-conditional { color: #d32f2f; background: #ffebee; padding: 4px 6px; border-radius: 3px; }
    .kind-if { color: #d32f2f; background: #ffebee; padding: 4px 6px; border-radius: 3px; }
    .kind-loop { color: #f57c00; background: #fff3e0; padding: 4px 6px; border-radius: 3px; }
    .kind-while { color: #f57c00; background: #fff3e0; padding: 4px 6px; border-radius: 3px; }
    .kind-for { color: #f57c00; background: #fff3e0; padding: 4px 6px; border-radius: 3px; }
    .kind-function_call { color: #7b1fa2; background: #f3e5f5; padding: 4px 6px; border-radius: 3px; }
    .kind-return { color: #00796b; background: #e0f2f1; padding: 4px 6px; border-radius: 3px; }

    .line-multiplier {
      font-family: 'Courier New', monospace;
      text-align: center;
      background: #f5f5f5;
      border-radius: 3px;
      font-weight: bold;
      color: #333;
    }

    .cost-value {
      font-family: 'Courier New', monospace;
      text-align: center;
      background: #e8f5e9;
      border-radius: 3px;
      font-weight: 500;
      color: #2e7d32;
    }

    /* Árbol de Recursión */
    .tree-container, .table-container {
      margin-top: 20px;
    }

    .tree {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 20px;
    }

    .tree-node {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
    }

    .node-box {
      background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
      color: white;
      padding: 12px 20px;
      border-radius: 6px;
      font-weight: bold;
      font-size: 1.1em;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .node-children {
      display: flex;
      gap: 15px;
      justify-content: center;
      flex-wrap: wrap;
      margin-top: 15px;
    }

    .child-node {
      background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
      color: white;
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 0.9em;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .tree-summary {
      margin-top: 20px;
      padding: 15px;
      background: #e7f3ff;
      border-radius: 6px;
      border-left: 4px solid #007bff;
      width: 100%;
    }

    .tree-summary p {
      margin: 8px 0;
      color: #004085;
    }

    /* Tabla de Rastreo */
    .trace-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 15px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .trace-table th, .trace-table td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid #ddd;
    }

    .trace-table th {
      background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
      color: white;
      font-weight: bold;
    }

    .trace-table tbody tr:hover {
      background: #f5f5f5;
    }

    .summary-row {
      background: #e7f3ff;
      font-weight: bold;
      border-top: 2px solid #007bff;
    }

    .unknown-container {
      padding: 15px;
      background: #fff3cd;
      border-radius: 6px;
      border-left: 4px solid #ffc107;
      color: #856404;
    }
  `]
})
export class ComplexityVisualizerComponent implements OnInit, OnChanges {
  @Input() response: AnalyzeResponse | null = null;

  complexityType: 'recursive' | 'iterative' | 'unknown' = 'unknown';
  recursionTree: RecursionTree | null = null;
  traceTable: TraceTable | null = null;
  
  methodName: string = '';
  irExpression: string = '';

  constructor(
    private recursionTreeService: RecursionTreeService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    if (this.response) {
      this.updateAnalysis();
    }
  }

  ngOnChanges(): void {
    if (this.response) {
      this.updateAnalysis();
    }
  }

  private updateAnalysis(): void {
    if (!this.response) return;

    // Actualizar tipo de complejidad
    const analysis = this.recursionTreeService.analyzeComplexity(this.response);
    this.complexityType = analysis.type;
    this.recursionTree = analysis.tree || null;
    this.traceTable = analysis.table || null;

    // Actualizar nombre del método
    this.methodName = this.formatMethodName(this.response.method_used || '');

    // Actualizar expresión IR
    this.irExpression = this.formatIRExpression(this.response.ir_worst);

    this.cdr.detectChanges();
  }

  formatMethodName(method: string): string {
    const methodNames: { [key: string]: string } = {
      'master_theorem': 'Master Theorem',
      'characteristic_equation': 'Characteristic Equation',
      'iteration_method': 'Iteration Method',
      'recursion_tree': 'Recursion Tree',
      'summation_analysis': 'Summation Analysis',
      'pattern_matching': 'Pattern Matching',
      'iteration': 'Iterative Analysis'
    };
    return methodNames[method] || method.replace(/_/g, ' ').toUpperCase();
  }

  formatKindName(kind: string): string {
    const kindNames: { [key: string]: string } = {
      'assign': 'Asig.',
      'assignment': 'Asig.',
      'conditional': 'Cond.',
      'if': 'Si',
      'loop': 'Bucle',
      'while': 'Mientras',
      'for': 'Para',
      'function_call': 'Llamada',
      'return': 'Retorno',
      'declaration': 'Decl.',
      'comparison': 'Comp.',
      'arithmetic': 'Arith.'
    };
    return kindNames[kind] || kind.substring(0, 6);
  }

  getKindDescription(kind: string): string {
    const descriptions: { [key: string]: string } = {
      'assign': 'Asignación de variable',
      'assignment': 'Asignación de variable',
      'conditional': 'Rama condicional (if/else)',
      'if': 'Rama condicional (if)',
      'loop': 'Bucle (for/while)',
      'while': 'Bucle mientras',
      'for': 'Bucle para',
      'function_call': 'Llamada a función',
      'return': 'Retorno de función',
      'declaration': 'Declaración de variable',
      'comparison': 'Comparación',
      'arithmetic': 'Operación aritmética'
    };
    return descriptions[kind] || kind;
  }

  private formatIRExpression(irObj: any): string {
    if (!irObj) return 'N/A';
    
    if (typeof irObj === 'object') {
      try {
        return this.irObjectToString(irObj);
      } catch {
        return JSON.stringify(irObj).substring(0, 100) + '...';
      }
    }
    
    return String(irObj);
  }

  private irObjectToString(obj: any, depth: number = 0): string {
    if (depth > 3) return '...';
    
    if (obj === null || obj === undefined) return 'ε';
    if (typeof obj === 'string' || typeof obj === 'number') return String(obj);
    if (typeof obj === 'boolean') return obj ? 'T' : 'F';

    if (Array.isArray(obj)) {
      if (obj.length === 0) return '∅';
      const terms = obj.map(item => this.irObjectToString(item, depth + 1)).filter(s => s);
      return terms.join(' + ');
    }

    if (typeof obj === 'object') {
      if (obj.k !== undefined) return `${obj.k}`;
      if (obj.name !== undefined) return obj.name;
      
      if (obj.log) {
        const arg = obj.log.arg?.name || 'n';
        const base = obj.log.base || 2;
        return `log₍${base}₎(${arg})`;
      }
      
      if (obj.terms && Array.isArray(obj.terms)) {
        const terms = obj.terms.map((t: any) => this.irObjectToString(t, depth + 1)).filter((s: string) => s);
        return terms.join(' + ');
      }
      
      if (obj.alt && Array.isArray(obj.alt)) {
        const alts = obj.alt.map((a: any) => this.irObjectToString(a, depth + 1)).filter((s: string) => s);
        return `max(${alts.join(', ')})`;
      }
      
      const keys = Object.keys(obj);
      if (keys.length === 1) {
        const key = keys[0];
        const value = this.irObjectToString(obj[key], depth + 1);
        return value;
      }
    }

    return 'T(n)';
  }
}