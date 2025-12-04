import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-textarea-with-lines',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="textarea-wrapper">
      <div class="line-numbers">
        <div *ngFor="let line of lineNumbers" class="line-number">{{ line }}</div>
      </div>
      <textarea 
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
      font-size: 1em;
      line-height: 1.5;
      overflow: hidden;
      transition: all 0.3s ease;
    }

    .textarea-wrapper:focus-within {
      border-color: #007bff;
      box-shadow: 0 0 8px rgba(0, 123, 255, 0.3);
      background-color: #fff;
    }

    .line-numbers {
      background-color: #f0f0f0;
      border-right: 2px solid #ddd;
      padding: 15px 10px;
      text-align: right;
      user-select: none;
      color: #999;
      font-weight: 600;
      font-size: 0.9em;
      min-width: 50px;
      display: flex;
      flex-direction: column;
      gap: 1px;
    }

    .line-number {
      height: 1.5em;
      display: flex;
      align-items: center;
      justify-content: flex-end;
      padding-right: 8px;
    }

    .textarea-with-lines {
      flex: 1;
      padding: 15px;
      border: none;
      outline: none;
      background-color: transparent;
      resize: vertical;
      font-family: 'Courier New', monospace;
      font-size: 1em;
      line-height: 1.5;
      color: #333;
      overflow: hidden;
      line-height: 1.5;
    }

    .textarea-with-lines:disabled {
      background-color: #e9ecef;
      cursor: not-allowed;
      opacity: 0.7;
      color: #666;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TextareaWithLinesComponent {
  @Input() value: string = '';
  @Input() rows: number = 10;
  @Input() disabled: boolean = false;
  @Input() placeholder: string = '';
  
  @Output() valueChange = new EventEmitter<string>();

  lineNumbers: number[] = [];

  ngOnInit() {
    this.updateLineNumbers();
  }

  onValueChange(newValue: string) {
    this.value = newValue;
    this.updateLineNumbers();
    this.valueChange.emit(newValue);
  }

  onScroll(event: any) {
    const lineNumbersDiv = event.target.parentElement?.querySelector('.line-numbers');
    if (lineNumbersDiv) {
      lineNumbersDiv.scrollTop = event.target.scrollTop;
    }
  }

  updateLineNumbers() {
    const lineCount = (this.value.match(/\n/g) || []).length + 1;
    this.lineNumbers = Array.from({ length: lineCount }, (_, i) => i + 1);
  }
}
