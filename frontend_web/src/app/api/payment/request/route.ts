import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";

export async function POST(request: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session || !session.user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { planId } = await request.json();
    
    // Define items/prices (In real scenario, fetch from DB)
    const plans: Record<string, { name: string; price: string }> = {
      "premium_1m": { name: "Stock Now 프리미엄 (1개월)", price: "1000" }, // Test price
      "premium_3m": { name: "Stock Now 프리미엄 (3개월)", price: "2700" },
    };

    const plan = plans[planId];
    if (!plan) {
      return NextResponse.json({ error: "Invalid plan" }, { status: 400 });
    }

    // Payapp API Request
    const formData = new URLSearchParams();
    formData.append("cmd", "payrequest");
    formData.append("userid", process.env.PAYAPP_USER_ID || "");
    formData.append("goodname", plan.name);
    formData.append("price", plan.price);
    formData.append("recvname", session.user.name || "사용자");
    formData.append("recvemail", session.user.email || "");
    formData.append("smsuse", "n"); // Don't send SMS from Payapp
    formData.append("var1", session.user.id); // Store userId to match in webhook
    formData.append("var2", planId); // Store planId
    
    // Dynamic feedbackurl to support multiple projects
    // Note: process.env.NEXTAUTH_URL should be the base domain
    const feedbackUrl = `${process.env.NEXTAUTH_URL}/api/payment/webhook`;
    formData.append("feedbackurl", feedbackUrl);

    const response = await fetch("https://api.payapp.co.kr/oapi/api_payrequest.html", {
      method: "POST",
      body: formData,
    });

    const text = await response.text();
    // Parse result (Payapp returns query string like result=0&payurl=...)
    const resultParams = new URLSearchParams(text);
    const state = resultParams.get("state");
    const payurl = resultParams.get("payurl");

    if (state === "1" && payurl) {
      return NextResponse.json({ payurl });
    } else {
      console.error("Payapp Request Failed:", text);
      return NextResponse.json({ error: "Payapp request failed", details: text }, { status: 500 });
    }

  } catch (error) {
    console.error("Failed to process payment request:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
