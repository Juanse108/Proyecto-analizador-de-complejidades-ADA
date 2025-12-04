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
  height: number | string;
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

  analyzeComplexity(response: AnalyzeResponse): {
    type: 'recursive' | 'iterative' | 'unknown';
    tree?: RecursionTree;
    table?: TraceTable;
  } {
    const normalized = (response.normalized_code || '').toLowerCase();
    const bigO = (response.big_o || '').toLowerCase();

    // Detectar si es recursivo o iterativo
    const isRecursive = 
      response.algorithm_kind === 'recursive' ||
      normalized.includes('call ') ||
      !!response.recurrence_equation;

    const isIterative =
      response.algorithm_kind === 'iterative' ||
      normalized.includes('for ') ||
      normalized.includes('while ');

    if (isRecursive && !isIterative) {
      return {
        type: 'recursive',
        tree: this.generateRecursionTree(normalized, bigO, response)
      };
    } else if (isIterative && !isRecursive) {
      return {
        type: 'iterative',
        table: this.generateTraceTable(bigO, response)
      };
    }

    return { type: 'unknown' };
  }

  private generateRecursionTree(code: string, bigO: string, response: AnalyzeResponse): RecursionTree {
    // 🆕 Detección específica por algoritmo
    
    // 1. MergeSort
    if (code.includes('mergesort') || code.includes('merge_sort')) {
      return this.generateMergeSortTree();
    }
    
    // 2. QuickSort
    if (code.includes('quicksort') || code.includes('quick_sort')) {
      return this.generateQuickSortTree(bigO);
    }
    
    // 3. Fibonacci
    if (code.includes('fibonacci') || code.includes('fib(')) {
      return this.generateFibonacciTree();
    }
    
    // 4. Binary Search
    if (code.includes('binarysearch') || code.includes('binary_search')) {
      return this.generateBinarySearchTree();
    }
    
    // 5. Factorial
    if (code.includes('factorial') || code.includes('fact(')) {
      return this.generateFactorialTree();
    }
    
    // Fallback genérico basado en big-O
    return this.generateGenericTree(bigO);
  }

  // ===== ÁRBOLES ESPECÍFICOS =====

  private generateMergeSortTree(): RecursionTree {
    return {
      root: {
        level: 0,
        cost: 'n',
        width: 100,
        children: [
          {
            level: 1,
            cost: 'n/2',
            width: 50,
            children: [
              { level: 2, cost: 'n/4', width: 25, children: [] },
              { level: 2, cost: 'n/4', width: 25, children: [] }
            ]
          },
          {
            level: 1,
            cost: 'n/2',
            width: 50,
            children: [
              { level: 2, cost: 'n/4', width: 25, children: [] },
              { level: 2, cost: 'n/4', width: 25, children: [] }
            ]
          }
        ]
      },
      height: 'log₂(n)',
      totalCost: 'O(n log n)',
      description: 'MergeSort: División balanceada en 2 subproblemas de tamaño n/2. Cada nivel cuesta Θ(n). Con log₂(n) niveles, el costo total es Θ(n log n).'
    };
  }

  private generateQuickSortTree(bigO: string): RecursionTree {
    if (bigO.includes('n²') || bigO.includes('n^2')) {
      // Peor caso: desbalanceado (cadena lineal)
      return {
        root: {
          level: 0,
          cost: 'n',
          width: 100,
          children: [
            {
              level: 1,
              cost: 'n-1',
              width: 90,
              children: [
                {
                  level: 2,
                  cost: 'n-2',
                  width: 80,
                  children: [
                    { level: 3, cost: '...', width: 70, children: [] }
                  ]
                }
              ]
            }
          ]
        },
        height: 'n',
        totalCost: 'O(n²)',
        description: 'QuickSort (peor caso): Pivote siempre es el mínimo/máximo. Genera una cadena lineal n → n-1 → n-2 → ... → 1 con altura n. Costo por nivel ≈ n, total Θ(n²).'
      };
    } else {
      // Mejor/promedio caso: balanceado (como MergeSort)
      return this.generateQuickSortBalancedTree();
    }
  }

  private generateQuickSortBalancedTree(): RecursionTree {
    return {
      root: {
        level: 0,
        cost: 'n',
        width: 100,
        children: [
          {
            level: 1,
            cost: 'n/2',
            width: 50,
            children: [
              { level: 2, cost: 'n/4', width: 25, children: [] },
              { level: 2, cost: 'n/4', width: 25, children: [] }
            ]
          },
          {
            level: 1,
            cost: 'n/2',
            width: 50,
            children: [
              { level: 2, cost: 'n/4', width: 25, children: [] },
              { level: 2, cost: 'n/4', width: 25, children: [] }
            ]
          }
        ]
      },
      height: 'log₂(n)',
      totalCost: 'O(n log n)',
      description: 'QuickSort (mejor/promedio caso): Pivote divide razonablemente. Árbol balanceado con 2 subproblemas de tamaño ≈ n/2. Altura log₂(n). Costo por nivel ≈ n, total Θ(n log n).'
    };
  }

  private generateFibonacciTree(): RecursionTree {
    return {
      root: {
        level: 0,
        cost: 'T(n)',
        width: 100,
        children: [
          {
            level: 1,
            cost: 'T(n-1)',
            width: 60,
            children: [
              { level: 2, cost: 'T(n-2)', width: 30, children: [] },
              { level: 2, cost: 'T(n-3)', width: 30, children: [] }
            ]
          },
          {
            level: 1,
            cost: 'T(n-2)',
            width: 40,
            children: [
              { level: 2, cost: 'T(n-3)', width: 20, children: [] },
              { level: 2, cost: 'T(n-4)', width: 20, children: [] }
            ]
          }
        ]
      },
      height: 'n',
      totalCost: 'O(2^n)',
      description: 'Fibonacci recursivo: Árbol binario donde cada nodo T(n) se divide en T(n-1) y T(n-2). Altura ≈ n. Número de nodos ≈ Φ(φ^n) ≈ O(2^n), donde φ ≈ 1.618 (razón áurea). Por tanto, costo total Θ(φ^n) ≈ O(2^n).'
    };
  }

  private generateBinarySearchTree(): RecursionTree {
    return {
      root: {
        level: 0,
        cost: 'n',
        width: 100,
        children: [
          {
            level: 1,
            cost: 'n/2',
            width: 100,
            children: [
              {
                level: 2,
                cost: 'n/4',
                width: 100,
                children: [
                  { level: 3, cost: '...', width: 100, children: [] }
                ]
              }
            ]
          }
        ]
      },
      height: 'log₂(n)',
      totalCost: 'O(log n)',
      description: 'Binary Search recursivo: Una única rama que reduce el espacio búsqueda a la mitad en cada nivel (n → n/2 → n/4 → ... → 1). Altura: log₂(n). Trabajo por nivel: O(1). Costo total: O(log n).'
    };
  }

  private generateFactorialTree(): RecursionTree {
    return {
      root: {
        level: 0,
        cost: 'n',
        width: 100,
        children: [
          {
            level: 1,
            cost: 'n-1',
            width: 100,
            children: [
              {
                level: 2,
                cost: 'n-2',
                width: 100,
                children: [
                  { level: 3, cost: '...', width: 100, children: [] }
                ]
              }
            ]
          }
        ]
      },
      height: 'n',
      totalCost: 'O(n)',
      description: 'Factorial recursivo: Cadena lineal n → n-1 → n-2 → ... → 1. Altura: n. Trabajo por nivel: O(1). Costo total: O(n).'
    };
  }

  private generateGenericTree(bigO: string): RecursionTree {
    // Fallback basado en big-O
    if (bigO.includes('log')) {
      return this.generateBinarySearchTree();
    } else if (bigO.includes('2^n')) {
      return this.generateFibonacciTree();
    } else {
      return this.generateMergeSortTree();
    }
  }

  // ===== TABLA ITERATIVA (sin cambios) =====

  private generateTraceTable(bigO: string, response: AnalyzeResponse): TraceTable {
    const iterations: TraceRow[] = [];

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
      return { iterations, totalCost: 'O(n²)' };
    }

    if (bigO.includes('log')) {
      for (let i = 0; i < 4; i++) {
        iterations.push({
          iteration: i + 1,
          condition: 'left ≤ right',
          variable: `mid = (left + right) / 2`,
          cost: '1',
          cumulativeCost: `${i + 1}`
        });
      }
      return { iterations, totalCost: 'O(log n)' };
    }

    // Por defecto: O(n)
    for (let i = 1; i <= 5; i++) {
      iterations.push({
        iteration: i,
        condition: 'i ≤ n',
        variable: `i = ${i}`,
        cost: '1',
        cumulativeCost: `${i}`
      });
    }
    return { iterations, totalCost: 'O(n)' };
  }
}