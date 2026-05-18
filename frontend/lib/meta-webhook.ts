import { NextRequest, NextResponse } from "next/server";

export async function verifyMetaWebhook(req: NextRequest) {
  const verifyToken = process.env.META_VERIFY_TOKEN;
  const searchParams = req.nextUrl.searchParams;

  const mode = searchParams.get("hub.mode");
  const token = searchParams.get("hub.verify_token");
  const challenge = searchParams.get("hub.challenge");

  if (mode === "subscribe" && token === verifyToken && challenge) {
    return new NextResponse(challenge, { status: 200 });
  }

  return new NextResponse("Forbidden", { status: 403 });
}

export async function receiveMetaWebhook(req: NextRequest) {
  const rawBody = await req.text();
  let body: unknown = rawBody;
  try {
    body = JSON.parse(rawBody);
  } catch {
    body = rawBody;
  }
  const backendWebhookUrl =
    process.env.BACKEND_WEBHOOK_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/api\/v1\/?$/, "/webhooks/meta/instagram");

  console.log("Webhook Event:", typeof body === "string" ? body : JSON.stringify(body));

  if (backendWebhookUrl) {
    try {
      const signature = req.headers.get("x-hub-signature-256");
      const contentType = req.headers.get("content-type") ?? "application/json";
      await fetch(backendWebhookUrl, {
        method: "POST",
        headers: {
          "content-type": contentType,
          ...(signature ? { "x-hub-signature-256": signature } : {})
        },
        body: rawBody,
        cache: "no-store"
      });
    } catch (error) {
      console.error("Failed to forward webhook:", error);
    }
  }

  return NextResponse.json({ success: true, forwarded: Boolean(backendWebhookUrl) }, { status: 200 });
}
