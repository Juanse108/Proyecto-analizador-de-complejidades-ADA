import { Injectable } from '@angular/core';
import { AnalyzeResponse } from './orchestrator.service';

export interface RecursionNode {
  level: number;
  cost: string;
  width: number;
  children: RecursionNode[];
}

export interface RecursionTree {
  root: RecursionNode;
  height: number;
  totalCost: string;
  description: string;
}

export interface TraceRow {
  iteration: number;
  condition: string;
  variable: string;
  cost: string;
  cumulativeCost: string;
}

export interface TraceTable {
  iterations: TraceRow[];
  totalCost: string;
}

@Injectable({
  providedIn: 'root'
})
export class RecursionTreeService {

  /**
   * Analiza la respuesta del analyzer y determina si es recursivo o iterativo
   */
  analyzeComplexity(response: AnalyzeResponse): {
    type: 'recursive' | 'iterative' | 'unknown';
    tree?: RecursionTree;
    table?: TraceTable;
  } {
    const bigO = (response.big_o || '').toLowerCase();
    const notes = response.notes || [];
    const normalizedCode = (response.normalized_code || '').toLowerCase();

    // Detectar si es recursivo o iterativo
    const isRecursive = 
      notes.some(n => n.toLowerCase().includes('recursiv')) ||
      notes.some(n => n.toLowerCase().includes('divide')) ||
      notes.some(n => n.toLowerCase().includes('conquer')) ||
      normalizedCode.includes('return');

    const isIterative =
      notes.some(n => n.toLowerCase().includes('iterativ')) ||
      notes.some(n => n.toLowerCase().includes('loop')) ||
      normalizedCode.includes('for ') ||
      normalizedCode.includes('while ');

    if (isRecursive && !isIterative) {
      return {
        type: 'recursive',
        tree: this.generateRecursionTree(bigO, response)
      };
    } else if (isIterative && !isRecursive) {
      return {
        type: 'iterative',
        table: this.generateTraceTable(bigO, response)
      };
    }

    return { type: 'unknown' };
  }

  /**
   * Genera un árbol de recursión basado en la complejidad
   */
  private generateRecursionTree(bigO: string, response: AnalyzeResponse): RecursionTree {
    let height = 0;
    let totalCost = bigO;

    if (bigO.includes('n log n') || bigO.includes('n*log n')) {
      height = 5;
      totalCost = 'O(n log n)';
    } else if (bigO.includes('log n')) {
      height = 4;
      totalCost = 'O(log n)';
    } else if (bigO.includes('n²') || bigO.includes('n^2')) {
      height = 4;
      totalCost = 'O(n²)';
    } else if (bigO.includes('n') && !bigO.includes('n²')) {
      height = 3;
      totalCost = 'O(n)';
    } else if (bigO.includes('2^n')) {
      height = 5;
      totalCost = 'O(2ⁿ)';
    } else {
      height = 3;
    }

    const root = this.buildRecursiveNode(height, 0, 100);

    return {
      root,
      height,
      totalCost,
      description: `Árbol de recursión - Complejidad ${totalCost}`
    };
  }

  /**
   * Construye nodos recursivamente para el árbol
   */
  private buildRecursiveNode(
    maxLevel: number,
    currentLevel: number,
    width: number
  ): RecursionNode {
    const levelCosts: { [key: number]: string } = {
      0: 'n',
      1: 'n/2 + n/2',
      2: 'n/4 × 4',
      3: '...',
      4: 'O(1)'
    };

    const children: RecursionNode[] = [];
    if (currentLevel < maxLevel - 1) {
      const childWidth = width / 2;
      children.push(
        this.buildRecursiveNode(maxLevel, currentLevel + 1, childWidth)
      );
      children.push(
        this.buildRecursiveNode(maxLevel, currentLevel + 1, childWidth)
      );
    }

    return {
      level: currentLevel,
      cost: levelCosts[currentLevel] || `n/${Math.pow(2, currentLevel)}`,
      width,
      children
    };
  }

  /**
   * Genera tabla de rastreo para algoritmos iterativos
   */
  private generateTraceTable(bigO: string, response: AnalyzeResponse): TraceTable {
    const iterations: TraceRow[] = [];
    let totalCost = bigO;

    if (bigO.includes('n²') || bigO.includes('n^2')) {
      for (let i = 1; i <= 5; i++) {
        iterations.push({
          iteration: i,
          condition: 'i ≤ n',
          variable: `i = ${i}`,
          cost: 'n',
          cumulativeCost: `${i}n`
        });
      }
      totalCost = 'O(n²)';
    } else if (bigO.includes('n') && !bigO.includes('n²')) {
      for (let i = 1; i <= 5; i++) {
        iterations.push({
          iteration: i,
          condition: 'i ≤ n',
          variable: `i = ${i}`,
          cost: '1',
          cumulativeCost: `${i}`
        });
      }
      totalCost = 'O(n)';
    } else if (bigO.includes('log n')) {
      for (let i = 0; i < 4; i++) {
        iterations.push({
          iteration: i + 1,
          condition: 'left ≤ right',
          variable: `mid = (left + right) / 2`,
          cost: '1',
          cumulativeCost: `${i + 1}`
        });
      }
      totalCost = 'O(log n)';
    }

    return {
      iterations,
      totalCost
    };
  }
}