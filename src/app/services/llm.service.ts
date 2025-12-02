import { Injectable } from '@angular/core';
import { Observable, from } from 'rxjs';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { environment } from '../../environments/environment';

export interface LLMResponse {
  text: string;
}

@Injectable({
  providedIn: 'root'
})
export class LlmService {
  private genAI: GoogleGenerativeAI;
  private model: any;

  constructor() {
    this.genAI = new GoogleGenerativeAI(environment.geminiApiKey);
    this.model = this.genAI.getGenerativeModel({ model: 'gemini-2.0-flash' });
  }

  generate(userPrompt: string, systemInstruction: string, temperature: number = 0.1): Observable<LLMResponse> {
    const promise: Promise<LLMResponse> = this.model.generateContent({
      contents: [
        {
          role: 'user',
          parts: [{ text: userPrompt }]
        }
      ],
      systemInstruction: systemInstruction,
      generationConfig: {
        temperature: temperature,
        maxOutputTokens: 1024
      }
    }).then((response: any) => {
      const text = response.response.text();
      return { text: text };
    });

    return from(promise);
  }

  normalizeCode(naturalLanguage: string): Observable<LLMResponse> {
    const systemInstruction = `Eres un experto en pseudocódigo. Convierte el lenguaje natural a pseudocódigo siguiendo estas reglas ESTRICTAMENTE:
- Asignación: variable <- expresion
- Ciclo FOR: for variableContadora <- valorInicial to limite do ... end
- Ciclo WHILE: while (condicion) do ... end
- Condicional IF: if (condicion) then ... else ... end
- Subrutinas: nombre_subrutina(parametros) begin ... end
- Llamada: CALL nombre_subrutina(parametros)
- Valores Booleanos: T (true) y F (false)
Solo devuelve el código sin explicaciones ni Markdown.`;
    
    return this.generate(naturalLanguage, systemInstruction, 0.1);
  }
}