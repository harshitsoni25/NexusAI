// Types mirroring the Nexus AI Pro API contracts (pro/api). Where the backend
// does not yet expose a resource (datasets, logs, settings), the type is defined
// here and served by the mock client.

export type JobState = "completed" | "failed" | "running" | "pending" | "cancelled";

export interface JobSummary {
  job_id: string;
  target: string | null;
  state: JobState | string | null;
  dataset_id: string | null;
}

export interface JobDetail extends JobSummary {
  detail: Record<string, unknown>;
}

export interface JobList {
  jobs: JobSummary[];
  count: number;
}

export type SubmissionState = "accepted" | "running" | "finished" | "failed";

export interface ScrapeRequest {
  target: string;
  dataset_id?: string;
  export_formats: string[];
  report_formats: string[];
}

export interface ScrapeAccepted {
  submission_id: string;
  state: SubmissionState;
  target: string;
  dataset_id: string;
  job_id: string | null;
  status_url: string;
}

export interface SubmissionStatus {
  submission_id: string;
  state: SubmissionState;
  target: string;
  dataset_id: string;
  job_id: string | null;
  error: string | null;
}

export interface Statistics {
  total_jobs: number;
  by_state: Record<string, number>;
  [key: string]: unknown;
}

export interface Liveness {
  status: string;
  service: string;
}

export interface Readiness {
  ready: boolean;
  checks: Record<string, unknown>;
}

export interface PluginInfo {
  name: string;
  kind: string | null;
  status: string | null;
}

export interface PluginReport {
  loaded: PluginInfo[];
  failed: { detail: string }[];
  count: number;
}

// --- resources served by mocks (no backend endpoint yet) --------------------

export interface DatasetVersion {
  dataset_id: string;
  version: number;
  processed_at: string | null;
  record_count: number;
  quality_grade: string | null;
  source_count: number;
}

export interface DatasetRecord {
  identity: string;
  fields: Record<string, string>;
  source_uri: string;
}

export interface ExportManifest {
  id: string;
  dataset_id: string;
  format: string;
  location: string;
  record_count: number;
  created_at: string;
}

export interface ReportManifest {
  id: string;
  dataset_id: string;
  format: string;
  location: string;
  created_at: string;
}

export interface LogEntry {
  timestamp: string;
  level: "INFO" | "WARNING" | "ERROR" | "DEBUG";
  logger: string;
  message: string;
  request_id: string;
}

export interface Settings {
  apiBase: string;
  useMocks: boolean;
  maxConcurrentScrapes: number;
  defaultExportFormats: string[];
  defaultReportFormats: string[];
  logJson: boolean;
}

export interface ApiError {
  code: string;
  message: string;
  request_id: string;
  category?: string;
}
