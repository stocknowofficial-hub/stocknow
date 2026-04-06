import asyncio
import ujson
import time
import aiohttp
from datetime import datetime
from common.config import settings
from common.redis_client import redis_client
from watcher.utils.definitions import (
    check_today_actionable,
    fetch_kr_volume_rank,
    fetch_kr_bulk_rank,
    fetch_kr_trading_value_rank,
    fetch_kr_program_trend,
    fetch_kr_investor_trend,
    fetch_kr_broker_trend,
    fetch_kr_foreign_estimate,
    fetch_kr_frgn_inst_rank,
    update_telegraph_board,
    update_telegraph_frgn_inst,
    setup_telegraph_account
)
import os


async def push_to_dashboard(frgn_top10: list, inst_top10: list, vol_top_20: list):
    """웹 대시보드 D1에 수급 데이터 업로드 (5분마다 호출)
    - frgn_top10: FHPTJ04400000 외국인 순매수 Top10
    - inst_top10: FHPTJ04400000 기관계 순매수 Top10
    - vol_top_20: 거래량 Top20
    """
    secret = getattr(settings, 'WHALE_SECRET', '') or os.environ.get('WHALE_SECRET', '')
    if not secret:
        return

    def extract_frgn_inst(items: list, amt_field: str) -> list:
        """FHPTJ04400000 응답 → 대시보드 포맷 (백만원 → 억원)"""
        result = []
        for s in items:
            name = s.get('hts_kor_isnm') or s.get('name', '')
            code = s.get('mksc_shrn_iscd') or s.get('code', '')
            try:
                price = int(str(s.get('stck_prpr') or s.get('price', 0)).replace(',', ''))
            except:
                price = 0
            chgrate = str(s.get('prdy_ctrt') or s.get('chgrate', '0')).strip()
            try:
                amt_eok = int(str(s.get(amt_field, 0)).replace(',', '')) / 100  # 백만원 → 억원
            except:
                amt_eok = 0.0
            result.append({"name": name, "code": code, "price": price, "chgrate": chgrate, "amount_eok": round(amt_eok, 1)})
        return result

    def extract_volume(items: list) -> list:
        result = []
        for s in items:
            name = s.get('hts_kor_isnm') or s.get('name', '')
            code = s.get('mksc_shrn_iscd') or s.get('code', '')
            try:
                price = int(str(s.get('stck_prpr') or s.get('price', 0)).replace(',', ''))
            except:
                price = 0
            chgrate = str(s.get('prdy_ctrt') or s.get('chgrate', '0')).strip()
            try:
                acml_vol = int(str(s.get('acml_vol', 0)).replace(',', ''))
            except:
                acml_vol = 0
            result.append({"name": name, "code": code, "price": price, "chgrate": chgrate, "acml_vol": acml_vol})
        return result

    # 외국인/기관 타임스탬프 헤더 (언제 데이터인지 명시)
    ts_header = []
    if latest_frgn_inst_updated_at:
        ts_header = [{"name": f"📅 {latest_frgn_inst_updated_at} 기준 (하루 4회 업데이트)", "is_header": True, "code": "", "price": 0, "chgrate": "0"}]

    payload = {
        "market": "KR",
        "foreign_items": ts_header + extract_frgn_inst(frgn_top10, 'frgn_ntby_tr_pbmn'),  # 외국인
        "program_items": ts_header + extract_frgn_inst(inst_top10, 'orgn_ntby_tr_pbmn'),  # 기관 (program 컬럼 재활용)
        "volume_items":  extract_volume(vol_top_20),
    }

    url = f"{settings.CLOUDFLARE_URL}/api/whale-feed"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers={"X-Secret-Key": secret},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    print(f"📡 [Dashboard] D1 업데이트 완료 (외국인 {len(payload['foreign_items'])} / 기관 {len(payload['program_items'])} / 거래량 {len(payload['volume_items'])})")
                else:
                    print(f"⚠️ [Dashboard] D1 업데이트 실패: HTTP {resp.status}")
    except Exception as e:
        print(f"⚠️ [Dashboard] push 실패: {e}")

