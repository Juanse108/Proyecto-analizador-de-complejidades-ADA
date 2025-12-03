import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

export interface AnalyzeRequest {
  code: string;
  objective: 'worst' | 'best' | 'average';
}

export interface AnalyzeResponse {
  normalized_code: string;
  big_o: string;
  big_omega: string;
  theta: string;
  ir?: string;
  notes?: string[];
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
      errorMessage = error.error?.detail || `Error ${error.status}: ${error.statusText}`;
    }

    console.error('Error en Orchestrator Service:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}