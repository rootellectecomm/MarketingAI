import { NextRequest } from "next/server";
import { receiveMetaWebhook, verifyMetaWebhook } from "@/lib/meta-webhook";

const backendWebhookUrl =
  process.env.BACKEND_WEBHOOK_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/api\/v1\/?$/, "/webhooks/meta/instagram");

export async function GET(req: NextRequest) {
  return verifyMetaWebhook(req);
}

export async function POST(req: NextRequest) {
  return receiveMetaWebhook(req, backendWebhookUrl);
}
