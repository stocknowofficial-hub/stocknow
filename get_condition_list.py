# 조건검색 리스트 찾는 코드
import requests
import json
import os
from common.config import settings
from watcher.kis_auth import get_access_token

# 👇 사장님 HTS 아이디
MY_HTS_ID = "chh6518"

def get_my_condition_list():
    print("🚀 [조건검색 목록] 조회 시작 (API 문서 정석 Ver)...")

    # 1. 토큰 정리 & 재발급
    if os.path.exists("token.dat"):
        try: os.remove("token.dat")
        except: pass
    
    token = get_access_token()
    if not token:
        print("❌ 토큰 발급 실패.")
        return

    # [사진1 참고] 조건검색 목록 조회 URL
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/psearch-title"
    
    # [사진1 참고] Header (Required='Y' 항목만 구성)
    headers = {
        "content-type": "application/json; utf-8",   # 필수
        "authorization": f"Bearer {token}",          # 필수
        "appkey": settings.KIS_APP_KEY,              # 필수
        "appsecret": settings.KIS_APP_SECRET,        # 필수
        "tr_id": "HHKST03900300",                    # 🚨 [핵심] 목록 조회용 TR ID
        "custtype": "P"                              # 필수 (개인)
    }
    
    # [사진1 참고] Query Parameter (Required='Y' 항목만 구성)
    params = {
        "user_id": MY_HTS_ID                         # 필수
    }
    
    print(f"📡 요청 보내는 중... (TR_ID: {headers['tr_id']})")
    
    try:
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        
        print("\n================ [ 응답 결과 ] ================")
        
        # [사진2 참고] 정상 응답 시 output2 (Array)에 데이터가 옴
        if 'output2' in data:
            result_list = data['output2']
            print(f"✅ 성공! 총 {len(result_list)}개의 조건식을 가져왔습니다.\n")
            
            for item in result_list:
                # [사진2 참고] seq(조건키값), grp_nm(그룹명), condition_nm(조건명)
                seq = item['seq']
                grp = item['grp_nm']
                name = item['condition_nm']
                
                print(f"   🎯 [SEQ: {seq}]  {name}  (그룹: {grp})")
                
        else:
            # 실패 시 원본 메시지 출력
            print("❌ 목록이 없습니다 (응답 원본):")
            print(json.dumps(data, indent=4, ensure_ascii=False))

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    get_my_condition_list()