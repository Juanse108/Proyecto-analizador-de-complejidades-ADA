import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-textarea-with-lines',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="textarea-wrapper">
      <div class="line-numbers" #lineNumbers>
        <div *ngFor="let line of lineNumbersArray" class="line-number">{{ line }}</div>
      </div>
      <textarea 
        #textarea
        class="textarea-with-lines"
        [ngModel]="value"
        (ngModelChange)="onValueChange($event)"
        (scroll)="onScroll($event)"
        [rows]="rows"
        [disabled]="disabled"
        [placeholder]="placeholder"
      ></textarea>
    </div>
  `,
  styles: [`
    .textarea-wrapper {
      display: flex;
      border: 2px solid #ddd;
      border-radius: 8px;
      background-color: #fafafa;
      font-family: 'Courier New', monospace;
      font-size: 14px;
      line-height: 1.5;
      overflow: hidden;
      transition: all 0.3s ease;
      max-height: 500px;
    }

    .textarea-wrapper:focus-within {
      border-color: #007bff;
      box-shadow: 0 0 8px rgba(0, 123, 255, 0.3);
      background-color: #fff;
    }

    .line-numbers {
      background: linear-gradient(to right, #f8f8f8, #f0f0f0);
      border-right: 2px solid #ddd;
      padding: 15px 8px 15px 10px;
      text-align: right;
      user-select: none;
      color: #888;
      font-weight: 600;
      font-size: 14px;
      min-width: 45px;
      overflow: hidden;
      line-height: 1.5;
    }

    .line-number {
      height: 21px;
      padding-right: 5px;
      transition: color 0.2s ease;
    }

    .line-number:hover {
      color: #555;
    }

    .textarea-with-lines {
      flex: 1;
      padding: 15px 10px;
      border: none;
      outline: none;
      background-color: transparent;
      resize: vertical;
      font-family: 'Courier New', monospace;
      font-size: 14px;
      line-height: 1.5;
      color: #333;
      overflow-y: auto;
      overflow-x: auto;
    }

    .textarea-with-lines:disabled {
      background-color: #e9ecef;
      cursor: not-allowed;
      opacity: 0.7;
      color: #666;
    }
  `]
})
export class TextareaWithLinesComponent implements OnInit, OnChanges {
  @Input() value: string = '';
  @Input() rows: number = 10;
  @Input() disabled: boolean = false;
  @Input() placeholder: string = '';
  
  @Output() valueChange = new EventEmitter<string>();

  lineNumbersArray: number[] = [];

  ngOnInit() {
    this.updateLineNumbers();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['value']) {
      this.updateLineNumbers();
    }
  }

  onValueChange(newValue: string) {
    this.value = newValue;
    this.updateLineNumbers();
    this.valueChange.emit(newValue);
  }

  onScroll(event: any) {
    const textarea = event.target;
    const lineNumbersDiv = textarea.parentElement?.querySelector('.line-numbers');
    if (lineNumbersDiv) {
      lineNumbersDiv.scrollTop = textarea.scrollTop;
    }
  }

  updateLineNumbers() {
    const lineCount = this.value ? (this.value.match(/\n/g) || []).length + 1 : 1;
    this.lineNumbersArray = Array.from({ length: lineCount }, (_, i) => i + 1);
  }
}
