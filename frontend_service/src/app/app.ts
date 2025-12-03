import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { OrchestratorService, AnalyzeResponse } from './services/orchestrator.service';
import { GeminiService, ToGrammarResponse, ComparisonResponse } from './services/gemini.service';
import { ComplexityVisualizerComponent } from './components/complexity-visualizer.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule, 
    FormsModule, 
    HttpClientModule, 
    ComplexityVisualizerComponent
  ],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class AppComponent implements OnInit {
  // Variables para Lenguaje Natural
  natLangInput: string = '';
  isGenerating: boolean = false;

  // Variables para Pseudocódigo Generado
  generatedPseudocode: string = '';
  issues: string[] = [];

  // Variables para Análisis
  inputCode: string = '';
  selectedObjective: 'worst' | 'best' | 'average' = 'worst';
  result: AnalyzeResponse | null = null;
  isLoading: boolean = false;
  errorMsg: string | null = null;

  // Variables para Comparación LLM
  isComparingLLM: boolean = false;
  llmComparison: ComparisonResponse | null = null;
  comparisonError: string | null = null;

  // Estado del servicio
  isServiceReady: boolean = false;

  constructor(
    private orchestratorService: OrchestratorService,
    private geminiService: GeminiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Verificar que el orchestrator esté disponible
    this.orchestratorService.healthCheck().subscribe({
      next: (response) => {
        this.isServiceReady = true;
        console.log('✅ Orchestrator Service disponible:', response);
      },
      error: (error) => {
        this.isServiceReady = false;
        console.error('❌ Error al conectar con Orchestrator:', error);
        this.errorMsg = '⚠️ El servicio de backend no está disponible. Asegúrate de que el orchestrator esté corriendo en puerto 8000.';
        this.cdr.detectChanges();
      }
    });
  }

  /**
   * Generar Pseudocódigo desde Lenguaje Natural usando Gemini
   */
  async onGeneratePseudocode(): Promise<void> {
    if (!this.natLangInput.trim()) {
      this.errorMsg = '❌ Por favor ingresa una descripción del algoritmo';
      this.cdr.detectChanges();
      return;
    }

    this.isGenerating = true;
    this.errorMsg = null;
    this.generatedPseudocode = '';
    this.issues = [];
    this.cdr.detectChanges();

    try {
      console.log('📝 Generando pseudocódigo desde Gemini 2.0:', this.natLangInput);
      
      const response: ToGrammarResponse = await this.geminiService.toGrammar(this.natLangInput);

      console.log('📦 Respuesta completa:', response);
      console.log('📄 Pseudocódigo:', response.pseudocode_normalizado);
      console.log('⚠️ Issues:', response.issues);

      if (!response || !response.pseudocode_normalizado) {
        throw new Error('Respuesta vacía del servicio Gemini');
      }

      // Asignar valores explícitamente
      this.generatedPseudocode = response.pseudocode_normalizado;
      this.inputCode = response.pseudocode_normalizado;
      this.issues = response.issues || [];

      console.log('✅ Pseudocódigo asignado a variable:', this.generatedPseudocode.substring(0, 50));
      console.log('✅ Pseudocódigo generado exitosamente');

      this.natLangInput = '';
      this.cdr.detectChanges();

    } catch (err: any) {
      console.error('❌ Error en Gemini:', err);
      this.errorMsg = `❌ Error generando pseudocódigo: ${err.message || 'Error desconocido'}`;
      this.generatedPseudocode = '';
      this.issues = [];
      this.cdr.detectChanges();
    } finally {
      this.isGenerating = false;
      this.cdr.detectChanges();
    }
  }

  /**
   * Analizar la complejidad del pseudocódigo
   */
  onAnalyze(): void {
    if (!this.inputCode.trim()) {
      this.errorMsg = '❌ Por favor ingresa un código para analizar';
      this.cdr.detectChanges();
      return;
    }

    if (!this.isServiceReady) {
      this.errorMsg = '❌ El servicio de backend no está disponible';
      this.cdr.detectChanges();
      return;
    }

    this.isLoading = true;
    this.errorMsg = null;
    this.result = null;
    this.llmComparison = null;
    this.cdr.detectChanges();

    console.log(`🔍 Analizando código con objetivo: ${this.selectedObjective}`);

    this.orchestratorService.analyze(this.inputCode, this.selectedObjective).subscribe({
      next: (response: AnalyzeResponse) => {
        this.result = response;
        console.log('✅ Análisis completado:', response);
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (error: Error) => {
        console.error('❌ Error en análisis:', error);
        this.errorMsg = `❌ Error al analizar: ${error.message}`;
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  /**
   * Comparar resultado del Analyzer con análisis del LLM
   */
  async onCompareLLM(): Promise<void> {
    if (!this.result) {
      this.comparisonError = '❌ No hay resultado del analyzer para comparar';
      this.cdr.detectChanges();
      return;
    }

    this.isComparingLLM = true;
    this.comparisonError = null;
    this.llmComparison = null;
    this.cdr.detectChanges();

    try {
      console.log('🔍 Comparando con análisis LLM...');
      
      const comparison = await this.geminiService.compareAnalysis(
        this.result.normalized_code,
        {
          big_o: this.result.big_o,
          big_omega: this.result.big_omega,
          theta: this.result.theta
        }
      );

      this.llmComparison = comparison;
      console.log('✅ Comparación completada:', comparison);
      this.cdr.detectChanges();

    } catch (err: any) {
      console.error('❌ Error en comparación LLM:', err);
      this.comparisonError = `❌ Error en comparación: ${err.message || 'Error desconocido'}`;
      this.cdr.detectChanges();
    } finally {
      this.isComparingLLM = false;
      this.cdr.detectChanges();
    }
  }

  /**
   * Limpiar el pseudocódigo generado
   */
  clearGenerated(): void {
    this.generatedPseudocode = '';
    this.issues = [];
    this.inputCode = '';
    this.errorMsg = null;
    this.cdr.detectChanges();
  }

  /**
   * Limpiar todo
   */
  clearAll(): void {
    this.natLangInput = '';
    this.generatedPseudocode = '';
    this.inputCode = '';
    this.result = null;
    this.issues = [];
    this.errorMsg = null;
    this.llmComparison = null;
    this.comparisonError = null;
    this.cdr.detectChanges();
  }

  /**
   * Copiar el pseudocódigo al portapapeles
   */
  async copyToClipboard(): Promise<void> {
    if (!this.generatedPseudocode.trim()) {
      this.errorMsg = '❌ No hay pseudocódigo para copiar';
      this.cdr.detectChanges();
      return;
    }

    try {
      await navigator.clipboard.writeText(this.generatedPseudocode);
      console.log('✅ Pseudocódigo copiado al portapapeles');
      
      // Mostrar confirmación temporal
      const originalError = this.errorMsg;
      this.errorMsg = '✅ Código copiado al portapapeles';
      this.cdr.detectChanges();
      
      setTimeout(() => {
        this.errorMsg = originalError;
        this.cdr.detectChanges();
      }, 2000);
    } catch (err) {
      console.error('❌ Error al copiar:', err);
      this.errorMsg = '❌ No se pudo copiar al portapapeles';
      this.cdr.detectChanges();
    }
  }

  /**
   * Cargar un ejemplo predefinido
   */
  loadExample(): void {
    const exampleCode = `algorithm BubbleSort(array A, integer n)
begin
  for i <- 1 to n-1 do
  begin
    for j <- 1 to n-i do
    begin
      if A[j] > A[j+1] then
      begin
        temp <- A[j]
        A[j] <- A[j+1]
        A[j+1] <- temp
      end
    end
  end
end`;
    
    this.inputCode = exampleCode;
    this.cdr.detectChanges();
    console.log('📋 Ejemplo cargado');
  }

  /**
   * Obtener color basado en el porcentaje de acuerdo
   */
  getAgreementColor(agreement: number): string {
    if (agreement >= 90) return '#28a745'; // Verde
    if (agreement >= 70) return '#ffc107'; // Amarillo
    return '#dc3545'; // Rojo
  }

  /**
   * Obtener emoji basado en match
   */
  getMatchEmoji(match: boolean): string {
    return match ? '✅' : '❌';
  }
}