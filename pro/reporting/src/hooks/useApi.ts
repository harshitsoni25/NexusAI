import { useCallback, useEffect, useState } from "react";

export interface AsyncState<T> { data: T | null; loading: boolean; error: string | null; reload: () => void; }

export function useApi<T>(loader: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(() => {
    let active = true; setLoading(true); setError(null);
    loader().then((r) => active && setData(r)).catch((e: unknown) => active && setError(e instanceof Error ? e.message : String(e))).finally(() => active && setLoading(false));
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => run(), [run]);
  return { data, loading, error, reload: run };
}
