import { TestBed } from '@angular/core/testing';

import { AnalyzerService } from './analyzer';

describe('Analyzer', () => {
  let service: AnalyzerService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(AnalyzerService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
 