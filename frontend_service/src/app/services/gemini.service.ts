import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export interface ToGrammarResponse {
  pseudocode_normalizado: string;
  issues: string[];
}

export interface ComparisonRequest {
  pseudocode: string;
  analyzer_result: {
    big_o: string;
    big_omega: string;
    theta: string;
  };
}

export interface ComparisonResponse {
  llm_analysis: {
    big_o: string;
    big_omega: string;
    theta: string;
    reasoning: string;
  };
  comparison: {
    big_o_match: boolean;
    big_omega_match: boolean;
    theta_match: boolean;
    overall_agreement: number; // 0-100
    differences: string[];
    recommendations: string[];
  };
  summary: string;
}

export interface GeminiRequest {
  contents: Array<{
    parts: Array<{
      text: string;
    }>;
  }>;
}

export interface GeminiResponse {
  candidates: Array<{
    content: {
      parts: Array<{
        text: string;
      }>;
    };
  }>;
}

// --- REGLAS DEL SISTEMA ---
const SYSTEM_RULES = `
Eres un convertidor a un dialecto ESTRICTO de pseudocódigo basado en Pascal.
Tu tarea es tomar una descripción en lenguaje natural de un algoritmo
y devolver SOLO un JSON minificado exactamente así:
{"pseudocode_normalizado":"<string>","issues":["<string>",...]}

REGLAS DURAS:
- TODOS los cuerpos de IF, WHILE y FOR deben ir con 'begin' y 'end'.
- 'begin' y 'end' DEBEN ir SIEMPRE solos en su propia línea.
- Por cada 'begin' debe haber exactamente un 'end' correspondiente.
- NO uses bloques de código markdown (no uses \`\`\`).
- NO escribas texto en lenguaje natural fuera de comentarios.
- Asignación: variable <- expresión
- Ciclo FOR: for i <- 1 to n do
- Ciclo WHILE: while (condición) do
- IF: if (condición) then ... else ...
- Valores Booleanos: T (true) y F (false)

EJEMPLO VÁLIDO:
{
  "pseudocode_normalizado": "algorithm BinarySearch(array A, integer n, integer target)\\nbegin\\n  left <- 1\\n  right <- n\\n  while (left <= right) do\\n  begin\\n    mid <- (left + right) / 2\\n    if A[mid] = target then\\n    begin\\n      return mid\\n    end\\n    else\\n    begin\\n      if A[mid] < target then\\n      begin\\n        left <- mid + 1\\n      end\\n      else\\n      begin\\n        right <- mid - 1\\n      end\\n    end\\n  end\\n  return -1\\nend",
  "issues": []
}
`;

