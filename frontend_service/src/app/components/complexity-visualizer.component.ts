import { Component, Input, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AnalyzeResponse } from '../services/orchestrator.service';
import { RecursionTreeService, RecursionTree, TraceTable } from '../services/complexity_visualizer.service';

@Component({
  selector: 'app-complexity-visualizer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="visualizer-container" *ngIf="response">
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
export class ComplexityVisualizerComponent implements OnInit {
  @Input() response: AnalyzeResponse | null = null;

  complexityType: 'recursive' | 'iterative' | 'unknown' = 'unknown';
  recursionTree: RecursionTree | null = null;
  traceTable: TraceTable | null = null;

  constructor(
    private recursionTreeService: RecursionTreeService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    if (this.response) {
      const analysis = this.recursionTreeService.analyzeComplexity(this.response);
      this.complexityType = analysis.type;
      this.recursionTree = analysis.tree || null;
      this.traceTable = analysis.table || null;
      this.cdr.detectChanges();
    }
  }

  ngOnChanges(): void {
    if (this.response) {
      const analysis = this.recursionTreeService.analyzeComplexity(this.response);
      this.complexityType = analysis.type;
      this.recursionTree = analysis.tree || null;
      this.traceTable = analysis.table || null;
      this.cdr.detectChanges();
    }
  }
}