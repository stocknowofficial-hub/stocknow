// Telegram Bot API 유틸리티 (Cloudflare Workers 환경에서 사용)

const BOT_TOKEN = () => process.env.TELEGRAM_BOT_TOKEN ?? "";
const VIP_CHANNEL_ID = () => process.env.TELEGRAM_VIP_CHANNEL_ID ?? "-1003564191070";
const SITE_URL = () => process.env.NEXTAUTH_URL ?? "https://stock-now.pages.dev";

/**
 * VIP 채널 1회용 초대 링크를 생성하고 유저에게 DM으로 발송
 * - 이미 채널 멤버면 안내 메시지만 발송 (링크 생성 안 함)
 * - prevInviteLink 있으면 revoke 후 새 링크 발급
 * @returns 새로 발급된 초대 링크 URL (실패 또는 이미 멤버면 null)
 */
export async function sendVipInvite(
  telegramId: string,
  userName: string,
  planDisplay: string = "STANDARD",
  expiresAt: string | null = null,
  prevInviteLink: string | null = null
): Promise<string | null> {
  const token = BOT_TOKEN();
  const channelId = VIP_CHANNEL_ID();
  if (!token || !channelId) {
    console.error("[Telegram] BOT_TOKEN or VIP_CHANNEL_ID not set");
    return null;
  }

  try {
    // 0. 이미 채널 멤버인지 확인 — 이미 있으면 새 링크 생성 불필요
    const memberRes = await fetch(
      `https://api.telegram.org/bot${token}/getChatMember`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: channelId, user_id: telegramId }),
      }
    );
    const memberData = (await memberRes.json()) as { ok: boolean; result?: { status: string } };
    const memberStatus = memberData?.result?.status;

    if (memberStatus === "kicked") {
      await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: telegramId,
          text: `🚫 채널에서 차단(내보내기)되어 입장할 수 없는 상태입니다.\n\n오류라고 생각되시면 관리자에게 문의해주세요.`,
          parse_mode: "Markdown",
        }),
      });
      console.log("[Telegram] 차단된(kicked) 채널 멤버 — 초대 링크 생략:", telegramId);
      return null;
    }

    if (memberStatus === "member" || memberStatus === "administrator" || memberStatus === "creator") {
      await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: telegramId,
          text: `✅ 이미 VIP 채널에 입장되어 있습니다!\n\n구독 관리는 여기서: ${SITE_URL()}/dashboard`,
          parse_mode: "Markdown",
        }),
      });
      console.log("[Telegram] 이미 채널 멤버 — 초대 링크 생략:", telegramId);
      return null;
    }

    // 1. 기존 링크 있으면 그대로 재발송 (revoke 금지 — 이중 호출 시 유효 링크가 revoke되는 버그 방지)
    if (prevInviteLink) {
      const expiresDisplay = expiresAt
        ? new Date(expiresAt).toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" })
        : "무제한";
      const text =
        `[Stock Now] VIP 채널 입장 안내\n\n` +
        `안녕하세요, ${userName}님.\n` +
        `지금부터 *${planDisplay}* 동안 AI가 분석하는 실시간 주도주와 핵심 브리핑을 받아보실 수 있습니다.\n\n` +
        `▪️ 이용 기한: ${expiresDisplay}까지\n` +
        `▪️ 입장 링크: ${prevInviteLink}\n\n` +
        `본 링크는 보안을 위한 1회용 링크입니다.\n` +
        `입장 후 채널을 이탈하시면 재입장이 제한될 수 있습니다.`;
      await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: telegramId, text, parse_mode: "Markdown" }),
      });
      console.log("[Telegram] 기존 초대 링크 재발송 (revoke 없음):", telegramId, prevInviteLink);
      return prevInviteLink;
    }

    // 2. 기존 링크 없을 때만 새 1회용 초대 링크 생성
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

    console.log("[Telegram] createChatInviteLink 응답:", JSON.stringify(inviteData));

    if (!inviteData.ok || !inviteData.result?.invite_link) {
      console.error("[Telegram] 초대 링크 생성 실패:", JSON.stringify(inviteData));
      return null;
    }

    const inviteLink = inviteData.result.invite_link;
    console.log("[Telegram] 새 초대 링크 생성됨:", inviteLink, "/ member_limit:", inviteData.result);

    const expiresDisplay = expiresAt
      ? new Date(expiresAt).toLocaleDateString("ko-KR", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })
      : "무제한";

    // 3. 유저에게 DM 발송
    const text =
      `[Stock Now] VIP 채널 입장 안내\n\n` +
      `안녕하세요, ${userName}님.\n` +
      `지금부터 *${planDisplay}* 동안 AI가 분석하는 실시간 주도주와 핵심 브리핑을 받아보실 수 있습니다.\n\n` +
      `▪️ 이용 기한: ${expiresDisplay}까지\n` +
      `▪️ 입장 링크: ${inviteLink}\n\n` +
      `본 링크는 보안을 위한 1회용 링크입니다.\n` +
      `입장 후 채널을 이탈하시면 재입장이 제한될 수 있습니다.`;

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
      return null;
    }

    console.log("[Telegram] VIP 초대 링크 발송 완료 →", telegramId);
    return inviteLink;
  } catch (e) {
    console.error("[Telegram] sendVipInvite 예외:", e);
    return null;
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
