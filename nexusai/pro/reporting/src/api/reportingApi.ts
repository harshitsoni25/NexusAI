import type {
  ExportFormat,
  ExportPreview,
  ReportDocument,
  ReportingBundle,
  StatisticRow,
  SuccessRate,
} from "./types";

// The reporting surface every section depends on. A mock implementation gives a rich,
// self-contained analytics experience; the live implementation derives what it can from
// the existing backend (/statistics, /jobs) and reuses the mock for series/documents the
// backend does not expose. No backend endpoints are added or changed.
export interface ReportingApi {
  bundle(range: RangeKey): Promise<ReportingBundle>;
  reportDocument(id?: string): Promise<ReportDocument>;
  listReports(): Promise<{ id: string; title: string; generatedAt: string }[]>;
  exportPreview(datasetId: string, format: ExportFormat): Promise<ExportPreview>;
  datasets(): Promise<{ dataset_id: string; records: number }[]>;
}

export type RangeKey = "7d" | "30d" | "90d";

const BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
const delay = (ms = 220) => new Promise((r) => setTimeout(r, ms));
const iso = (d: Date) => d.toISOString().slice(0, 10);

// ---------------------------------------------------------------------------
// Mock analytics — deterministic-ish generated series so every chart renders.
// ---------------------------------------------------------------------------

function rangeDays(range: RangeKey): number {
  return range === "7d" ? 7 : range === "30d" ? 30 : 90;
}

function seededTrends(days: number) {
  const points = [];
  const today = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const base = 6 + Math.round(4 * Math.sin(i / 3));
    const completed = Math.max(0, base + (i % 5));
    const failed = Math.max(0, Math.round(base / 6) + (i % 3 === 0 ? 1 : 0));
    const running = i < 2 ? 2 : 0;
    points.push({ date: iso(d), completed, failed, running });
  }
  return points;
}

function mockBundle(range: RangeKey): ReportingBundle {
  const trends = seededTrends(rangeDays(range));
  const completed = trends.reduce((s, p) => s + p.completed, 0);
  const failed = trends.reduce((s, p) => s + p.failed, 0);
  const running = trends.reduce((s, p) => s + p.running, 0);
  const total = completed + failed + running;
  const rate = total ? completed / total : 0;

  const storagePoints = trends.map((p, i) => ({
    date: p.date,
    datasetsMb: 120 + i * 3.4,
    exportsMb: 40 + i * 1.1,
    reportsMb: 12 + i * 0.4,
  }));
  const last = storagePoints[storagePoints.length - 1];
  const totalMb = last ? last.datasetsMb + last.exportsMb + last.reportsMb : 0;

  return {
    kpis: [
      { id: "total", label: "Total jobs", value: total, hint: `last ${rangeDays(range)} days` },
      { id: "success", label: "Success rate", value: (rate * 100).toFixed(1), unit: "%", delta: 2.4 },
      { id: "avg", label: "Avg execution", value: 3.9, unit: "s", delta: -6.1 },
      { id: "storage", label: "Storage used", value: totalMb.toFixed(0), unit: "MB", delta: 4.8 },
    ],
    successRate: { total, completed, failed, running, other: 0, rate },
    trends,
    executionTime: {
      p50: 2.8,
      p90: 6.1,
      p99: 11.4,
      averageSeconds: 3.9,
      histogram: [
        { bucket: "0-1s", count: 8 },
        { bucket: "1-2s", count: 21 },
        { bucket: "2-4s", count: 34 },
        { bucket: "4-8s", count: 17 },
        { bucket: "8-16s", count: 6 },
        { bucket: "16s+", count: 2 },
      ],
    },
    storage: {
      totalMb,
      points: storagePoints,
      byDataset: [
        { dataset_id: "ds-a1b2c3", mb: 84.2, records: 1280 },
        { dataset_id: "ds-99aa88", mb: 61.7, records: 1043 },
        { dataset_id: "ds-d4e5f6", mb: 18.9, records: 420 },
      ],
    },
    statistics: [
      { metric: "Total jobs", value: total },
      { metric: "Completed", value: completed },
      { metric: "Failed", value: failed },
      { metric: "Running", value: running },
      { metric: "Success rate", value: `${(rate * 100).toFixed(1)}%` },
      { metric: "Avg execution (s)", value: 3.9 },
      { metric: "p90 execution (s)", value: 6.1 },
      { metric: "Datasets", value: 3 },
      { metric: "Storage (MB)", value: totalMb.toFixed(0) },
    ],
  };
}

const SAMPLE_RECORDS = Array.from({ length: 12 }, (_, i) => ({
  sku: `SKU-${100 + i}`,
  title: `Sample item ${i + 1}`,
  price: (9.99 + i).toFixed(2),
  in_stock: i % 3 === 0 ? "false" : "true",
}));

