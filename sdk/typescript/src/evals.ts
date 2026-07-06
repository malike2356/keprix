import type { KeprixClient } from "./client.js";

export type EvalCase = {
  name: string;
  input: string;
  expect_contains?: string;
  expect_equals?: string;
};

export type EvalReport = {
  suite: string;
  trace_id: string;
  passed: number;
  total: number;
  success: boolean;
  cases: Array<{
    name: string;
    passed: boolean;
    input: string;
    output: string;
  }>;
  traces: Array<{
    trace_id: string;
    app_name: string;
    event: string;
    payload: Record<string, unknown>;
    created_at: string;
  }>;
  exported_at: string;
};

export class EvalSuite {
  private readonly cases: EvalCase[] = [];

  constructor(private readonly suiteName: string) {}

  case(testCase: EvalCase): this {
    this.cases.push(testCase);
    return this;
  }

  listCases(): EvalCase[] {
    return [...this.cases];
  }

  async runRemote(client: KeprixClient): Promise<EvalReport> {
    return client.request<EvalReport>("/api/sdk/typescript/evals/run", {
      method: "POST",
      body: JSON.stringify({
        suite_name: this.suiteName,
        cases: this.cases,
      }),
    });
  }

  runLocal(runner: (input: string) => string): EvalReport {
    const traceId = crypto.randomUUID();
    const traces: EvalReport["traces"] = [];
    const results: EvalReport["cases"] = [];
    const now = new Date().toISOString();

    traces.push({
      trace_id: traceId,
      app_name: this.suiteName,
      event: "before_run",
      payload: { case_count: this.cases.length },
      created_at: now,
    });

    let passed = 0;
    for (const testCase of this.cases) {
      const output = runner(testCase.input);
      let ok = true;
      if (testCase.expect_contains) {
        ok = output.includes(testCase.expect_contains);
      } else if (testCase.expect_equals !== undefined) {
        ok = output === testCase.expect_equals;
      }
      if (ok) passed += 1;
      results.push({ name: testCase.name, passed: ok, input: testCase.input, output });
      traces.push({
        trace_id: traceId,
        app_name: this.suiteName,
        event: "after_run",
        payload: { case: testCase.name, passed: ok, output },
        created_at: new Date().toISOString(),
      });
    }

    return {
      suite: this.suiteName,
      trace_id: traceId,
      passed,
      total: results.length,
      success: passed === results.length && results.length > 0,
      cases: results,
      traces,
      exported_at: new Date().toISOString(),
    };
  }

  compare(baseline: EvalReport, candidate: EvalReport) {
    const regressions = candidate.cases.filter((row, index) => {
      const base = baseline.cases[index];
      return base && base.passed && !row.passed;
    });
    const improvements = candidate.cases.filter((row, index) => {
      const base = baseline.cases[index];
      return base && !base.passed && row.passed;
    });
    return {
      baseline_passed: baseline.passed,
      candidate_passed: candidate.passed,
      regressions,
      improvements,
      delta: candidate.passed - baseline.passed,
    };
  }

  exportReport(report: EvalReport): string {
    return JSON.stringify(report, null, 2);
  }
}

export function defineEvalSuite(name: string): EvalSuite {
  return new EvalSuite(name);
}
