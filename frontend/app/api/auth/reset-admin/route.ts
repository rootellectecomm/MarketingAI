import { NextResponse } from "next/server";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
const RESET_ADMIN_SECRET = process.env.RESET_ADMIN_SECRET ?? "rootellect-reset-secret";

export async function POST() {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/reset-admin`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Reset-Admin-Secret": RESET_ADMIN_SECRET
      },
      cache: "no-store"
    });

    const body = await response.text();
    if (!response.ok) {
      return NextResponse.json(
        { error: body || `Reset failed with status ${response.status}` },
        { status: response.status }
      );
    }

    return new NextResponse(body, {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  } catch (error) {
    return NextResponse.json(
      {
        error:
          error instanceof Error
            ? `Cannot reach backend at ${API_BASE_URL}: ${error.message}`
            : "Cannot reach backend"
      },
      { status: 502 }
    );
  }
}
