import { NextResponse } from "next/server";
import { createAdminCookieHeader } from "@/lib/admin-auth";

export async function POST(request: Request) {
  try {
    const { username, password } = await request.json();

    if (
      username !== process.env.ADMIN_USERNAME ||
      password !== process.env.ADMIN_PASSWORD
    ) {
      return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
    }

    const cookieHeader = await createAdminCookieHeader();
    return NextResponse.json(
      { ok: true },
      { headers: { "Set-Cookie": cookieHeader } }
    );
  } catch {
    return NextResponse.json({ error: "Server error" }, { status: 500 });
  }
}
