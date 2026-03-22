// Telegram Bot API 유틸리티 (Cloudflare Workers 환경에서 사용)

const BOT_TOKEN = () => process.env.TELEGRAM_BOT_TOKEN ?? "";
const VIP_CHANNEL_ID = () => process.env.TELEGRAM_VIP_CHANNEL_ID ?? "-1003373972207";
const SITE_URL = () => process.env.NEXTAUTH_URL ?? "https://stock-now.pages.dev";

/**
 * VIP 채널 1회용 초대 링크를 생성하고 유저에게 DM으로 발송
 */
export async function sendVipInvite(
  telegramId: string,
  userName: string,
  planDisplay: string = "STANDARD",
  expiresAt: string | null = null
): Promise<boolean> {
  const token = BOT_TOKEN();
  const channelId = VIP_CHANNEL_ID();
  if (!token || !channelId) {
    console.error("[Telegram] BOT_TOKEN or VIP_CHANNEL_ID not set");
    return false;
  }

  try {
    // 1. 1회용 초대 링크 생성 (30분 후 만료, 최대 1명)
    const expireUnix = Math.floor(Date.now() / 1000) + 60 * 60 * 24 * 7; // 7일 유효
    const inviteRes = await fetch(
      `https://api.telegram.org/bot${token}/createChatInviteLink`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: channelId,
          member_limit: 1,
          expire_date: expireUnix,
          name: `VIP_${telegramId}_${Date.now()}`,
        }),
      }
    );
    const inviteData = (await inviteRes.json()) as {
      ok: boolean;
      result?: { invite_link: string };
    };

    if (!inviteData.ok || !inviteData.result?.invite_link) {
      console.error("[Telegram] 초대 링크 생성 실패:", JSON.stringify(inviteData));
      return false;
    }

    const inviteLink = inviteData.result.invite_link;

    const expiresDisplay = expiresAt
      ? new Date(expiresAt).toLocaleDateString("ko-KR", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })
      : "무제한";

    // 2. 유저에게 DM 발송
    const text =
      `🎉 *VIP 채널에 입장하세요*\n\n` +
      `안녕하세요, ${userName}님!\n` +
      `*${planDisplay}*이 시작됩니다!\n\n` +
      `📅 이용 기간: ${expiresDisplay}\n\n` +
      `아래 링크로 VIP 채널에 입장하세요:\n` +
      `👉 ${inviteLink}\n\n` +
      `⚠️ 이 링크는 1회용이며 7일간 유효합니다.\n` +
      `입장 후 채널을 떠나지 마세요!`;

    const msgRes = await fetch(
      `https://api.telegram.org/bot${token}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: telegramId,
          text,
          parse_mode: "Markdown",
        }),
      }
    );
    const msgData = (await msgRes.json()) as { ok: boolean };

    if (!msgData.ok) {
      console.error("[Telegram] DM 발송 실패 (telegramId:", telegramId, "):", JSON.stringify(msgData));
      return false;
    }

    console.log("[Telegram] VIP 초대 링크 발송 완료 →", telegramId);
    return true;
  } catch (e) {
    console.error("[Telegram] sendVipInvite 예외:", e);
    return false;
  }
}

/**
 * 만료 알림 + 재결제 안내 메시지 발송
 */
export async function sendExpiryNotice(
  telegramId: string,
  userName: string,
  expiresAt: string
): Promise<boolean> {
  const token = BOT_TOKEN();
  const siteUrl = SITE_URL();
  if (!token) return false;

  try {
    const expiresDisplay = expiresAt.split("T")[0];
    const text =
      `😭 *${userName}님, 구독이 만료되었습니다*\n\n` +
      `(${expiresDisplay} 만료)\n\n` +
      `더 이상 VIP 채널의 실시간 정보를 받아보실 수 없습니다.\n` +
      `계속해서 최고의 투자 정보를 받으시려면 멤버십을 갱신해주세요!\n\n` +
      `👉 *[멤버십 갱신하기]*\n${siteUrl}/dashboard`;

    const res = await fetch(
      `https://api.telegram.org/bot${token}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: telegramId,
          text,
          parse_mode: "Markdown",
        }),
      }
    );
    const data = (await res.json()) as { ok: boolean };
    return data.ok;
  } catch (e) {
    console.error("[Telegram] sendExpiryNotice 예외:", e);
    return false;
  }
}
