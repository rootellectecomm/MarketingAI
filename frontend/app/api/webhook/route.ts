import { NextRequest } from "next/server";
import { receiveMetaWebhook, verifyMetaWebhook } from "@/lib/meta-webhook";

export async function GET(req: NextRequest) {
  return verifyMetaWebhook(req);
}

export async function POST(req: NextRequest) {
  return receiveMetaWebhook(req);
}

