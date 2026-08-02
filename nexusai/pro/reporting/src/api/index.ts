import { HttpReportingApi, mockApi, type ReportingApi } from "./reportingApi";

const useMocks = (import.meta.env.VITE_USE_MOCKS ?? "true") === "true";

export const api: ReportingApi = useMocks ? mockApi : new HttpReportingApi();
export const usingMocks = useMocks;
export * from "./types";
export type { RangeKey } from "./reportingApi";
