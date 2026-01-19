import asyncio
import requests
import ujson
from bs4 import BeautifulSoup
from common.redis_client import redis_client
from common.config import settings

# 트럼프 형님 계정
TARGET_HANDLE = "realDonaldTrump"
API_BASE_URL = "https://truthsocial.com/api/v1"
BASE_URL = "https://truthsocial.com"

# ✅ 내부 캐시
LAST_POST_REAL_ID = None 
TRUMP_ACCOUNT_ID = None # API로 조회한 숫자 ID (예: 107...)

# ✅ [Headers] CloudScraper 대신 일반 헤더 사용 (테스트 성공)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://truthsocial.com/"
}

async def get_trump_account_id(headers):
    """
    User Handle(@realDonaldTrump) -> Account ID(숫자) 변환
    """
    url = f"{API_BASE_URL}/accounts/lookup?acct={TARGET_HANDLE}"
    try:
        loop = asyncio.get_running_loop()
        # cloudscraper -> requests
        response = await loop.run_in_executor(None, lambda: requests.get(url, headers=HEADERS, timeout=15))
        
        if response.status_code == 200:
            data = response.json()
            return data.get('id')
        else:
            print(f"⚠️ [SNS Watcher] 계정 조회 실패: {response.status_code} - {response.text[:100]}")
            return None
    except Exception as e:
        print(f"❌ [SNS Watcher] 계정 조회 에러: {e}")
        return None

async def run_trump_watcher():
    global LAST_POST_REAL_ID, TRUMP_ACCOUNT_ID
    print(f"🇺🇸 [SNS Watcher] 트럼프 전담 마크맨 (Requests Ver.) 가동 중...")

    # CloudScraper가 알아서 헤더 관리하므로, 기본 Accept만 추가
    # headers = ... (제거)

    while True:
        try:
            # 1. ID 확보 (없으면 조회)
            if not TRUMP_ACCOUNT_ID:
                TRUMP_ACCOUNT_ID = await get_trump_account_id(None)
                if not TRUMP_ACCOUNT_ID:
                    print("⚠️ [SNS Watcher] 트럼프 ID를 못 찾았습니다. 잠시 대기...")
                    await asyncio.sleep(60)
                    continue
                else:
                    print(f"✅ [SNS Watcher] 타겟 고정 완료. Account ID: {TRUMP_ACCOUNT_ID}")

            # 2. 최신 타임라인 조회 (Posts)
            api_url = f"{API_BASE_URL}/accounts/{TRUMP_ACCOUNT_ID}/statuses?exclude_replies=true&limit=1"
            
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, lambda: requests.get(api_url, headers=HEADERS, timeout=15))

            if response.status_code == 200:
                posts = response.json()
                
                if posts and len(posts) > 0:
                    latest_post = posts[0]
                    
                    # -------------------------------------------------
                    # 📝 데이터 파싱 (JSON)
                    # -------------------------------------------------
                    current_id = str(latest_post.get('id'))
                    
                    # HTML 태그 제거 (Content가 HTML로 옴)
                    raw_html = latest_post.get('content', '')
                    soup = BeautifulSoup(raw_html, 'html.parser')
                    post_text = soup.get_text(separator=' ', strip=True) 
                    
                    # 시간 (UTC ISO format -> 예쁘게 변환은 Worker가 하거나 그대로 전달)
                    post_time = latest_post.get('created_at')
                    
                    # 링크
                    post_link = latest_post.get('url', '') # API가 친절하게 Link 줌!

                    # -------------------------------------------------
                    # 🚦 판단 로직 (ID 비교)
                    # -------------------------------------------------
                    if current_id:
                        # [초기화] 봇 켜고 처음 봤을 때 -> 기준점만 설정
                        if LAST_POST_REAL_ID is None:
                            LAST_POST_REAL_ID = current_id
                            print(f"✅ [SNS Watcher] 기준점 설정 완료: ID {current_id} ({post_time})")
                        
                        # [새 글 발견] 저장된 ID랑 다를 때
                        elif LAST_POST_REAL_ID != current_id:
                            # ✅ [필터] 텍스트 없는 글(사진/영상만 있는 경우)은 스킵
                            if not post_text:
                                print(f"🔇 [SNS Watcher] 텍스트가 없는 미디어 게시글입니다. (Skip) - ID: {current_id}")
                                LAST_POST_REAL_ID = current_id 
                                continue

                            print(f"🚨 [속보] (API) 트럼프 새 글 발견! (ID: {current_id})")
                            
                            payload = {
                                "type": "SNS_ANALYSIS",
                                "source": "Truth Social",
                                "author": "Donald Trump",
                                "text": post_text,
                                "time": post_time,
                                "url": post_link
                            }
                            await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps(payload))
                            
                            LAST_POST_REAL_ID = current_id
                else:
                    print("🤔 [SNS Watcher] 게시글이 0개입니다.")

            else:
                print(f"⚠️ [SNS Watcher] 타임라인 조회 실패: {response.status_code}")

        except Exception as e:
            print(f"❌ [SNS Watcher] 크롤링 에러: {e}")

        # 2분 대기 (API Rate Limit 고려)
        await asyncio.sleep(120)
