import type { NexusAIApi } from "./client";
import type {
  DatasetRecord,
  DatasetVersion,
  ExportManifest,
  JobDetail,
  JobList,
  JobSummary,
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

const delay = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const nowIso = () => new Date().toISOString();
const uid = () => Math.random().toString(16).slice(2, 14);

function seedJobs(): JobSummary[] {
  const targets = [
    "https://example.com/products",
    "https://news.example.org",
    "https://shop.example.net/catalog",
    "https://blog.example.com",
    "https://data.example.io/listings",
  ];
  const states = ["completed", "completed", "failed", "running", "completed"] as const;
  return targets.map((target, i) => ({
    job_id: `job-${1000 + i}`,
    target,
    state: states[i],
    dataset_id: `ds-${uid().slice(0, 8)}`,
  }));
}

// A small mutable in-memory store so the UI behaves like a real app in mock mode.
const store = {
  jobs: seedJobs(),
  submissions: new Map<string, SubmissionStatus>(),
  exports: [
    { id: uid(), dataset_id: "ds-a1b2c3", format: "csv", location: "/data/reports/export.csv", record_count: 128, created_at: nowIso() },
    { id: uid(), dataset_id: "ds-a1b2c3", format: "ndjson", location: "/data/reports/export.ndjson", record_count: 128, created_at: nowIso() },
  ] as ExportManifest[],
  reports: [
    { id: uid(), dataset_id: "ds-a1b2c3", format: "html", location: "/data/reports/report.html", created_at: nowIso() },
  ] as ReportManifest[],
};

const datasets: DatasetVersion[] = [
  { dataset_id: "ds-a1b2c3", version: 3, processed_at: nowIso(), record_count: 128, quality_grade: "A", source_count: 12 },
  { dataset_id: "ds-d4e5f6", version: 1, processed_at: nowIso(), record_count: 42, quality_grade: "B", source_count: 4 },
  { dataset_id: "ds-99aa88", version: 7, processed_at: nowIso(), record_count: 1043, quality_grade: "A", source_count: 88 },
];

function seedRecords(datasetId: string): DatasetRecord[] {
  return Array.from({ length: 12 }, (_, i) => ({
    identity: `${datasetId}-r${i}`,
    fields: { title: `Item ${i + 1}`, price: `$${(9.99 + i).toFixed(2)}`, sku: `SKU-${i + 100}` },
    source_uri: `https://example.com/item/${i + 1}`,
  }));
}

const logs: LogEntry[] = Array.from({ length: 30 }, (_, i) => {
  const levels: LogEntry["level"][] = ["INFO", "INFO", "INFO", "WARNING", "ERROR"];
  return {
    timestamp: new Date(Date.now() - i * 60000).toISOString(),
    level: levels[i % levels.length],
    logger: ["job_runner", "engine_gateway", "main"][i % 3],
    message: [
      "scrape started target=https://example.com",
      "scrape finished job=job-1004",
      "startup complete",
      "retry after transient network error",
      "export failed: no exporter registered",
    ][i % 5],
    request_id: uid().slice(0, 12),
  };
});

export const mockApi: NexusAIApi = {
  async liveness(): Promise<Liveness> {
    await delay(80);
    return { status: "ok", service: "nexusai-pro-api" };
  },
  async readiness(): Promise<Readiness> {
    await delay(120);
    return {
      ready: true,
      checks: {
        ok: true,
        checks: [
          { name: "python", status: "pass" },
          { name: "sqlalchemy", status: "pass" },
          { name: "playwright", status: "warn", remediation: "pip install nexusai[browser]" },
          { name: "adapters", status: "pass" },
        ],
      },
    };
  },
  async startScrape(body: ScrapeRequest): Promise<ScrapeAccepted> {
    await delay();
    const submission_id = uid();
    const dataset_id = body.dataset_id ?? `ds-${uid().slice(0, 8)}`;
    const record: SubmissionStatus = {
      submission_id,
      state: "running",
      target: body.target,
      dataset_id,
      job_id: null,
      error: null,
    };
    store.submissions.set(submission_id, record);
    // simulate completion after a short delay
    setTimeout(() => {
      const job_id = `job-${2000 + store.jobs.length}`;
      store.submissions.set(submission_id, { ...record, state: "finished", job_id });
      store.jobs.unshift({ job_id, target: body.target, state: "completed", dataset_id });
    }, 2500);
    return {
      submission_id,
      state: "running",
      target: body.target,
      dataset_id,
      job_id: null,
      status_url: `/api/v1/scrape/${submission_id}`,
    };
  },
  async submissionStatus(id: string): Promise<SubmissionStatus> {
    await delay(120);
    const record = store.submissions.get(id);
    if (!record) throw new Error(`submission '${id}' not found`);
    return record;
  },
  async listJobs(limit = 50): Promise<JobList> {
    await delay();
    const jobs = store.jobs.slice(0, limit);
    return { jobs, count: jobs.length };
  },
  async getJob(jobId: string): Promise<JobDetail> {
    await delay();
    const job = store.jobs.find((j) => j.job_id === jobId);
    if (!job) throw new Error(`job '${jobId}' not found`);
    return {
      ...job,
      detail: {
        stages: ["retrieve", "extract", "process", "validate", "persist", "export", "report"],
        records: 128,
        duration_seconds: 4.2,
        quality_grade: "A",
      },
    };
  },
  async statistics(): Promise<Statistics> {
    await delay();
    const by_state: Record<string, number> = {};
    for (const j of store.jobs) {
      const s = String(j.state ?? "unknown");
      by_state[s] = (by_state[s] ?? 0) + 1;
    }
    return { total_jobs: store.jobs.length, by_state };
  },
  async plugins(): Promise<PluginReport> {
    await delay();
    return {
      loaded: [
        { name: "generic-html", kind: "adapter", status: "loaded" },
        { name: "sitemap-discovery", kind: "discovery", status: "loaded" },
      ],
      failed: [{ detail: "legacy-xml-adapter: incompatible contract version" }],
      count: 2,
    };
  },
  async listDatasets(): Promise<DatasetVersion[]> {
    await delay();
    return datasets;
  },
  async datasetRecords(datasetId: string): Promise<DatasetRecord[]> {
    await delay();
    return seedRecords(datasetId);
  },
  async listExports(): Promise<ExportManifest[]> {
    await delay();
    return store.exports;
  },
  async createExport(datasetId: string, format: string): Promise<ExportManifest> {
    await delay(400);
    const manifest: ExportManifest = {
      id: uid(),
      dataset_id: datasetId,
      format,
      location: `/data/reports/export.${format}`,
      record_count: 128,
      created_at: nowIso(),
    };
    store.exports = [manifest, ...store.exports];
    return manifest;
  },
  async listReports(): Promise<ReportManifest[]> {
    await delay();
    return store.reports;
  },
  async createReport(datasetId: string, format: string): Promise<ReportManifest> {
    await delay(400);
    const manifest: ReportManifest = {
      id: uid(),
      dataset_id: datasetId,
      format,
      location: `/data/reports/report.${format}`,
      created_at: nowIso(),
    };
    store.reports = [manifest, ...store.reports];
    return manifest;
  },
  async logs(): Promise<LogEntry[]> {
    await delay();
    return logs;
  },
};
