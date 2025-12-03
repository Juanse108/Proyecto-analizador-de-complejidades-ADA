export interface ComplexityIR {
  [key: string]: any;
}

export interface AnalyzeResponse {
  normalized_code: string;
  big_o: string;
  big_omega: string;
  theta: string;
  ir?: string | ComplexityIR;
  notes?: string[];
}

export interface AnalyzeRequest {
  code: string;
  objective: 'worst' | 'best' | 'average';
}