# ----------------------------------------
# 📊 Dashboard State
# ----------------------------------------
TELEGRAPH_CONFIG_PATH = "telegraph_config_kr.json"
telegraph_config = {"access_token": "", "path": "", "url": "", "path_saved": False}
last_dashboard_update = 0

# 🏦 외국인/기관 수급 동향 보드
TELEGRAPH_FRGN_INST_PATH = "telegraph_config_kr_frgn.json"
frgn_inst_config = {"access_token": "", "path": "", "url": "", "path_saved": False}
frgn_inst_sent_slots = set()   # 당일 발송된 슬롯 추적
FRGN_INST_SLOTS = [930, 1120, 1320, 1430]  # 업데이트 시각 (HHMM)

# 📡 대시보드용 외국인/기관 최신 캐시 (슬롯 업데이트 시 갱신)
latest_frgn_top10: list = []
latest_inst_top10: list = []
latest_frgn_inst_updated_at: str = ""  # 마지막 업데이트 시각 (예: "03월 31일 14:30")

if os.path.exists(TELEGRAPH_FRGN_INST_PATH):
    try:
        with open(TELEGRAPH_FRGN_INST_PATH, "r") as f:
            saved = ujson.load(f)
            frgn_inst_config.update(saved)
            frgn_inst_config["path_saved"] = True
    except: pass

# Load Config
if os.path.exists(TELEGRAPH_CONFIG_PATH):
    try:
        with open(TELEGRAPH_CONFIG_PATH, "r") as f:
            saved = ujson.load(f)
            telegraph_config.update(saved)
            telegraph_config["path_saved"] = True
    except: pass
else:
    # Initial Setup
    setup_telegraph_account(telegraph_config)


# 🐳 K-Whale 설정
# [변경] 누적(Daily) -> 순간체결(Delta 30s) 기준으로 변경
# 30초 동안 순매수가 이만큼 '증가'하면 알림
# [Điều chỉnh] 알림 감도 상향 (10억 -> 3억 / 50억 -> 10억)
MIN_PROGRAM_DELTA_GENERAL = 300000000       # 3억 (30초간 급증)
MIN_PROGRAM_DELTA_LARGE_CAP = 1000000000   # 10억 (30초간 급증 - 대형주)

SCAN_INTERVAL = 30

# 대형주 목록 (시총 상위 20위) - 알림 기준 상향 대상
LARGE_CAP_CODES = {
    "005930", "373220", "000660", "207940", "005935", 
    "005380", "000270", "005490", "105560", "035420",
    "006400", "051910", "068270", "035720", "012330",
    "028260", "003550", "032830", "055550", "323410"
}
alert_history = {} # 중복 알림 방지 (쿨타임)
sent_slots = set() # 스케줄 알림 (09:15, 12:20, 15:10)
last_dashboard_link_sent = 0 # 마지막 링크 발송 시간
prev_prog_map = {} # 이전 프로그램 순매수 저장 (Delta 계산용)

prev_frgn_map = {} # 이전 외국인 순매수 저장 (Delta 계산용)

