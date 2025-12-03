import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { GeminiService, ToGrammarResponse } from './services/gemini.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class AppComponent {
  // Variables para Lenguaje Natural
  natLangInput: string = '';
  isGenerating: boolean = false;

  // Variables para Pseudocódigo
  generatedPseudocode: string = '';
  issues: string[] = [];
  errorMsg: string | null = null;

  constructor(private gemini: GeminiService) {}

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