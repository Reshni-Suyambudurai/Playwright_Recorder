// Flow JSON models — mirrors the Python schema

export interface SchemaField {
  type: string;
  required: boolean;
  default: string | null;
  label: string;
  secret?: boolean;
}

export interface FlowSchema {
  credentials: Record<string, SchemaField>;
  runParameters: Record<string, SchemaField>;
}

export interface FlowStep {
  step: number;
  action: string;
  by: string;
  selector: string | Record<string, string> | null;
  value: string | null;
  rawValue: string | null;
  paramKey: string | null;
  isSensitive: boolean;
  meta: { raw: string };
}

export interface Flow {
  flowName: string;
  source: { type: string };
  steps: FlowStep[];
  schema: FlowSchema;
}

export interface ActionResult {
  index: number;
  action: string;
  status: 'passed' | 'failed' | 'skipped';
  duration_ms: number;
  error?: string;
  screenshot?: string;
}

export interface RunReport {
  summary: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
    duration: string;
  };
  results: ActionResult[];
}