@Injectable({
  providedIn: 'root'
})
export class GeminiService {
  private apiKey = 'AIzaSyAHecVUUB9dgXHlxqdQeKLB5yk8UVndIuM';
  private model = 'gemini-2.0-flash';
  private apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${this.model}:generateContent`;

  constructor(private http: HttpClient) {}

  /**
   * Convierte texto en lenguaje natural a pseudocódigo normalizado
   */
  async toGrammar(text: string): Promise<ToGrammarResponse> {
    if (!text.trim()) {
      throw new Error('El texto de entrada no puede estar vacío');
    }

    const userPrompt = `
Convierte la siguiente descripción de algoritmo a pseudocódigo normalizado:

"${text}"

Responde SOLO con un JSON válido, sin explicaciones adicionales.
El JSON debe tener exactamente esta estructura:
{
  "pseudocode_normalizado": "...",
  "issues": [...]
}
`;

    try {
      console.log('🔄 Llamando a Gemini 2.0...');
      const response = await this.callGemini(userPrompt, SYSTEM_RULES);
      
      console.log('📨 Respuesta bruta de Gemini:', response);
      
      // Limpiar la respuesta (eliminar markdown backticks si existen)
      let cleanedResponse = response
        .replace(/```json\n?/g, '')
        .replace(/```\n?/g, '')
        .trim();

      console.log('🧹 Respuesta limpia:', cleanedResponse);
      
      // Intentar extraer JSON si está envuelto en texto
      const jsonMatch = cleanedResponse.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        cleanedResponse = jsonMatch[0];
        console.log('📍 JSON extraído:', cleanedResponse);
      }

      // Parsear JSON
      let parsed: ToGrammarResponse;
      try {
        parsed = JSON.parse(cleanedResponse);
      } catch (parseError) {
        console.error('❌ Error al parsear JSON:', parseError);
        console.error('Contenido intentado:', cleanedResponse);
        throw new Error(`JSON inválido: ${cleanedResponse.substring(0, 100)}...`);
      }
      
      if (!parsed.pseudocode_normalizado) {
        console.error('⚠️ Pseudocódigo vacío en respuesta:', parsed);
        throw new Error('El pseudocódigo generado está vacío');
      }

      console.log('✅ Pseudocódigo parseado correctamente');

      return {
        pseudocode_normalizado: parsed.pseudocode_normalizado,
        issues: parsed.issues || []
      };
    } catch (error) {
      console.error('❌ Error en toGrammar:', error);
      throw error;
    }
  }

  /**
   * Compara el análisis del LLM con el del analyzer del backend
   */
  async compareAnalysis(pseudocode: string, analyzerResult: {
    big_o: string;
    big_omega: string;
    theta: string;
  }): Promise<ComparisonResponse> {
    if (!pseudocode.trim()) {
      throw new Error('El pseudocódigo no puede estar vacío');
    }

    const comparisonPrompt = `
Eres un experto en análisis de complejidad algorítmica. Tu tarea es analizar el siguiente pseudocódigo
y comparar tu análisis con el resultado proporcionado por un analyzer automático.

PSEUDOCÓDIGO A ANALIZAR:
\`\`\`
${pseudocode}
\`\`\`

RESULTADO DEL ANALYZER (que queremos verificar):
- O(n): ${analyzerResult.big_o}
- Ω(n): ${analyzerResult.big_omega}
- Θ(n): ${analyzerResult.theta}

Por favor:
1. Analiza el pseudocódigo independientemente
2. Calcula la complejidad: O(n), Ω(n), Θ(n)
3. Compara tus resultados con los del analyzer
4. Explica las diferencias (si las hay)

Responde SOLO con un JSON válido, sin explicaciones adicionales. Estructura exacta:
{
  "llm_analysis": {
    "big_o": "O(...)",
    "big_omega": "Ω(...)",
    "theta": "Θ(...)",
    "reasoning": "Explicación del análisis LLM"
  },
  "comparison": {
    "big_o_match": true/false,
    "big_omega_match": true/false,
    "theta_match": true/false,
    "overall_agreement": 85,
    "differences": ["Diferencia 1", "Diferencia 2"],
    "recommendations": ["Recomendación 1", "Recomendación 2"]
  },
  "summary": "Resumen de la comparación"
}
`;

    try {
      console.log('🔄 Llamando a Gemini 2.0 para comparación...');
      const response = await this.callGemini(comparisonPrompt, 'Eres un experto en complejidad algorítmica');
      
      console.log('📨 Respuesta bruta:', response);
      
      // Limpiar la respuesta (eliminar markdown backticks si existen)
      let cleanedResponse = response
        .replace(/```json\n?/g, '')
        .replace(/```\n?/g, '')
        .trim();

      // Intentar extraer JSON si está envuelto en texto
      const jsonMatch = cleanedResponse.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        cleanedResponse = jsonMatch[0];
      }

      // Parsear JSON
      let parsed: ComparisonResponse;
      try {
        parsed = JSON.parse(cleanedResponse);
      } catch (parseError) {
        console.error('❌ Error al parsear JSON:', parseError);
        throw new Error(`JSON inválido en comparación`);
      }

      console.log('✅ Comparación parseada correctamente');

      return parsed;
    } catch (error) {
      console.error('❌ Error en compareAnalysis:', error);
      throw error;
    }
  }

  /**
   * Llama a la API de Gemini 2.0
   */
  private async callGemini(userPrompt: string, systemInstruction: string): Promise<string> {
    const payload: GeminiRequest = {
      contents: [
        {
          parts: [
            {
              text: `${systemInstruction}\n\n${userPrompt}`
            }
          ]
        }
      ]
    };

    console.log('📤 Enviando a Gemini:', payload);

    try {
      const response = await firstValueFrom(
        this.http.post<GeminiResponse>(
          `${this.apiUrl}?key=${this.apiKey}`,
          payload
        )
      );

      console.log('📥 Respuesta de Gemini API:', response);

      if (!response.candidates || response.candidates.length === 0) {
        throw new Error('No se recibieron candidatos de Gemini');
      }

      const text = response.candidates[0]?.content?.parts?.[0]?.text;
      
      if (!text) {
        throw new Error('La respuesta de Gemini está vacía');
      }

      return text;
    } catch (error: any) {
      if (error instanceof HttpErrorResponse) {
        console.error('❌ Error HTTP de Gemini:', {
          status: error.status,
          statusText: error.statusText,
          message: error.error?.error?.message
        });
        throw new Error(`Error Gemini (${error.status}): ${error.error?.error?.message || error.statusText}`);
      }
      throw error;
    }
  }

  /**
   * Genera un prompt genérico con Gemini
   */
  async generate(userPrompt: string, systemInstruction: string, temperature: number = 0.1): Promise<string> {
    try {
      return await this.callGemini(userPrompt, systemInstruction);
    } catch (error) {
      console.error('❌ Error en generate:', error);
      throw error;
    }
  }
}