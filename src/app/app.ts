import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms'; // Necesario para [(ngModel)]
import { AnalyzerService } from './services/analyzer';
import { AnalyzeResponse } from './models/analysis.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class AppComponent {
  inputCode: string = `for i <- 1 to n do\n  print(i)\nend`; // Ejemplo inicial
  result: AnalyzeResponse | null = null;
  isLoading: boolean = false;
  errorMsg: string | null = null;

  constructor(private analyzerService: AnalyzerService) {}

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
}