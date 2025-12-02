import { Injectable } from '@angular/core';

export interface ToGrammarResponse {
  pseudocode_normalizado: string;
  issues: string[];
}

// --- 1. REGLAS DEL SISTEMA (Portadas de tu código Python) ---
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
- NO escribas texto en lenguaje natural fuera de comentarios con '►'.

FORMATO VÁLIDO:
- Asignación: variable <- expresión
- Ciclo FOR: for i <- 1 to n do
- Ciclo WHILE: while (condición) do
- IF: if (condición) then ... else ...
`;

const EXAMPLE_PAIR = `
Ejemplo:
Entrada: "Sumar los n primeros números"
Salida JSON:
{"pseudocode_normalizado":"begin\\n  s <- 0\\n  for i <- 1 to n do\\n  begin\\n    s <- s + i\\n  end\\nend","issues":[]}
`;

@Injectable({
  providedIn: 'root'
})
export class GeminiService {
  // ⚠️ IMPORTANTE: En un proyecto real, esto debe ir tras un proxy.
  // Para este proyecto académico, pon tu API Key aquí.
  private readonly apiKey = 'TU_API_KEY_AQUI'; 
  private readonly apiUrl = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';

  constructor() {}

  /**
   * Convierte lenguaje natural a Pseudocódigo usando las reglas estrictas.
   */
  async toGrammar(text: string): Promise<ToGrammarResponse> {
    // Validación de entrada
    if (!text || !text.trim()) {
      return {
        pseudocode_normalizado: 'begin\nend',
        issues: ['Entrada vacía']
      };
    }

    // Construcción del Prompt completo tal como lo tenías en Python
    const fullPrompt = `
      ${SYSTEM_RULES}
      ${EXAMPLE_PAIR}
      
      Entrada real:
      "${text}"
      
      Responde SOLO con el JSON:
    `;

    try {
      const response = await fetch(`${this.apiUrl}?key=${this.apiKey}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: fullPrompt }] }]
        })
      });

      if (!response.ok) {
        throw new Error(`Error HTTP ${response.status}`);
      }

      const data = await response.json();
      
      // Manejo de errores de la API de Google
      if (data.error) {
        throw new Error(data.error.message);
      }

      const rawText = data.candidates?.[0]?.content?.parts?.[0]?.text || '';
      
      // Limpieza: A veces el LLM pone ```json al principio
      const jsonStr = rawText.replace(/```json/g, '').replace(/```/g, '').trim();
      
      const parsed = JSON.parse(jsonStr);
      return {
        pseudocode_normalizado: parsed.pseudocode_normalizado || '',
        issues: Array.isArray(parsed.issues) ? parsed.issues : []
      };

    } catch (error) {
      console.error('Error en Gemini Service:', error);
      // Fallback elegante para que la UI no explote
      return {
        pseudocode_normalizado: `begin\n  ► Error: ${text}\nend`,
        issues: ['Error de conexión con LLM']
      };
    }
  }
}