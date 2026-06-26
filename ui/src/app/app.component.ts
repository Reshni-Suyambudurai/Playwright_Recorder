import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { FlowService } from './services/flow.service';
import { Flow, RunReport, SchemaField } from './models/flow.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit {
  flows: string[] = [];
  selectedFile = '';
  selectedFlow: Flow | null = null;
  paramsForm: FormGroup = this.fb.group({});

  credKeys: string[] = [];
  paramKeys: string[] = [];

  running = false;
  report: RunReport | null = null;
  serverError: string | null = null;

  constructor(private fb: FormBuilder, private flowService: FlowService) {}

  ngOnInit(): void {
    this.flowService.getFlows().subscribe({
      next: (res) => (this.flows = res.flows),
      error: () =>
        (this.serverError =
          'Cannot reach the server. Start it with: python server.py'),
    });
  }

  onFlowSelect(event: Event): void {
    const name = (event.target as HTMLSelectElement).value;
    if (!name) { this.selectedFlow = null; return; }
    this.selectedFile = name;
    this.report = null;
    this.serverError = null;
    this.flowService.getFlow(name).subscribe((flow) => {
      this.selectedFlow = flow;
      this.buildForm(flow);
    });
  }

  buildForm(flow: Flow): void {
    const controls: Record<string, unknown[]> = {};
    this.credKeys  = Object.keys(flow.schema.credentials   ?? {});
    this.paramKeys = Object.keys(flow.schema.runParameters ?? {});

    for (const key of this.credKeys) {
      controls[`credentials.${key}`] = [null, Validators.required];
    }
    for (const key of this.paramKeys) {
      const field = flow.schema.runParameters[key];
      controls[`runParameters.${key}`] = [
        field.default ?? null,
        field.required ? Validators.required : null,
      ];
    }
    this.paramsForm = this.fb.group(controls);
  }

  field(section: 'credentials' | 'runParameters', key: string): SchemaField {
    return this.selectedFlow!.schema[section][key];
  }

  run(): void {
    if (!this.selectedFlow || this.paramsForm.invalid) return;
    this.running = true;
    this.report = null;
    this.serverError = null;

    const runtimeValues: Record<string, string> = {};
    for (const [k, v] of Object.entries(this.paramsForm.value)) {
      runtimeValues[k] = String(v ?? '');
    }

    this.flowService
      .runFlow({
        flowFile: this.selectedFile,
        runtimeValues,
        headless: false,
        browser: 'chromium',
      })
      .subscribe({
        next: (r) => { this.report = r; this.running = false; },
        error: (e) => {
          this.serverError = e?.error?.detail ?? 'Execution failed.';
          this.running = false;
        },
      });
  }

  get passRate(): number {
    if (!this.report) return 0;
    return Math.round((this.report.summary.passed / this.report.summary.total) * 100);
  }
}
