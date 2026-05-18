import { proxyBackendPost } from "@/lib/backend-api";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  return proxyBackendPost("/auth/login", { body });
}
