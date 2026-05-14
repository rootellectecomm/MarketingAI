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
  const body = await req.json();

  console.log("Webhook Event:", JSON.stringify(body));

  return NextResponse.json({ success: true }, { status: 200 });
}

