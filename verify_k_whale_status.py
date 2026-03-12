
import asyncio
import os
import sys
import time
from common.config import settings
from watcher.utils.definitions import (
    fetch_kr_volume_rank,
    fetch_kr_bulk_rank,
    fetch_kr_program_trend,
    fetch_kr_investor_trend
)
from watcher.kis_auth import get_access_token

# Thresholds from whale_watcher_kr.py
MIN_PROGRAM_NET_BUY = 1000000000  # 1 Billion Won

async def verify_status():
    print("🔑 Access Token 발급 중...")
    token = get_access_token()
    if not token:
        print("❌ 토큰 발급 실패")
        return

    print("\n📊 [Candidates Scanning]...")
    
    # 1. Fetch Candidates
    print("   👉 Fetching Volume Rank...")
    c_vol = fetch_kr_volume_rank(token)
    print(f"      -> Found {len(c_vol)} items.")
    
    print("   👉 Fetching Bulk Rank (Big Buy Orders)...")
    c_bulk = fetch_kr_bulk_rank(token)
    print(f"      -> Found {len(c_bulk)} items.")

    # Merge
    candidates = c_vol + c_bulk
    seen = set()
    unique_candidates = []
    for c in candidates:
        code = c.get('mksc_shrn_iscd')
        if code and code not in seen:
            unique_candidates.append(c)
            seen.add(code)
    
    print(f"   ✅ Merged Unique Candidates: {len(unique_candidates)} items.\n")
    
    if not unique_candidates:
        print("⚠️ No candidates found. Aborting.")
        return

    print(f"🔎 [Deep Analysis] Checking Top 10 Candidates...")
    print(f"{'Code':<8} | {'Name':<12} | {'Price':<10} | {'Prog Net Buy(100M)':<18} | {'Frgn Net Buy(100M)':<18} | {'Status'}")
    print("-" * 100)

    # Check Top 10 only for verify
    for stock in unique_candidates[:10]:
        code = stock.get('mksc_shrn_iscd')
        name = stock.get('hts_kor_isnm')
        price = stock.get('stck_prpr')
        
        # 1. Program Trend
        p_data = fetch_kr_program_trend(token, code)
        prog_net_buy = 0
        if p_data:
            latest = p_data[0]
            try:
                prog_net_buy = int(latest.get('whol_smtn_ntby_tr_pbmn', 0))
            except: pass
            
        # 2. Investor Trend
        i_data = fetch_kr_investor_trend(token, code)
        frgn_net_buy = 0
        if i_data:
            try:
                frgn_net_buy = int(i_data.get('frgn_ntby_tr_pbmn', 0))
            except: pass
            
        # Check Alert Condition
        # Condition: Prog >= 1 Billion AND Frgn >= 0 (strictly based on recent fix: Frgn >= 0 ?? No, logic is "if Frgn < 0 continue")
        # So Alert if Prog >= 1B AND Frgn >= 0. (Wait, logic says 'if frgn < 0: continue'. So it allows 0.)
        
        is_alert = False
        if prog_net_buy >= MIN_PROGRAM_NET_BUY:
            if frgn_net_buy >= 0: # Note: Logic is 'if frgn < 0 continue', so >= 0 is pass.
                is_alert = True
        
        # Format for display (Unit: 100 Million Won for easier reading)
        p_buy_fmt = f"{prog_net_buy / 100000000:.1f}억"
        f_buy_fmt = f"{frgn_net_buy / 100000000:.1f}억"
        
        status = "💤 Pass"
        if is_alert:
            status = "🔥 ALERT!"
        elif prog_net_buy >= MIN_PROGRAM_NET_BUY:
             status = "⚠️ Prog Only (Frgn Sold)"
            
        print(f"{code:<8} | {name:<12} | {price:<10} | {p_buy_fmt:<18} | {f_buy_fmt:<18} | {status}")
        
        # Avoid API Rate Limit during loop
        # time.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(verify_status())