function buildPreview(datasetId: string, format: ExportFormat): ExportPreview {
  const columns = Object.keys(SAMPLE_RECORDS[0]);
  let raw = "";
  if (format === "csv") {
    raw = [columns.join(","), ...SAMPLE_RECORDS.map((r) => columns.map((c) => (r as Record<string, string>)[c]).join(","))].join("\n");
  } else if (format === "ndjson") {
    raw = SAMPLE_RECORDS.map((r) => JSON.stringify(r)).join("\n");
  } else {
    raw = JSON.stringify(SAMPLE_RECORDS, null, 2);
  }
  return { dataset_id: datasetId, format, columns, rows: SAMPLE_RECORDS as Record<string, string>[], raw, truncated: true };
}

function mockReportHtml(title: string, range: RangeKey): string {
  const b = mockBundle(range);
  const rows = b.statistics.map((s) => `<tr><td>${s.metric}</td><td style="text-align:right">${s.value}</td></tr>`).join("");
  return `<!doctype html><html><head><meta charset="utf-8"><style>
    body{font-family:Inter,system-ui,sans-serif;color:#0f172a;margin:24px;background:#fff}
    h1{font-size:20px;margin:0 0 4px} .sub{color:#64748b;font-size:12px;margin-bottom:20px}
    .cards{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}
    .card{border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;min-width:120px}
    .card .v{font-size:22px;font-weight:700} .card .l{font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.04em}
    table{border-collapse:collapse;width:100%;max-width:420px} td{border-bottom:1px solid #eef2f7;padding:6px 8px;font-size:13px}
    .bar{height:8px;background:#0f766e;border-radius:6px}
  </style></head><body>
    <h1>${title}</h1><div class="sub">Generated ${new Date().toLocaleString()} · window: last ${rangeDays(range)} days</div>
    <div class="cards">
      ${b.kpis.map((k) => `<div class="card"><div class="l">${k.label}</div><div class="v">${k.value}${k.unit ?? ""}</div></div>`).join("")}
    </div>
    <div style="margin-bottom:8px;font-weight:600">Success rate</div>
    <div style="background:#eef2f7;border-radius:6px;overflow:hidden;max-width:420px;margin-bottom:20px">
      <div class="bar" style="width:${(b.successRate.rate * 100).toFixed(1)}%"></div>
    </div>
    <div style="font-weight:600;margin-bottom:8px">Statistics</div>
    <table>${rows}</table>
  </body></html>`;
}

export const mockApi: ReportingApi = {
  async bundle(range) {
    await delay();
    return mockBundle(range);
  },
  async reportDocument(id) {
    await delay();
    const title = id === "weekly" ? "Weekly Scraping Report" : "Analytics Report";
    return { id: id ?? "analytics", title, generatedAt: new Date().toISOString(), html: mockReportHtml(title, "30d") };
  },
  async listReports() {
    await delay(120);
    return [
      { id: "analytics", title: "Analytics Report", generatedAt: new Date().toISOString() },
      { id: "weekly", title: "Weekly Scraping Report", generatedAt: new Date().toISOString() },
    ];
  },
  async exportPreview(datasetId, format) {
    await delay();
    return buildPreview(datasetId, format);
  },
  async datasets() {
    await delay(120);
    return [
      { dataset_id: "ds-a1b2c3", records: 1280 },
      { dataset_id: "ds-99aa88", records: 1043 },
      { dataset_id: "ds-d4e5f6", records: 420 },
    ];
  },
};

// ---------------------------------------------------------------------------
// Live API — derives KPIs / success rate / statistics from the existing backend,
// and reuses the mock for series and documents the backend does not expose.
// ---------------------------------------------------------------------------

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return (await res.json()) as T;
}

export class HttpReportingApi implements ReportingApi {
  async bundle(range: RangeKey): Promise<ReportingBundle> {
    // Reuse the mock series, but override the derivable parts with real data.
    const base = mockBundle(range);
    try {
      const stats = await get<{ data: { total_jobs?: number; by_state?: Record<string, number> } }>("/statistics");
      const byState = stats.data?.by_state ?? {};
      const completed = byState["completed"] ?? 0;
      const failed = byState["failed"] ?? 0;
      const running = byState["running"] ?? 0;
      const total = stats.data?.total_jobs ?? completed + failed + running;
      const rate = total ? completed / total : 0;
      const success: SuccessRate = { total, completed, failed, running, other: Math.max(0, total - completed - failed - running), rate };
      const statistics: StatisticRow[] = [
        { metric: "Total jobs", value: total },
        { metric: "Completed", value: completed },
        { metric: "Failed", value: failed },
        { metric: "Running", value: running },
        { metric: "Success rate", value: `${(rate * 100).toFixed(1)}%` },
        ...base.statistics.filter((r) => !["Total jobs", "Completed", "Failed", "Running", "Success rate"].includes(r.metric)),
      ];
      const kpis = base.kpis.map((k) =>
        k.id === "total" ? { ...k, value: total } : k.id === "success" ? { ...k, value: (rate * 100).toFixed(1) } : k,
      );
      return { ...base, kpis, successRate: success, statistics };
    } catch {
      return base; // backend unavailable -> full mock
    }
  }
  reportDocument(id?: string) {
    return mockApi.reportDocument(id);
  }
  listReports() {
    return mockApi.listReports();
  }
  exportPreview(datasetId: string, format: ExportFormat) {
    return mockApi.exportPreview(datasetId, format);
  }
  datasets() {
    return mockApi.datasets();
  }
}
