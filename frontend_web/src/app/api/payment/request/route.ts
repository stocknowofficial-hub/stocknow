import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { PLANS } from "@/lib/plans";

export async function POST(request: Request) {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { planId } = await request.json();
    const plan = PLANS[planId];
    if (!plan) {
      return NextResponse.json({ error: "Invalid plan" }, { status: 400 });
    }

    const userId = session.user.id as string;
    const baseUrl = process.env.NEXTAUTH_URL || "https://stock-now.pages.dev";

    const formData = new URLSearchParams();
    formData.append("cmd", "payrequest");
    formData.append("userid", process.env.PAYAPP_USER_ID || "");
    formData.append("api_key", process.env.PAYAPP_API_KEY || "");
    formData.append("goodname", plan.name);
    formData.append("price", String(plan.price));
    formData.append("recvname", session.user.name || "사용자");
    formData.append("recvemail", session.user.email || "");
    formData.append("recvphone", "01000000000");
    formData.append("smsuse", "n");
    formData.append("var1", userId);   // webhook에서 유저 식별
    formData.append("var2", plan.id);  // webhook에서 플랜 식별
    formData.append("feedbackurl", `${baseUrl}/api/payment/webhook`);
    formData.append("returnurl", `${baseUrl}/dashboard?payment=success`);
    formData.append("cancelurl", `${baseUrl}/dashboard?payment=cancel`);

    const response = await fetch("https://api.payapp.kr/oapi/apiLoad.html", {
      method: "POST",
      body: formData,
    });

    const text = await response.text();
    const result = new URLSearchParams(text);
    const state = result.get("state");
    const payurl = result.get("payurl");

    console.log("[Payment Request] planId:", planId, "userId:", userId, "state:", state);

    if (state === "1" && payurl) {
      return NextResponse.json({ payurl });
    }

    console.error("[Payment Request] Payapp error:", text);
    return NextResponse.json(
      { error: "결제 URL 생성 실패", details: text },
      { status: 500 }
    );
  } catch (error) {
    console.error("[Payment Request] Exception:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
