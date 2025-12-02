import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { AnalyzerService } from './services/analyzer';
import { LlmService } from './services/llm.service';
import { AnalyzeResponse } from './models/analysis.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class AppComponent {
  inputCode: string = `for i <- 1 to n do\n  print(i)\nend`; // Ejemplo inicial
  naturalLanguageInput: string = '';
  result: AnalyzeResponse | null = null;
  isLoading: boolean = false;
  isNormalizingLoading: boolean = false;
  errorMsg: string | null = null;

  constructor(
    private analyzerService: AnalyzerService,
    private llmService: LlmService
  ) {}

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

  onNormalize() {
    if (!this.naturalLanguageInput.trim()) {
      this.errorMsg = 'Por favor, ingresa una descripción en lenguaje natural.';
      return;
    }

    this.isNormalizingLoading = true;
    this.errorMsg = null;

    this.llmService.normalizeCode(this.naturalLanguageInput).subscribe({
      next: (response) => {
        this.inputCode = response.text;
        this.isNormalizingLoading = false;
        this.naturalLanguageInput = '';
      },
      error: (err) => {
        console.error(err);
        this.errorMsg = 'Error al convertir a pseudocódigo. Revisa que el servicio LLM esté corriendo.';
        this.isNormalizingLoading = false;
      }
    });
  }
}