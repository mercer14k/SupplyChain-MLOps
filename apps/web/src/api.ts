import { useCallback, useEffect, useState } from "react";

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch("/api/v1" + path, options);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      body?.error?.message || `Request failed (${response.status})`,
    );
  }
  return response.json();
}
export function mutation<T>(
  path: string,
  body: unknown,
  token: string,
): Promise<T> {
  return api<T>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify(body),
  });
}
export function useResource<T>(path: string, refresh: number) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const load = useCallback(
    (signal?: AbortSignal) => {
      setLoading(true);
      api<T>(path, { signal })
        .then((d) => {
          setData(d);
          setError("");
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(e.message);
        })
        .finally(() => {
          if (!signal?.aborted) setLoading(false);
        });
    },
    [path],
  );
  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load, refresh]);
  return { data, error, loading };
}
export const short = (id: string) => id.slice(0, 12);
export const dateTime = (value: string) =>
  new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
export const metric = (value: unknown, percent = false) =>
  typeof value === "number"
    ? percent
      ? `${(value * 100).toFixed(1)}%`
      : value.toFixed(3)
    : "—";
