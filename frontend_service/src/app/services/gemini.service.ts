import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';

export interface ToGrammarResponse {
  pseudocode_normalizado: string;
  issues: string[];
}

export interface LineCostDetailComparison {
  line: number;
  kind: string;
  text?: string;
  multiplier?: string;
  llm_cost_worst?: string;
  analyzer_cost_worst?: string;
  cost_match?: boolean;
}

export interface ComparisonResponse {
  llm_analysis: {
    big_o: string;
    big_omega: string;
    theta: string;
    reasoning: string;
    method_used?: string;
    ir_worst?: string;
    ir_best?: string;
  };
  comparison: {
    big_o_match: boolean;
    big_omega_match: boolean;
    theta_match: boolean;
    overall_agreement: number;
    differences: string[];
    recommendations: string[];
  };
  summary: string;
  line_analysis?: LineCostDetailComparison[];
}

@Injectable({
  providedIn: 'root'
})
export class GeminiService {
  // Backend API base URL - obtiene las credenciales desde .env del backend
  private backendApiUrl = environment.llmServiceUrl;

  constructor(private http: HttpClient) {}

  async toGrammar(text: string): Promise<ToGrammarResponse> {
    if (!text.trim()) {
      throw new Error('El texto de entrada no puede estar vacío');
    }

    const payload = {
      text: text,
      hints: ''
    };

    try {
      console.log('🔄 Llamando al backend (llm_service)...');
      const response = await firstValueFrom(
        this.http.post<ToGrammarResponse>(
          `${this.backendApiUrl}/to-grammar`,
          payload
        )
      );

      console.log('📨 Respuesta del backend:', response);

      if (!response.pseudocode_normalizado) {
        throw new Error('El pseudocódigo generado está vacío');
      }

      console.log('✅ Pseudocódigo generado correctamente');

      return {
        pseudocode_normalizado: response.pseudocode_normalizado,
        issues: response.issues || []
      };
    } catch (error) {
      console.error('❌ Error en toGrammar:', error);
      throw error;
    }
  }

  async compareAnalysis(pseudocode: string, analyzerResult: {
    big_o: string;
    big_omega: string;
    theta?: string | null;
  }): Promise<ComparisonResponse> {
    if (!pseudocode.trim()) {
      throw new Error('El pseudocódigo no puede estar vacío');
    }

    const payload = {
      pseudocode: pseudocode,
      analyzer_result: {
        big_o: analyzerResult.big_o,
        big_omega: analyzerResult.big_omega,
        theta: analyzerResult.theta || ''
      }
    };

    try {
      console.log('🔄 Llamando al backend para comparación de análisis...');
      const response = await firstValueFrom(
        this.http.post<ComparisonResponse>(
          `${this.backendApiUrl}/compare-analysis`,
          payload
        )
      );

      console.log('📨 Respuesta de comparación:', response);

      return response;
    } catch (error) {
      console.error('❌ Error en compareAnalysis:', error);
      throw error;
    }
  }
}