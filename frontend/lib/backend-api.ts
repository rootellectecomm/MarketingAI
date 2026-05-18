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
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? `Cannot reach backend at ${apiBaseUrl}: ${error.message}`
            : `Cannot reach backend at ${apiBaseUrl}`,
        fix:
          "Set BACKEND_API_BASE_URL or NEXT_PUBLIC_API_BASE_URL on the frontend Vercel project to https://marketing-ai-gymu.vercel.app/api/v1, then redeploy the frontend."
      },
      { status: 502 }
    );
  }
}
