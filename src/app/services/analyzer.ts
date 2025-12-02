import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AnalyzeRequest, AnalyzeResponse } from '../models/analysis.model';

@Injectable({
  providedIn: 'root'
})
export class AnalyzerService {
  private apiUrl = 'http://localhost:8000/analyze'; // Puerto del orchestrator

  constructor(private http: HttpClient) { }

  analyzeCode(code: string, objective: 'worst' | 'best' | 'avg' = 'worst'): Observable<AnalyzeResponse> {
    const payload: AnalyzeRequest = {
      code: code,
      objective: objective
    };
    return this.http.post<AnalyzeResponse>(this.apiUrl, payload);
  }
}