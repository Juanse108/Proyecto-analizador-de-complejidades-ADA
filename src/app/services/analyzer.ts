import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AnalyzeRequest, AnalyzeResponse } from '../models/analysis.model';

@Injectable({
  providedIn: 'root'
})
export class AnalyzerService {
  // Asegúrate de que este puerto coincida con tu Orchestrator Service en docker-compose
  private apiUrl = 'http://localhost:8003/analyze'; 

  constructor(private http: HttpClient) { }

  analyzeCode(code: string): Observable<AnalyzeResponse> {
    const payload: AnalyzeRequest = {
      code: code,
      objective: 'worst' // Por defecto
    };
    return this.http.post<AnalyzeResponse>(this.apiUrl, payload);
  }
}