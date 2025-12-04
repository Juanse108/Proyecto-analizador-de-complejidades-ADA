import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface AnalyzeRequest {
  code: string;
  objective: 'worst' | 'best' | 'average';
}

export interface LineCostDetail {
  line: number;
  kind: string;
  text?: string;
  multiplier?: string;
  cost_worst?: string;
  cost_best?: string;
  cost_avg?: string;
}

export interface StrongBounds {
  formula: string;
  terms: Array<{ expr: string; degree: number[] }>;
  dominant_term: string;
  constant: number;
  evaluated_at?: any;
}

export interface AnalyzeResponse {
  normalized_code: string;
  big_o: string;
  big_omega: string;
  theta?: string;
  ir?: string;
  notes?: string[];
  
  algorithm_kind?: string;
  ir_worst?: any;
  ir_best?: any;
  ir_avg?: any;
  lines?: LineCostDetail[];
  method_used?: string;
  strong_bounds?: StrongBounds;
  summations?: {
    worst?: string;
    best?: string;
    avg?: string;
  };
  
  // 🆕 NUEVO CAMPO
  recurrence_equation?: string;
}

@Injectable({
  providedIn: 'root'
})
export class OrchestratorService {
  private apiUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) { }

  /**
   * Ejecuta el análisis completo del pipeline
   */
  analyze(code: string, objective: 'worst' | 'best' | 'average' = 'worst'): Observable<AnalyzeResponse> {
    const payload: AnalyzeRequest = {
      code: code.trim(),
      objective: objective
    };

    console.log('📤 Enviando al Orchestrator:', payload);

    return this.http.post<AnalyzeResponse>(`${this.apiUrl}/analyze`, payload).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Verificar el estado del orquestador
   */
  healthCheck(): Observable<{ status: string; service: string }> {
    return this.http.get<{ status: string; service: string }>(`${this.apiUrl}/health`).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Manejo centralizado de errores
   */
  private handleError(error: HttpErrorResponse) {
    let errorMessage = 'Error desconocido';

    if (error.error instanceof ErrorEvent) {
      // Error del lado del cliente
      errorMessage = `Error: ${error.error.message}`;
    } else {
      // Error del servidor
      if (error.error?.detail) {
        errorMessage = error.error.detail;
      } else if (error.error?.message) {
        errorMessage = error.error.message;
      } else {
        errorMessage = `Error ${error.status}: ${error.statusText}`;
      }
    }

    console.error('❌ Error en Orchestrator Service:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}