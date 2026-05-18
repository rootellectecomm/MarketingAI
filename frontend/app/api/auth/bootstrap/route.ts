import { proxyBackendPost } from "@/lib/backend-api";

export async function POST() {
  return proxyBackendPost("/auth/bootstrap");
}
