import { Component, Input, OnInit, OnChanges, AfterViewInit, ChangeDetectorRef, ViewChild, ElementRef, Pipe, PipeTransform } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { AnalyzeResponse } from '../services/orchestrator.service';
import { RecursionTreeService, RecursionTree, TraceTable } from '../services/recursion-tree.service';
import * as katex from 'katex';

// Pipe para sanitizar HTML (SVG)
@Pipe({
  name: 'sanitizeHtml',
  standalone: true
})
export class SanitizeHtmlPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(html: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }
}

@Component({
  selector: 'app-complexity-visualizer',
  standalone: true,
  imports: [CommonModule, SanitizeHtmlPipe],
  template: `
    <div class="visualizer-container" *ngIf="response">
      <!-- 1️⃣ Sumatorias y Derivación (Iterativos) - PRIMERO -->
      <div *ngIf="response.algorithm_kind === 'iterative' && response.summations" class="summations-section">
        <h3>🔣 Sumatorias y Derivación</h3>
        
        <!-- Tabs para peor/mejor/promedio -->
        <div class="summations-tabs">
          <ng-container *ngFor="let caseType of summationCases">
            <button 
              *ngIf="response.summations && response.summations[caseType]"
              [class.active]="selectedSummationCase === caseType"
              (click)="selectSummationCase(caseType)"
              class="tab-button">
              {{ getCaseLabel(caseType) }}
            </button>
          </ng-container>
        </div>

        <!-- Contenido de la sumatoria seleccionada -->
        <div class="summation-content" *ngIf="response.summations && response.summations[selectedSummationCase]">
          <div class="summation-formula">
            <!-- Renderizar LaTeX si el objeto tiene propiedad 'latex' -->
            <div *ngIf="isSummationObject(response.summations[selectedSummationCase])" 
                 #latexContainer 
                 class="latex-formula">
            </div>
            <!-- Fallback para strings simples -->
            <pre *ngIf="!isSummationObject(response.summations[selectedSummationCase])">
              {{ response.summations[selectedSummationCase] }}
            </pre>
          </div>
        </div>
      </div>

      <!-- 2️⃣ Análisis de Complejidad - SEGUNDO -->
      <div class="equations-container">
        <h3>📐 Análisis de Complejidad</h3>
        
        <!-- Cotas -->
        <div class="bounds-section">
          <p><strong>Cota Superior:</strong> <span class="complexity-value">O({{ response.big_o }})</span></p>
          <p><strong>Cota Inferior:</strong> <span class="complexity-value">Ω({{ response.big_omega }})</span></p>
          <p *ngIf="response.theta"><strong>Cota Exacta:</strong> <span class="complexity-value">Θ({{ response.theta }})</span></p>
          <p *ngIf="response.method_used"><strong>Método Utilizado:</strong> {{ methodName }}</p>
        </div>

        <!-- Ecuación de Recurrencia (Recursivos)  -->
        <div *ngIf="response.algorithm_kind === 'recursive' && response.recurrence_equation" 
            class="recurrence-section">
          <h4>🔄 Ecuación de Recurrencia</h4>
          <div class="equation-box">
            <pre style="margin: 0; font-family: 'Courier New', monospace; white-space: pre-wrap;">{{ response.recurrence_equation }}</pre>
          </div>
          <p class="equation-note">
            Esta es la ecuación de recurrencia del algoritmo, no su solución.
            La solución asintótica es: {{ response.big_o }}
          </p>
        </div>
      </div>

      <!-- 3️⃣ Fórmula Explícita de Cotas Ajustadas - TERCERO -->
      <div *ngIf="response.strong_bounds" class="formula-section">
        <h3>🔢 Fórmula Explícita con Cotas Ajustadas</h3>
        <div class="equation-box">
          <p>{{ response.strong_bounds.formula }}</p>
        </div>
        <div class="formula-details" *ngIf="response.strong_bounds.dominant_term">
          <p><strong>Término Dominante:</strong> <code>{{ response.strong_bounds.dominant_term }}</code></p>
          <p *ngIf="response.strong_bounds.constant"><strong>Constante Aditiva:</strong> <code>{{ response.strong_bounds.constant }}</code></p>
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
        
        <!-- Cargando LLM -->
        <div *ngIf="isLoadingTree" class="loading-container">
          <div class="spinner"></div>
          <p>⏳ Generando árbol con Graphviz...</p>
          <p class="loading-hint">El LLM está analizando el algoritmo recursivo...</p>
        </div>
        
        <!-- SVG del LLM + Descripción -->
        <div *ngIf="treeSvg && !isLoadingTree">
          <div class="tree-hint">
            💡 Usa scroll si el árbol es muy grande
          </div>
          <div class="svg-tree-container" [innerHTML]="treeSvg | sanitizeHtml"></div>
          
          <!-- Descripción del árbol -->
          <div class="tree-summary" *ngIf="treeDescription">
            <p><strong>Descripción:</strong> {{ treeDescription }}</p>
          </div>
        </div>
      </div>

      <!-- Tabla de Seguimiento de Ejecución (Iterativo) -->
      <div *ngIf="response.algorithm_kind === 'iterative'" class="trace-container">
        <h3>Seguimiento de Ejecución del Pseudocódigo</h3>
        
        <!-- Mostrar traza si existe -->
        <ng-container *ngIf="response.execution_trace && response.execution_trace.steps && response.execution_trace.steps.length > 0; else noTrace">
          <div class="trace-description" *ngIf="response.execution_trace.description">
            <p><strong>Descripción:</strong> {{ response.execution_trace.description }}</p>
            <p><strong>Total de Iteraciones:</strong> {{ response.execution_trace.total_iterations }}</p>
            <p><strong>Profundidad Máxima:</strong> {{ response.execution_trace.max_depth }}</p>
            <p><strong>Variables Rastreadas:</strong> {{ response.execution_trace.variables_tracked.join(', ') }}</p>
          </div>

          <div class="trace-hint">
            💡 Esta tabla muestra cómo evoluciona el algoritmo paso a paso con n={{ getExampleSize() }}
          </div>

          <div class="trace-table-wrapper">
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
                  <td class="step-number">{{ step.step }}</td>
                  <td class="line-number">{{ step.line }}</td>
                  <td class="condition">{{ step.condition || '—' }}</td>
                  <td class="variables">{{ formatVariables(step.variables) }}</td>
                  <td class="operation">{{ step.operation }}</td>
                  <td class="cost">{{ step.cost }}</td>
                  <td class="cumulative">{{ step.cumulative_cost }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="trace-footer">
            <p><strong>Complejidad Derivada:</strong> <code>{{ response.execution_trace.complexity_formula }}</code></p>
            <p class="trace-note">
              Esta tabla muestra una ejecución simulada del algoritmo. 
              Los valores reales dependerán de la entrada específica.
            </p>
          </div>
        </ng-container>

        <!-- Fallback si no hay traza -->
        <ng-template #noTrace>
          <div class="trace-hint" style="background: #fff3e0; border-left-color: #ff9800; color: #e65100;">
            El seguimiento de ejecución no está disponible para este algoritmo.
          </div>
          <div class="trace-description">
            <p><strong>¿Qué debería mostrar aquí?</strong></p>
            <p>Una tabla de seguimiento paso a paso que muestra:</p>
            <ul style="margin: 10px 0; padding-left: 20px;">
              <li>Estado de variables en cada iteración (i, j, n, etc.)</li>
              <li>Condiciones evaluadas en bucles y condicionales</li>
              <li>Operaciones ejecutadas en cada paso</li>
              <li>Costo acumulado de la ejecución</li>
            </ul>
            <p style="margin-top: 10px; padding: 10px; background: #e3f2fd; border-radius: 4px; font-size: 0.9em;">
              <strong>🔧 Para desarrolladores:</strong> El backend necesita incluir el campo <code>execution_trace</code> 
              en la respuesta. Verifica que el servicio <code>core_analyzer_service</code> esté corriendo con los últimos cambios.
            </p>
          </div>
        </ng-template>
      </div>

      <!-- Pantalla de Carga (cuando no se sabe el tipo aún) -->
      <div *ngIf="complexityType === 'unknown'" class="loading-container">
        <div class="spinner"></div>
        <p>⏳ Analizando algoritmo...</p>
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
      margin-bottom: 30px;
      padding: 20px;
      background: #ffebee;
      border-radius: 8px;
      border-left: 5px solid #d32f2f;
    }

    .formula-section h3 {
      margin-top: 0;
      color: #b71c1c;
      margin-bottom: 15px;
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

    /* Sumatorias y Derivación */
    .summations-section {
      margin-bottom: 30px;
      padding: 20px;
      background: #e0f2f1;
      border-radius: 8px;
      border-left: 5px solid #00897b;
    }

    .summations-section h3 {
      color: #00695c;
      margin-top: 0;
    }

    .summations-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 15px;
      border-bottom: 2px solid #e0f2f1;
      padding-bottom: 10px;
    }

    .tab-button {
      padding: 8px 16px;
      background: #f5f5f5;
      border: none;
      border-radius: 4px 4px 0 0;
      cursor: pointer;
      font-size: 0.95em;
      color: #666;
      transition: all 0.3s ease;
      font-weight: 500;
      border-bottom: 3px solid transparent;
    }

    .tab-button:hover {
      background: #e0f2f1;
      color: #00695c;
    }

    .tab-button.active {
      background: #00897b;
      color: white;
      border-bottom: 3px solid #00695c;
    }

    .summation-content {
      animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(-5px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .summation-formula {
      background: #f5f5f5;
      padding: 15px;
      border-radius: 4px;
      border-left: 3px solid #00897b;
      overflow-x: auto;
      font-family: 'Courier New', monospace;
      font-size: 1em;
      line-height: 1.6;
      color: #333;
    }

    .summation-formula pre {
      margin: 0;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: 'Courier New', monospace;
      color: #00695c;
      font-weight: 500;
    }

    /* Contenedor LaTeX */
    .latex-formula {
      background: #f5f5f5;
      padding: 20px;
      border-radius: 4px;
      border-left: 3px solid #00897b;
      overflow-x: auto;
      font-size: 1.1em;
      line-height: 1.8;
      min-height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .latex-formula :global(.katex-display) {
      margin: 0 !important;
      padding: 0 !important;
    }

    .latex-formula :global(.katex) {
      font-size: 1.1em;
    }


    /* Spinner de carga */
    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px 20px;
      background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
      border-radius: 8px;
      border: 2px dashed #7c4dff;
    }

    .spinner {
      border: 4px solid #e0e0e0;
      border-top: 4px solid #7c4dff;
      border-radius: 50%;
      width: 50px;
      height: 50px;
      animation: spin 1s linear infinite;
      margin-bottom: 15px;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .loading-hint {
      font-size: 0.9em;
      color: #666;
      font-style: italic;
      margin-top: 5px;
    }

    .tree-summary {
      margin-top: 20px;
      padding: 15px;
      background: #f5f5f5;
      border-radius: 6px;
      border-left: 4px solid #4caf50;
    }

    .tree-summary p {
      margin: 8px 0;
      line-height: 1.6;
    }

    .tree-hint {
      background: #e3f2fd;
      padding: 10px 15px;
      border-radius: 6px;
      border-left: 4px solid #2196f3;
      margin-bottom: 15px;
      font-size: 0.9em;
      color: #1565c0;
      text-align: center;
      font-weight: 500;
    }

    .svg-tree-container {
      background: white;
      padding: 20px;
      border-radius: 6px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      overflow: auto;
      max-height: 600px;
      max-width: 100%;
      display: block;
      position: relative;
    }

    .svg-tree-container svg {
      display: block;
      height: auto !important;
      width: auto !important;
      max-width: none !important;
    }

    .svg-tree-container::-webkit-scrollbar {
      width: 10px;
      height: 10px;
    }

    .svg-tree-container::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 5px;
    }

    .svg-tree-container::-webkit-scrollbar-thumb {
      background: #888;
      border-radius: 5px;
    }

    .svg-tree-container::-webkit-scrollbar-thumb:hover {
      background: #555;
    }

    /* Estilos para Tabla de Seguimiento de Ejecución */
    .trace-container {
      margin-top: 30px;
      padding: 20px;
      background: linear-gradient(135deg, #e8f5e9 0%, #f1f8e9 100%);
      border-radius: 8px;
      border-left: 5px solid #66bb6a;
    }

    .trace-container h3 {
      color: #2e7d32;
      margin-top: 0;
      margin-bottom: 15px;
    }

    .trace-description {
      background: white;
      padding: 15px;
      border-radius: 6px;
      margin-bottom: 15px;
      border-left: 4px solid #66bb6a;
    }

    .trace-description p {
      margin: 6px 0;
      font-size: 0.95em;
      color: #333;
    }

    .trace-hint {
      background: #fff9c4;
      padding: 10px 15px;
      border-radius: 4px;
      border-left: 3px solid #fbc02d;
      margin: 15px 0;
      font-size: 0.9em;
      color: #f57f17;
    }

    .trace-table-wrapper {
      overflow-x: auto;
      background: white;
      border-radius: 6px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      margin: 15px 0;
    }

    .trace-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9em;
    }

    .trace-table thead {
      background: linear-gradient(135deg, #66bb6a 0%, #81c784 100%);
      color: white;
    }

    .trace-table th {
      padding: 12px 10px;
      text-align: left;
      font-weight: 600;
      border-bottom: 2px solid #4caf50;
    }

    .trace-table td {
      padding: 10px;
      border-bottom: 1px solid #e0e0e0;
    }

    .trace-table tbody tr:hover {
      background: #f1f8e9;
      transition: background 0.2s;
    }

    .trace-table .step-number {
      font-weight: bold;
      color: #2e7d32;
      text-align: center;
      width: 60px;
    }

    .trace-table .line-number {
      text-align: center;
      width: 60px;
      color: #666;
    }

    .trace-table .condition {
      font-family: 'Courier New', monospace;
      color: #1976d2;
      max-width: 150px;
    }

    .trace-table .variables {
      font-family: 'Courier New', monospace;
      color: #6a1b9a;
      max-width: 200px;
      font-size: 0.85em;
    }

    .trace-table .operation {
      color: #424242;
      max-width: 250px;
    }

    .trace-table .cost {
      font-family: 'Courier New', monospace;
      color: #d84315;
      text-align: center;
      width: 70px;
    }

    .trace-table .cumulative {
      font-family: 'Courier New', monospace;
      color: #c62828;
      font-weight: bold;
      text-align: center;
      width: 90px;
    }

    .trace-table .trace-init {
      background: #e3f2fd;
    }

    .trace-table .trace-exit {
      background: #ffebee;
      font-style: italic;
    }

    .trace-footer {
      margin-top: 15px;
      padding: 15px;
      background: white;
      border-radius: 6px;
      border-left: 4px solid #66bb6a;
    }

    .trace-footer p {
      margin: 6px 0;
    }

    .trace-footer code {
      background: #f5f5f5;
      padding: 4px 8px;
      border-radius: 3px;
      color: #2e7d32;
      font-weight: bold;
    }

    .trace-note {
      font-size: 0.85em;
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

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px;
      background: #f0f8ff;
      border-radius: 8px;
      border: 2px dashed #007bff;
      gap: 15px;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 4px solid #f3f3f3;
      border-top: 4px solid #007bff;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .loading-container p {
      margin: 0;
      color: #007bff;
      font-weight: 500;
    }

    .loading-hint {
      font-size: 0.9em;
      color: #666;
      font-style: italic;
      margin-top: 5px;
    }

    .svg-tree-container {
      display: block;
      margin: 20px 0;
      padding: 20px;
      background: #f0f8ff;
      border-radius: 8px;
      border: 2px solid #007bff;
      overflow: auto;
      max-height: 600px;
      max-width: 100%;
    }

    .svg-tree-container svg {
      display: block;
      height: auto !important;
      width: auto !important;
      max-width: none !important;
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
export class ComplexityVisualizerComponent implements OnInit, OnChanges, AfterViewInit {
  @Input() response: AnalyzeResponse | null = null;
  @ViewChild('latexContainer', { read: ElementRef }) latexContainer: ElementRef | null = null;

  complexityType: 'recursive' | 'iterative' | 'unknown' = 'unknown';
  recursionTree: RecursionTree | null = null;
  treeSvg: string | null = null;
  traceTable: TraceTable | null = null;
  isLoadingTree = false;
  treeDescription: string | null = null;
  
  methodName: string = '';
  irExpression: string = '';
  selectedSummationCase: 'worst' | 'best' | 'avg' = 'worst';
  summationCases: Array<'worst' | 'best' | 'avg'> = ['worst', 'best', 'avg'];
  
  private lastAnalyzedCode: string | null = null;

  constructor(
    private recursionTreeService: RecursionTreeService,
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    if (this.response) {
      this.updateAnalysis();
    }
  }

  ngOnChanges(): void {
    if (this.response) {
      // Solo actualizar si el código cambió (evitar re-análisis innecesarios)
      const currentCode = `${this.response.normalized_code}-${this.response.big_o}`;
      if (currentCode !== this.lastAnalyzedCode) {
        this.lastAnalyzedCode = currentCode;
        this.updateAnalysis();
      }
    }
  }

  ngAfterViewInit(): void {
    this.renderSummationLatex();
  }

  private async updateAnalysis(): Promise<void> {
    if (!this.response) return;

    // LIMPIAR ESTADO ANTERIOR
    this.complexityType = 'unknown';
    this.recursionTree = null;
    this.traceTable = null;
    this.treeSvg = null;
    this.treeDescription = null;
    this.isLoadingTree = false;
    this.cdr.detectChanges(); // Forzar renderizado de estado limpio

    try {
      // Mostrar loading si es recursivo
      const normalized = (this.response.normalized_code || '').toLowerCase();
      const hasCallStatement = normalized.includes('call ');
      const hasSelfReference = /\b(fibonacci|factorial|quicksort|mergesort|binary.{0,10}search|hanoi)\b/i.test(this.response.normalized_code || '');
      const hasRecurrence = !!this.response.recurrence_equation;
      
      if (hasCallStatement || hasSelfReference || hasRecurrence || this.response.algorithm_kind === 'recursive') {
        this.isLoadingTree = true;
        this.complexityType = 'recursive';
        this.cdr.detectChanges();
      }

      // Actualizar tipo de complejidad (ahora es async para recursivos)
      const analysis = await this.recursionTreeService.analyzeComplexity(this.response);
      
      this.complexityType = analysis.type;
      this.recursionTree = analysis.tree || null;
      this.traceTable = analysis.table || null;
      this.treeSvg = analysis.svg || null;
      this.treeDescription = analysis.tree?.description || null;
      this.isLoadingTree = false;
    } catch (error) {
      this.complexityType = 'unknown';
      this.isLoadingTree = false;
    }

    // Actualizar nombre del método
    this.methodName = this.formatMethodName(this.response.method_used || '');

    // Actualizar expresión IR
    this.irExpression = this.formatIRExpression(this.response.ir_worst);

    this.cdr.detectChanges();
    
    // Renderizar LaTeX después de actualizar la vista
    setTimeout(() => this.renderSummationLatex(), 100);
  }

  /**
   * Verifica si el objeto es una sumatoria con estructura {latex, text}
   */
  isSummationObject(obj: any): boolean {
    return obj && typeof obj === 'object' && 'latex' in obj && 'text' in obj;
  }

  /**
   * Renderiza la fórmula LaTeX en el contenedor
   */
  private renderSummationLatex(): void {
    if (!this.response?.summations || !this.latexContainer) return;

    const summation = this.response.summations[this.selectedSummationCase];
    if (!summation || !this.isSummationObject(summation)) return;

    const container = this.latexContainer.nativeElement;
    container.innerHTML = ''; // Limpiar contenedor

    try {
      // Cast para acceder a propiedades del objeto
      const summationObj = summation as any;
      
      // Renderizar LaTeX con KaTeX
      const html = katex.renderToString(summationObj.latex, {
        throwOnError: false,
        displayMode: true,
        strict: 'ignore'
      });
      container.innerHTML = html;
      
      // Aplicar estilos
      container.style.marginTop = '15px';
      container.style.padding = '15px';
      container.style.backgroundColor = '#f5f5f5';
      container.style.borderRadius = '6px';
      container.style.border = '1px solid #ddd';
      container.style.overflowX = 'auto';
      container.style.minHeight = '60px';
      container.style.display = 'flex';
      container.style.alignItems = 'center';
      container.style.justifyContent = 'center';
    } catch (error) {
      // Fallback: mostrar texto plano
      const summationObj = summation as any;
      container.textContent = summationObj.text || JSON.stringify(summation);
    }
  }

  /**
   * Cambia el caso de sumatoria y re-renderiza
   */
  selectSummationCase(caseType: 'worst' | 'best' | 'avg'): void {
    this.selectedSummationCase = caseType;
    setTimeout(() => this.renderSummationLatex(), 50);
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

  getCaseLabel(caseType: 'worst' | 'best' | 'avg'): string {
    const labels: { [key: string]: string } = {
      'worst': 'Peor Caso (O)',
      'best': 'Mejor Caso (Ω)',
      'avg': 'Caso Promedio (Θ)'
    };
    return labels[caseType] || caseType;
  }

  /**
   * Formatea el objeto de variables para mostrar en la tabla de traza.
   */
  formatVariables(variables: { [key: string]: any }): string {
    if (!variables || Object.keys(variables).length === 0) {
      return '—';
    }
    
    return Object.entries(variables)
      .map(([key, value]) => `${key}=${value}`)
      .join(', ');
  }

  /**
   * Obtiene el tamaño de ejemplo usado en la traza.
   */
  getExampleSize(): number {
    if (!this.response?.execution_trace) return 5;
    
    // Buscar el valor de 'n' en las variables del primer paso
    const firstStep = this.response.execution_trace.steps[0];
    if (firstStep && firstStep.variables) {
      const nValue = firstStep.variables['n'];
      if (typeof nValue === 'number') {
        return nValue;
      }
    }
    
    return 5; // Valor por defecto
  }

  /**
   * 🆕 Determina la clase CSS para una fila de traza según su tipo
   */
  getTraceStepClass(step: any): string {
    if (step.kind === 'init') {
      return 'trace-init';
    } else if (step.kind === 'exit') {
      return 'trace-exit';
    }
    return '';
  }
}
