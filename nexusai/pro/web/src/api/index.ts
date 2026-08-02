import { HttpApi, type NexusAIApi } from "./client";
import { mockApi } from "./mocks";

// The whole app imports `api` from here. A single env flag switches between the
// live FastAPI backend and the in-memory mocks, so every screen works with or
// without a running backend.
const useMocks = (import.meta.env.VITE_USE_MOCKS ?? "true") === "true";

export const api: NexusAIApi = useMocks ? mockApi : new HttpApi();
export const usingMocks = useMocks;
export * from "./types";
