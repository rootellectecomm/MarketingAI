import { proxyBackendPost } from "@/lib/backend-api";

const RESET_ADMIN_SECRET = process.env.RESET_ADMIN_SECRET ?? "rootellect-reset-secret";

export async function POST() {
  return proxyBackendPost("/auth/reset-admin", {
    headers: {
      "X-Reset-Admin-Secret": RESET_ADMIN_SECRET
    }
  });
}
