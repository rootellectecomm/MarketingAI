import { NextResponse } from "next/server";

export function getBackendApiBaseUrl() {
  return (process.env.BACKEND_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(
    /\/$/,
    ""
  );
}

export async function proxyBackendPost(
  path: string,
  options: {
    body?: unknown;
    headers?: Record<string, string>;
  } = {}
) {
  const apiBaseUrl = getBackendApiBaseUrl();

  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...options.headers
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store"
    });
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("content-type") ?? "application/json"
      }
    });
  } catch (error) {
    const isLocalhost = apiBaseUrl.includes("localhost") || apiBaseUrl.includes("127.0.0.1");
    const fix = isLocalhost
      ? "Start the backend: from repo root run `docker compose up -d postgres redis api` OR `cd backend && uvicorn app.main:app --reload`. Or point frontend/.env.local to https://marketing-ai-gymu.vercel.app/api/v1 and restart `npm run dev`."
      : "Check BACKEND_API_BASE_URL in frontend/.env.local and confirm the deployed API responds at /health.";

    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? `Cannot reach backend at ${apiBaseUrl}: ${error.message}`
            : `Cannot reach backend at ${apiBaseUrl}`,
        fix
      },
      { status: 502 }
    );
  }
}
