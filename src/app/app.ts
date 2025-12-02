import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { AnalyzerService } from './services/analyzer';
import { GeminiService, ToGrammarResponse } from './services/gemini.service';
import { AnalyzeResponse } from './models/analysis.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class AppComponent {
  // Variables para Lenguaje Natural
  natLangInput: string = '';
  isGenerating: boolean = false;

  // Variables para Pseudocódigo Generado
  generatedPseudocode: string = '';
  issues: string[] = [];

  // Variables para Análisis
  inputCode: string = `for i <- 1 to n do\nbegin\n  print(i)\nend`;
  result: AnalyzeResponse | null = null;
  isLoading: boolean = false;
  errorMsg: string | null = null;

  constructor(
    private analyzerService: AnalyzerService,
    private gemini: GeminiService
  ) {}

  /**
   * Generar Pseudocódigo desde Lenguaje Natural usando Gemini
   */
  async onGeneratePseudocode() {
    if (!this.natLangInput.trim()) {
      this.errorMsg = 'Por favor ingresa una descripción del algoritmo';
      return;
    }

    this.isGenerating = true;
    this.errorMsg = null;
    this.generatedPseudocode = '';
    this.issues = [];

    try {
      const response: ToGrammarResponse = await this.gemini.toGrammar(this.natLangInput);

      this.generatedPseudocode = response.pseudocode_normalizado;
      this.inputCode = response.pseudocode_normalizado; // Copiar al área de análisis
      this.issues = response.issues || [];

      // Limpiar entrada después de generar
      this.natLangInput = '';

    } catch (err: any) {
      this.errorMsg = 'Error generando pseudocódigo: ' + err.message;
      console.error(err);
    } finally {
      this.isGenerating = false;
    }
  }

  /**
   * Analizar la complejidad del pseudocódigo
   */
  onAnalyze() {
    this.isLoading = true;
    this.errorMsg = null;
    this.result = null;

    this.analyzerService.analyzeCode(this.inputCode).subscribe({
      next: (response) => {
        this.result = response;
        this.isLoading = false;
      },
      error: (err) => {
        console.error(err);
        this.errorMsg = 'Error al conectar con el analizador. Revisa que el backend esté corriendo.';
        this.isLoading = false;
      }
    });
  }

  /**
   * Limpiar el pseudocódigo generado
   */
  clearGenerated() {
    this.generatedPseudocode = '';
    this.issues = [];
    this.errorMsg = null;
  }

  /**
   * Copiar el pseudocódigo al portapapeles
   */
  copyToClipboard() {
    if (this.generatedPseudocode) {
      navigator.clipboard.writeText(this.generatedPseudocode);
    }
  }
}