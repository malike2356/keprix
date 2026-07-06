/** TUI panel descriptor shared with CLI and terminal clients. */

export type TuiPanelSpec = {
  id: string;
  title: string;
  columns: string[];
  rows: string[][];
  footer?: string;
  actions?: Array<{ id: string; label: string; key?: string }>;
};

export function formatTuiPanel(spec: TuiPanelSpec): string {
  const header = spec.title;
  const body = spec.rows.map((row) => row.join(" | ")).join("\n");
  const footer = spec.footer ? `\n${spec.footer}` : "";
  return `${header}\n${spec.columns.join(" | ")}\n${body}${footer}`;
}
