import type {
  DatasetRecord,
  DatasetVersion,
  ExportManifest,
  JobDetail,
  JobList,
  Liveness,
  LogEntry,
  PluginReport,
  Readiness,
  ReportManifest,
  ScrapeAccepted,
  ScrapeRequest,
  Statistics,
  SubmissionStatus,
} from "./types";

// The surface every screen depends on. Both the real backend client and the
// mock client implement it, so screens never know which is in use.
export interface NexusAIApi {
  // health
  liveness(): Promise<Liveness>;
  readiness(): Promise<Readiness>;
  // scraping
  startScrape(body: ScrapeRequest): Promise<ScrapeAccepted>;
  submissionStatus(id: string): Promise<SubmissionStatus>;
  // jobs
  listJobs(limit?: number): Promise<JobList>;
  getJob(jobId: string): Promise<JobDetail>;
  // statistics
  statistics(): Promise<Statistics>;
  // plugins
  plugins(): Promise<PluginReport>;
  // datasets (mocked)
  listDatasets(): Promise<DatasetVersion[]>;
  datasetRecords(datasetId: string): Promise<DatasetRecord[]>;
  // exports & reports (mocked history; POST proxied to backend when live)
  listExports(): Promise<ExportManifest[]>;
  createExport(datasetId: string, format: string): Promise<ExportManifest>;
  listReports(): Promise<ReportManifest[]>;
  createReport(datasetId: string, format: string): Promise<ReportManifest>;
  // logs (mocked)
  logs(): Promise<LogEntry[]>;
}

const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body?.error?.message ?? message;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(message);
  }
  return (await response.json()) as T;
}

// Real client — talks to the FastAPI backend. Resources the backend does not yet
// expose fall back to the mock client (imported lazily to avoid a cycle).
export class HttpApi implements NexusAIApi {
  liveness = () => request<Liveness>("/health");
  readiness = () => request<Readiness>("/health/ready");

  startScrape = (body: ScrapeRequest) =>
    request<ScrapeAccepted>("/scrape", { method: "POST", body: JSON.stringify(body) });
  submissionStatus = (id: string) => request<SubmissionStatus>(`/scrape/${id}`);

  listJobs = (limit = 50) => request<JobList>(`/jobs?limit=${limit}`);
  getJob = (jobId: string) => request<JobDetail>(`/jobs/${jobId}`);

  statistics = () => request<Statistics>("/statistics");
  plugins = () => request<PluginReport>("/plugins");

  async listDatasets() {
    return (await import("./mocks")).mockApi.listDatasets();
  }
  async datasetRecords(datasetId: string) {
    return (await import("./mocks")).mockApi.datasetRecords(datasetId);
  }
  async listExports() {
    return (await import("./mocks")).mockApi.listExports();
  }
  createExport = (datasetId: string, format: string) =>
    request<ExportManifest>("/exports", {
      method: "POST",
      body: JSON.stringify({ dataset_id: datasetId, format }),
    });
  async listReports() {
    return (await import("./mocks")).mockApi.listReports();
  }
  createReport = (datasetId: string, format: string) =>
    request<ReportManifest>("/reports", {
      method: "POST",
      body: JSON.stringify({ dataset_id: datasetId, format }),
    });
  async logs() {
    return (await import("./mocks")).mockApi.logs();
  }
}
