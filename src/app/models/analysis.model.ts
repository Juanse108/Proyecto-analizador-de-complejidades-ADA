export interface ComplexityIR {
  [key: string]: any;
}

export interface AnalyzeResponse {
  big_o: string;
  big_omega: string | null;
  theta: string | null;
  strong_bounds: string | null;
  ir: ComplexityIR;
  notes: string | null;
}

export interface AnalyzeRequest {
  code: string;
  objective: 'worst' | 'best' | 'avg';
}
