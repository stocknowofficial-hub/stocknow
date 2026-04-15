"""
dashboard_promo.py
정해진 시각에 VIP/Free 채널에 대시보드 유도 메시지를 발송합니다.

발송 시각 (KST):
  - 07:10: 미국장 마감 후 — 간밤 월가 데이터 확인 유도
  - 16:10: 국내장 마감 후 — 장 마감 리포트 확인 유도
"""

import asyncio
import ujson
from datetime import datetime

import pytz

from common.config import settings
from common.logger import setup_logger
from common.redis_client import redis_client

logger = setup_logger("DashboardPromo", "logs/watcher", "watcher.log")

KST = pytz.timezone("Asia/Seoul")

MSG_MORNING = """\
[Stock Now] 뉴욕 증시 마감 브리핑

간밤 월가에는 어떤 변화가 있었을까요?
오늘 장 시작 전, 반드시 체크해야 할 미국장 핵심 데이터를 정리했습니다.

▪️ 거래량 Top 10 종목 흐름
▪️ AI 단기 예측 결과 업데이트
▪️ 월가 최신 컨센서스 분석

오늘 국내장 대응 전략, 대시보드에서 바로 세워보세요.
🔗 https://stock-now.co.kr/dashboard"""

MSG_EVENING = """\
[Stock Now] 정규장 마감 리포트

치열했던 오늘 하루, 시장의 수급은 어디로 향했을까요?
장 마감과 동시에 업데이트된 핵심 지표를 확인해 보세요.

▪️ 오늘의 수급 현황 (외국인/기관)
▪️ AI 예측 적중 여부 및 피드백
▪️ 장 마감 후 발간된 최신 리포트

내일의 주도주 힌트를 지금 대시보드에서 확인하세요.
🔗 https://stock-now.co.kr/dashboard"""


async def _send_promo(message: str, label: str):
    payload = {
        "type": "MARKET_LINK",
        "name": label,
        "message": message,
    }
    await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
    logger.info(f"📣 [DashboardPromo] 발송 완료: {label}")


async def run_dashboard_promo():
    logger.info("📣 [DashboardPromo] 대시보드 유도 메시지 태스크 시작")
    logger.info("   발송 시각: KST 07:10 (미국장 마감), KST 16:10 (국내장 마감)")

    last_morning: str = ""   # "YYYY-MM-DD" 형식으로 중복 발송 방지
    last_evening: str = ""

    # 시작 직후 self-healing restarter(07:00)와 충돌 방지를 위해 잠깐 대기
    await asyncio.sleep(30)

    while True:
        try:
            now = datetime.now(KST)
            weekday = now.weekday()   # 0=월 … 4=금, 5=토, 6=일
            today = now.strftime("%Y-%m-%d")
            h, m = now.hour, now.minute

            # 07:10 ~ 07:30 (평일 + 토요일 — 미국 금요일 마감 포함)
            if weekday <= 5 and h == 7 and 10 <= m < 30 and last_morning != today:
                last_morning = today
                await _send_promo(MSG_MORNING, "미국장 마감 브리핑")

            # 16:10 ~ 16:30 (평일만 — 국내장 마감)
            if weekday < 5 and h == 16 and 10 <= m < 30 and last_evening != today:
                last_evening = today
                await _send_promo(MSG_EVENING, "정규장 마감 리포트")

        except Exception as e:
            logger.error(f"❌ [DashboardPromo] 오류: {e}", exc_info=True)

        await asyncio.sleep(60)   # 1분마다 시간 체크