async def run_whale_watcher_kr(approval_key, access_token):
    """
    🐳 [K-Whale Hunter] 국내 주식 수급 포착 (프로그램 + 외국인)
    """
    global alert_history, prev_prog_map, prev_frgn_map, last_dashboard_update, latest_frgn_top10, latest_inst_top10, latest_frgn_inst_updated_at
    print(f"🐳 [K-Whale Hunter] 가동 시작 (Delta Mode | General: {MIN_PROGRAM_DELTA_GENERAL//100000000}억, LargeCap: {MIN_PROGRAM_DELTA_LARGE_CAP//100000000}억)")

    while True:
        try:
            # 1. 시간 & 개장 여부 체크
            # Strict Time Check (08:50 ~ 15:40) to prevent late night alerts
            now = datetime.now()
            current_time = int(now.strftime("%H%M"))
            
            # 주말 체크
            if now.weekday() >= 5:
                # 메모리 초기화 (주말)
                prev_prog_map.clear()
                prev_frgn_map.clear()
                await asyncio.sleep(3600)
                continue
                
            # 시간 체크 (08:50 ~ 15:40)
            if not (850 <= current_time <= 1540):
                # Reset history at midnight or after close
                if current_time > 1600:
                    alert_history.clear()
                    sent_slots.clear()
                    frgn_inst_sent_slots.clear()  # 수급동향 슬롯도 초기화
                    prev_prog_map.clear()
                    prev_frgn_map.clear()
                await asyncio.sleep(60)
                continue

            # ─────────────────────────────────────────────
            # 🏦 외국인/기관 수급 동향 스냅샷 (하루 4회)
            # ─────────────────────────────────────────────
            for slot in FRGN_INST_SLOTS:
                slot_str = f"{slot:04d}"
                # 슬롯 시각 ±15분 범위 내이고 아직 미발송
                slot_passed = slot <= current_time <= slot + 15
                if slot_passed and slot_str not in frgn_inst_sent_slots:
                    try:
                        loop = asyncio.get_running_loop()
                        frgn_top10 = await loop.run_in_executor(None, fetch_kr_frgn_inst_rank, access_token, "1")
                        inst_top10 = await loop.run_in_executor(None, fetch_kr_frgn_inst_rank, access_token, "2")

                        # 📡 대시보드 캐시 업데이트
                        if frgn_top10:
                            latest_frgn_top10.clear()
                            latest_frgn_top10.extend(frgn_top10)
                        if inst_top10:
                            latest_inst_top10.clear()
                            latest_inst_top10.extend(inst_top10)
                        if frgn_top10 or inst_top10:
                            latest_frgn_inst_updated_at = datetime.now().strftime("%m월 %d일 %H:%M")

                        if frgn_top10 or inst_top10:
                            board_url = update_telegraph_frgn_inst(frgn_inst_config, frgn_top10, inst_top10)

                            # 설정 저장 (최초 생성 시)
                            if not frgn_inst_config.get("path_saved") and frgn_inst_config["path"]:
                                with open(TELEGRAPH_FRGN_INST_PATH, "w") as f:
                                    ujson.dump({"access_token": frgn_inst_config["access_token"],
                                                "path": frgn_inst_config["path"],
                                                "url": frgn_inst_config["url"]}, f)
                                frgn_inst_config["path_saved"] = True

                            if board_url:
                                slot_label = f"{slot // 100:02d}:{slot % 100:02d}"
                                msg = (
                                    f"🏦 *외국인/기관 수급 동향* 업데이트 ({slot_label})\n"
                                    f"외국인 Top10 + 기관계 Top10 스냅샷\n\n"
                                    f"🔗 [수급 동향 보기]({board_url})"
                                )
                                await redis_client.publish(settings.REDIS_CHANNEL_STOCK, ujson.dumps({
                                    "type": "MARKET_LINK",
                                    "market": "KR",
                                    "subtype": "FRGN_INST",
                                    "message": msg,
                                }))
                                print(f"🏦 [수급동향] {slot_label} 스냅샷 발송 완료: {board_url}")

                        frgn_inst_sent_slots.add(slot_str)
                    except Exception as e:
                        print(f"⚠️ [수급동향] 슬롯 {slot} 처리 오류: {e}")
                        frgn_inst_sent_slots.add(slot_str)  # 오류 시도 슬롯도 추가 (무한 재시도 방지)

            # ... (Skip existing code until Step 2 Foreign calculation) ...
            
            # 2. 거래량 급등/상위 종목 스캔 (후보군 선정)
            # 2. 후보군 선정 (Volume Rank + Bulk Rank w/ Duplicate Removal)
            # A. 거래량 상위
            c_vol = fetch_kr_volume_rank(access_token)
            # B. 대량체결 매수 상위 (New!)
            c_bulk = fetch_kr_bulk_rank(access_token)
            
            # Merge & Deduplicate
            candidates = c_vol + c_bulk
            # Simple dedupe by code
            seen = set()
            unique_candidates = []
            for c in candidates:
                code = c.get('mksc_shrn_iscd')
                if code and code not in seen:
                    unique_candidates.append(c)
                    seen.add(code)
            
            candidates = unique_candidates

            # 📉 [Fallback Removed] API 실패시 그냥 다음 턴 대기
            if not candidates:
                # print("⚠️ [K-Whale] Candidate API returned empty. Retrying...")
                await asyncio.sleep(5)
                continue
                
            loop = asyncio.get_event_loop()

            # ---------------------------------------------------------
            # 🌍 [Pre-Fetch] 외국인 가집계 (전체 종목, 1회 호출)
            # ---------------------------------------------------------
            # 개별 조회 대신 여기서 맵핑 create
            frgn_est_list = await loop.run_in_executor(None, fetch_kr_foreign_estimate, access_token)
            frgn_map = {}
            if frgn_est_list:
                for item in frgn_est_list:
                    try:
                        f_code = item['stck_shrn_iscd']
                        buy_qty = int(item.get('glob_total_shnu_qty', 0))
                        sell_qty = int(item.get('glob_total_seln_qty', 0))
                        net_qty = buy_qty - sell_qty
                        frgn_map[f_code] = net_qty
                    except: pass
            
            # 상위 40개 분석 (범위 확대)
            for stock in candidates[:40]:
                code = stock.get('mksc_shrn_iscd')
                name = stock.get('hts_kor_isnm')
                # stck_prpr might be string with commas
                try: 
                    current_price = int(str(stock.get('stck_prpr', '0')).replace(',', ''))
                except: current_price = 0
                
                rate = stock.get('prdy_ctrt')
                
                if not code: continue
                
                # ---------------------------------------------------------
                # 🕵️‍♂️ Step 1: 프로그램 순매수 "급증(Delta)" 확인 (Trigger)
                # ---------------------------------------------------------
                prog_data = await loop.run_in_executor(None, fetch_kr_program_trend, access_token, code)
                
                # prog_data는 리스트(시간별 추이). 최신 값([0]) 확인
                if not prog_data: continue
                
                latest_prog = prog_data[0]
                # whol_smtn_ntby_tr_pbmn: 전체 합계 순매수 거래 대금 (백만)
                # API returns accumulated daily total.
                try:
                    current_prog_total = int(latest_prog.get('whol_smtn_ntby_tr_pbmn', 0))
                except: current_prog_total = 0
                
                # Retrieve Previous
                prev_prog_total = prev_prog_map.get(code)
                
                # Update Memory
                prev_prog_map[code] = current_prog_total

                # ---------------------------------------------------------
                # 📊 [Dashboard Data Collection] (All Candidiates)
                # ---------------------------------------------------------
                # Collect Program Net Buy for Dashboard Sorting
                # name, code, current_price, rate, current_prog_total (buy amount)
                stock['program_net_buy'] = current_prog_total # Unit: Million Won
                stock['code'] = code # Ensure code exists
                stock['name'] = name
                stock['price'] = current_price
                stock['chgrate'] = rate # Dashboard uses 'chgrate' or 'rate'

                # First run or Data missing -> Skip comparison, just store
                if prev_prog_total is None:
                    continue
                    
                # Calculate Delta (순매수 증가분)
                # 현재 누적 - 이전 누적
                prog_delta = current_prog_total - prev_prog_total
                
                # ✅ Dynamic Threshold Logic (Delta Based)
                # 30초(매 스캔) 동안 이만큼 늘어났으면 Trigger
                threshold = MIN_PROGRAM_DELTA_LARGE_CAP if code in LARGE_CAP_CODES else MIN_PROGRAM_DELTA_GENERAL
                
                # 조건: Delta가 양수(순매수 유입)이고 임계치 초과
                # [Update] Program OR Foreigner Trigger
                # if prog_delta < threshold: continue (Old)
                
                is_prog_trigger = (prog_delta >= threshold)
                
                # Check Foreigner Trigger later (after calc), for now verify Program first?
                # No, we need to calculate Foreigner Delta to check trigger.
                # So we proceed to calculate Foreigner Delta regardless of Program
                # But to save API calls, maybe we can optimize? 
                # Calculating Foreigner Delta from Map does NOT require extra API calls here (already fetched map).
                # So we continue to Step 2.
                pass 
                
                # However, if BOTH are weak, we skip early?
                # We don't know Foreign Delta yet for THIS stock specifically in this loop context?
                # Ah, 'frgn_map' is already populated in Pre-Fetch!
                # So we can look it up efficiently.
                
                # ... Proceed to Step 2 ...
 
                # ---------------------------------------------------------
                # 🕵️‍♂️ Step 2: 외국인 추정 (by 가집계 Map)
                # ---------------------------------------------------------
                frgn_net_buy_qty = frgn_map.get(code, 0)
                # 금액(원) 추산 = 순매수량 * 현재가
                current_frgn_total = int((frgn_net_buy_qty * current_price) / 1000000) # 백만

                # Retrieve Previous Foreign Total
                prev_frgn_total = prev_frgn_map.get(code)
                prev_frgn_map[code] = current_frgn_total
                
                # Calculate Foreign Delta
                # If no prev data, delta is 0
                frgn_delta = 0
                if prev_frgn_total is not None:
                    frgn_delta = current_frgn_total - prev_frgn_total
                
                # 외국인 Delta 계산
                # Threshold Check again with Foreigner
                is_frgn_trigger = (frgn_delta >= threshold)
                
                # [Final Trigger Check]
                if not (is_prog_trigger or is_frgn_trigger):
                    continue
                    
                # 쿨타임 체크 (30분)
                if time.time() - alert_history.get(code, 0) < 1800:
                    continue
                    
                # ---------------------------------------------------------
                # 🚨 Alert: 조건 만족!
                # ---------------------------------------------------------
                print(f"🐳 [K-Whale] {name}({code}) 포착! Program: +{prog_delta}백만(Total:{current_prog_total}), Foreign: +{frgn_delta}백만(Total:{current_frgn_total})")
                
                payload = {
                    "type": "K_WHALE_ALERT",
                    "market": "KR",
                    "code": code,
                    "name": name,
                    "price": current_price,
                    "rate": rate,
                    "program_delta": prog_delta,
                    "program_total": current_prog_total,
                    "foreign_delta": frgn_delta,
                    "foreign_total": current_frgn_total
                }
                
                # [Dashboard Only Mode] 개별 알림 중단
                # await redis_client.publish("whale_alert", ujson.dumps(payload))
                alert_history[code] = time.time()
                
                await asyncio.sleep(0.2) # API 부하 방지

            # ---------------------------------------------------------
            # 📊 [Dashboard Update] Every 5 minutes (300s)
            # ---------------------------------------------------------
            if time.time() - last_dashboard_update > 300:
                try:
                    # 1. Prepare Data
                    # A. Program Top 10 (from candidates)
                    # Filter only positive net buy
                    prog_list = [s for s in candidates if s.get('program_net_buy', 0) > 0]
                    prog_list.sort(key=lambda x: x.get('program_net_buy', 0), reverse=True)
                    prog_top_10 = prog_list[:10]
                    # Decorate Names with Amount
                    for p in prog_top_10:
                        amt = p.get('program_net_buy', 0) / 100_000_000 # Convert to Eok
                        p['name'] = f"{p['name']} (🤖+{amt:.1f}억)"

                    # B. Foreigner Top 10 (directly from frgn_est_list — has name/price/ntsl_qty)
                    frgn_list = []
                    for item in frgn_est_list:
                        try:
                            net_qty = int(item.get('glob_ntsl_qty', 0))
                            if net_qty == 0:
                                continue
                            f_code = item['stck_shrn_iscd']
                            name = item.get('hts_kor_isnm') or f_code
                            try:
                                price = int(str(item.get('stck_prpr', 0)).replace(',', ''))
                            except:
                                price = 0
                            chgrate = str(item.get('prdy_ctrt', '0')).strip()
                            amt_mil = (net_qty * price) / 1000000
                            frgn_list.append({
                                'name': name,
                                'code': f_code,
                                'price': price,
                                'chgrate': chgrate,
                                'foreign_net_buy': amt_mil,
                            })
                        except:
                            pass
                    frgn_list.sort(key=lambda x: abs(x.get('foreign_net_buy', 0)), reverse=True)
                    frgn_top_10 = frgn_list[:10]
                    for f in frgn_top_10:
                        amt_eok = f.get('foreign_net_buy', 0) / 100
                        label = f"👽+{amt_eok:.1f}억" if amt_eok >= 0 else f"👽{amt_eok:.1f}억"
                        f['name'] = f"{f['name']} ({label})"

                    # C. Volume Top 20
                    vol_top_20 = []
                    for v in c_vol[:20]:
                        v_copy = v.copy()
                        try:
                            vol_man = int(str(v.get('acml_vol', 0)).replace(',', '')) / 10000
                            vol_str = f"{vol_man:,.0f}만주"
                        except:
                            vol_str = ""
                        v_copy['name'] = f"{v['hts_kor_isnm']} ({vol_str})" if vol_str else v['hts_kor_isnm']
                        v_copy['code'] = v.get('mksc_shrn_iscd')
                        v_copy['chgrate'] = v.get('prdy_ctrt')
                        v_copy['price'] = v.get('stck_prpr')
                        vol_top_20.append(v_copy)

                    # D. Trading Value Top 20 (거래대금 기준 — 클라이언트 정렬)
                    c_val = await loop.run_in_executor(None, fetch_kr_trading_value_rank, access_token)
                    c_val_sorted = sorted(
                        c_val,
                        key=lambda x: int(str(x.get('acml_tr_pbmn', 0)).replace(',', '')),
                        reverse=True
                    )
                    val_top_20 = []
                    for v in c_val_sorted[:20]:
                        v_copy = v.copy()
                        v_copy['code'] = v.get('mksc_shrn_iscd', '')
                        v_copy['chgrate'] = v.get('prdy_ctrt', '0')
                        v_copy['price'] = v.get('stck_prpr', '0')
                        try:
                            amt_eok = int(str(v.get('acml_tr_pbmn', 0)).replace(',', '')) / 100_000_000
                            v_copy['name'] = f"{v.get('hts_kor_isnm', '')} ({amt_eok:,.0f}억)"
                        except:
                            v_copy['name'] = v.get('hts_kor_isnm', '')
                        val_top_20.append(v_copy)

                    # 2. Construct Display List with Headers
                    dashboard_list = []

                    dashboard_list.append({"name": "📈 거래량 Top 20", "is_header": True})
                    dashboard_list.extend(vol_top_20)

                    dashboard_list.append({"name": "💰 거래대금 Top 20", "is_header": True})
                    dashboard_list.extend(val_top_20)

                    # 3. Update Telegraph
                    url = update_telegraph_board(telegraph_config, "🇰🇷 국장 수급 주도주 현황 (Live)", dashboard_list, subtitle="실시간 거래량/수급 현황")

                    # 4. 웹 대시보드 D1 업데이트 (telegraph와 동시)
                    # 외국인/기관은 슬롯 캐시 사용 (FHPTJ04400000, 4회/일)
                    await push_to_dashboard(latest_frgn_top10, latest_inst_top10, vol_top_20)

                    if url:
                        # Save Config if Path changed (first run)
                        if not telegraph_config.get("path_saved"):
                             try:
                                 with open("telegraph_config_kr.json", "w") as f:
                                     ujson.dump(telegraph_config, f)
                                 telegraph_config["path_saved"] = True
                             except: pass
                        
                        # print(f"📊 [Dashboard] Updated: {url}")
                        
                        # [Notification] Scheduled Link Sending
                        # User Request: 09:15, 12:20, 15:10 KST
                        # Check Time
                        curr_hm = int(datetime.now().strftime("%H%M"))
                        
                        target_slot = None
                        # [Safe Guard] Window Expanded to 10 mins to prevent 'Interval Skip' (since Interval is 5 mins)
                        if 915 <= curr_hm < 925: target_slot = "OPEN"
                        elif 1220 <= curr_hm < 1230: target_slot = "MID"
                        elif 1510 <= curr_hm < 1520: target_slot = "CLOSE"
                        
                        if target_slot and (target_slot not in sent_slots):
                             payload = {
                                 "type": "WHALE_BOARD_UPDATE", # Reuse same type but w/ KR title
                                 "title": "🇰🇷 한국 증시 실시간 수급 현황판",
                                 "link": url
                             }
                             await redis_client.publish("news_alert", ujson.dumps(payload))
                             sent_slots.add(target_slot)
                             print(f"📡 [K-Dashboard] Link Sent ({target_slot}): {url}")
                        
                        
                    last_dashboard_update = time.time()

                except Exception as e:
                    print(f"⚠️ [Dashboard Error] {e}")

            await asyncio.sleep(SCAN_INTERVAL)

        except Exception as e:
            print(f"⚠️ [K-Whale Error] {e}")
            await asyncio.sleep(10)
