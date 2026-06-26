import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Flow, RunReport } from '../models/flow.model';

export interface RunRequest {
  flowFile: string;
  runtimeValues: Record<string, string>;
  headless: boolean;
  browser: string;
  channel?: string;
  slowMo?: number;
}

@Injectable({ providedIn: 'root' })
export class FlowService {
  private readonly base = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  getFlows(): Observable<{ flows: string[] }> {
    return this.http.get<{ flows: string[] }>(`${this.base}/flows`);
  }

  getFlow(name: string): Observable<Flow> {
    return this.http.get<Flow>(`${this.base}/flows/${name}`);
  }

  runFlow(req: RunRequest): Observable<RunReport> {
    return this.http.post<RunReport>(`${this.base}/run`, req);
  }
}
