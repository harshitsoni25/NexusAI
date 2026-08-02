// Types for the reporting/analytics surface. KPIs, success rate and the statistics
// table are derivable from the existing backend (/statistics, /jobs). Time-series
// (trends, execution time, storage) and the report document / export preview are
// served by the mock provider where the backend exposes no endpoint — no backend
// changes are made to support this module.

export interface Kpi {
  id: string;
  label: string;
  value: number | string;
  unit?: string;
  delta?: number; // percent change vs previous period; positive = up
  hint?: string;
}

export interface SuccessRate {
  total: number;
  completed: number;
  failed: number;
  running: number;
  other: number;
  rate: number; // 0..1 completed / total
}

export interface TrendPoint {
  date: string; // ISO date (day)
  completed: number;
  failed: number;
  running: number;
}

export interface ExecutionBucket {
  bucket: string; // e.g. "0-1s", "1-2s"
  count: number;
}

export interface ExecutionTime {
  p50: number;
  p90: number;
  p99: number;
  averageSeconds: number;
  histogram: ExecutionBucket[];
}

export interface StoragePoint {
  date: string;
  datasetsMb: number;
  exportsMb: number;
  reportsMb: number;
}

export interface StorageUsage {
  totalMb: number;
  points: StoragePoint[];
  byDataset: { dataset_id: string; mb: number; records: number }[];
}

export interface StatisticRow {
  metric: string;
  value: string | number;
}

export interface ReportDocument {
  id: string;
  title: string;
  generatedAt: string;
  html: string; // self-contained HTML rendered in a sandboxed iframe
}

export type ExportFormat = "csv" | "json" | "ndjson";

export interface ExportPreview {
  dataset_id: string;
  format: ExportFormat;
  columns: string[];
  rows: Record<string, string>[];
  raw: string; // the first bytes as they would appear in the file
  truncated: boolean;
}

export interface ReportingBundle {
  kpis: Kpi[];
  successRate: SuccessRate;
  trends: TrendPoint[];
  executionTime: ExecutionTime;
  storage: StorageUsage;
  statistics: StatisticRow[];
}
