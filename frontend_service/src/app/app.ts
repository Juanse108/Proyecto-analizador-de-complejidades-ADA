import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { OrchestratorService, AnalyzeResponse } from './services/orchestrator.service';
import { GeminiService, ToGrammarResponse, ComparisonResponse } from './services/gemini.service';
import { ComplexityVisualizerComponent } from './components/complexity-visualizer.component';

interface AlgorithmExample {
  name: string;
  type: 'iterativo' | 'recursivo';
  complexity: string;
  code: string;
}

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

  // 🆕 Menú de ejemplos
  showExamplesMenu: boolean = false;
  
  examples: AlgorithmExample[] = [
    {
      name: 'Bubble Sort',
      type: 'iterativo',
      complexity: 'O(n²)',
      code: `BubbleSort(A, n)
begin
  for i <- 1 to n - 1 do
  begin
    for j <- 1 to n - i do
    begin
      if (A[j] > A[j + 1]) then
      begin
        temp <- A[j]
        A[j] <- A[j + 1]
        A[j + 1] <- temp
      end
      else
      begin
        temp <- temp
      end
    end
  end
end`
    },
    {
      name: 'Binary Search',
      type: 'iterativo',
      complexity: 'O(log n)',
      code: `BinarySearch(A, n, x)
begin
  left <- 1
  right <- n
  while (left <= right) do
  begin
    mid <- (left + right) / 2
    if (A[mid] = x) then
    begin
      return mid
    end
    else
    begin
      if (A[mid] < x) then
      begin
        left <- mid + 1
      end
      else
      begin
        right <- mid - 1
      end
    end
  end
  return -1
end`
    },
    {
      name: 'Selection Sort',
      type: 'iterativo',
      complexity: 'O(n²)',
      code: `SelectionSort(A, n)
begin
  for i <- 1 to n - 1 do
  begin
    minIndex <- i
    for j <- i + 1 to n do
    begin
      if (A[j] < A[minIndex]) then
      begin
        minIndex <- j
      end
      else
      begin
        minIndex <- minIndex
      end
    end
    if (minIndex != i) then
    begin
      temp <- A[i]
      A[i] <- A[minIndex]
      A[minIndex] <- temp
    end
    else
    begin
      temp <- temp
    end
  end
end`
    },
    {
      name: 'Linear Search',
      type: 'iterativo',
      complexity: 'O(n)',
      code: `LinearSearch(A, n, x)
begin
  i <- 1
  found <- F
  while (i <= n and found = F) do
  begin
    if (A[i] = x) then
    begin
      found <- T
    end
    else
    begin
      i <- i + 1
    end
  end
end`
    },
    {
      name: 'Matrix Multiplication',
      type: 'iterativo',
      complexity: 'O(n³)',
      code: `MatrixMultiply(A, B, C, n)
begin
  for i <- 1 to n do
  begin
    for j <- 1 to n do
    begin
      C[i][j] <- 0
      for k <- 1 to n do
      begin
        C[i][j] <- C[i][j] + A[i][k] * B[k][j]
      end
    end
  end
end`
    },
    {
      name: 'Merge Sort (Recursivo)',
      type: 'recursivo',
      complexity: 'O(n log n)',
      code: `MergeSort(A, inicio, fin)
begin
  if (inicio < fin) then
  begin
    medio <- (inicio + fin) / 2
    CALL MergeSort(A, inicio, medio)
    CALL MergeSort(A, medio + 1, fin)
    CALL Merge(A, inicio, medio, fin)
  end
  else
  begin
    medio <- medio
  end
end`
    },
    {
      name: 'QuickSort (Recursivo)',
      type: 'recursivo',
      complexity: 'O(n log n)',
      code: `QuickSort(A, inicio, fin)
begin
  if (inicio < fin) then
  begin
    pivote <- Partition(A, inicio, fin)
    CALL QuickSort(A, inicio, pivote - 1)
    CALL QuickSort(A, pivote + 1, fin)
  end
  else
  begin
    pivote <- pivote
  end
end`
    },
    {
      name: 'Fibonacci (Recursivo)',
      type: 'recursivo',
      complexity: 'O(2^n)',
      code: `Fibonacci(n)
begin
  if (n <= 1) then
  begin
    return n
  end
  else
  begin
    return Fibonacci(n - 1) + Fibonacci(n - 2)
  end
end`
    },
    {
      name: 'Binary Search (Recursivo)',
      type: 'recursivo',
      complexity: 'O(log n)',
      code: `BinarySearchRec(A, x, inicio, fin)
begin
  if (inicio > fin) then
  begin
    return -1
  end
  else
  begin
    medio <- (inicio + fin) / 2
    if (A[medio] = x) then
    begin
      return medio
    end
    else
    begin
      if (A[medio] < x) then
      begin
        return BinarySearchRec(A, x, medio + 1, fin)
      end
      else
      begin
        return BinarySearchRec(A, x, inicio, medio - 1)
      end
    end
  end
end`
    },
    {
      name: 'Factorial (Recursivo)',
      type: 'recursivo',
      complexity: 'O(n)',
      code: `Factorial(n)
begin
  if (n <= 1) then
  begin
    return 1
  end
  else
  begin
    return n * Factorial(n - 1)
  end
end`
    }
  ];

  constructor(
    private orchestratorService: OrchestratorService,
    private geminiService: GeminiService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.orchestratorService.healthCheck().subscribe({
      next: (response) => {
        this.isServiceReady = true;
        console.log('✅ Orchestrator Service disponible:', response);
      },
      error: (error) => {
        this.isServiceReady = false;
        console.error('❌ Error al conectar con Orchestrator:', error);
        this.errorMsg = '⚠️ El servicio de backend no está disponible.';
        this.cdr.detectChanges();
      }
    });
  }

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
      const response: ToGrammarResponse = await this.geminiService.toGrammar(this.natLangInput);

      this.generatedPseudocode = response.pseudocode_normalizado;
      this.inputCode = response.pseudocode_normalizado;
      this.issues = response.issues || [];

      this.natLangInput = '';
      this.cdr.detectChanges();

    } catch (err: any) {
      this.errorMsg = `❌ Error generando pseudocódigo: ${err.message || 'Error desconocido'}`;
      this.cdr.detectChanges();
    } finally {
      this.isGenerating = false;
      this.cdr.detectChanges();
    }
  }

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
      const comparison = await this.geminiService.compareAnalysis(
        this.result.normalized_code,
        {
          big_o: this.result.big_o,
          big_omega: this.result.big_omega,
          theta: this.result.theta ?? undefined
        }
      );

      this.llmComparison = comparison;
      this.cdr.detectChanges();

    } catch (err: any) {
      this.comparisonError = `❌ Error en comparación: ${err.message || 'Error desconocido'}`;
      this.cdr.detectChanges();
    } finally {
      this.isComparingLLM = false;
      this.cdr.detectChanges();
    }
  }

  clearGenerated(): void {
    this.generatedPseudocode = '';
    this.issues = [];
    this.inputCode = '';
    this.errorMsg = null;
    this.cdr.detectChanges();
  }

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

  async copyToClipboard(): Promise<void> {
    if (!this.generatedPseudocode.trim()) {
      return;
    }

    try {
      await navigator.clipboard.writeText(this.generatedPseudocode);
      
      const originalError = this.errorMsg;
      this.errorMsg = '✅ Código copiado al portapapeles';
      this.cdr.detectChanges();
      
      setTimeout(() => {
        this.errorMsg = originalError;
        this.cdr.detectChanges();
      }, 2000);
    } catch (err) {
      this.errorMsg = '❌ No se pudo copiar al portapapeles';
      this.cdr.detectChanges();
    }
  }

  // 🆕 Métodos para el menú de ejemplos
  toggleExamplesMenu(): void {
    this.showExamplesMenu = !this.showExamplesMenu;
    this.cdr.detectChanges();
  }

  loadExample(example: AlgorithmExample): void {
    this.inputCode = example.code;
    this.showExamplesMenu = false;
    this.errorMsg = null;
    this.result = null;
    this.llmComparison = null;
    this.cdr.detectChanges();
    console.log(`📋 Ejemplo cargado: ${example.name} (${example.type}, ${example.complexity})`);
  }

  getAgreementColor(agreement: number): string {
    if (agreement >= 90) return '#28a745';
    if (agreement >= 70) return '#ffc107';
    return '#dc3545';
  }

  getMatchEmoji(match: boolean): string {
    return match ? '✅' : '❌';
  }
}