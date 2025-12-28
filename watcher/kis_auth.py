import requests
import ujson
from common.config import settings

# ... (기존 get_approval_key 함수는 그대로 둠) ...

def get_approval_key():
    """웹소켓 접속키 발급 (기존과 동일)"""
    url = f"{settings.KIS_BASE_URL}/oauth2/Approval"
    headers = {"content-type": "application/json; utf-8"}
    body = {
        "grant_type": "client_credentials",
        "appkey": settings.KIS_APP_KEY,
        "secretkey": settings.KIS_APP_SECRET
    }
    try:
        res = requests.post(url, headers=headers, data=ujson.dumps(body))
        if res.status_code == 200:
            return res.json().get("approval_key")
        return None
    except Exception as e:
        print(f"❌ [Auth] 오류: {e}")
        return None

def get_access_token():
    """
    [NEW] REST API용 접근 토큰 발급
    (랭킹 조회 등 일반 데이터 조회에 필요함)
    """
    url = f"{settings.KIS_BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json; utf-8"}
    body = {
        "grant_type": "client_credentials",
        "appkey": settings.KIS_APP_KEY,
        "appsecret": settings.KIS_APP_SECRET
    }
    try:
        res = requests.post(url, headers=headers, data=ujson.dumps(body))
        if res.status_code == 200:
            return res.json().get("access_token")
        else:
            print(f"❌ [Auth] Access Token 발급 실패: {res.text}")
    except Exception as e:
        print(f"❌ [Auth] 시스템 오류: {e}")
    return None