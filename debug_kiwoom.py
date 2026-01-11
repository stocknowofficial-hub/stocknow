import requests
from bs4 import BeautifulSoup
import time

def verify_user_url():
    # User Provided URL
    target_url = "https://finance.naver.com/research/invest_list.naver?searchType=keyword&keyword=kiwoom+Weekly&brokerCode=39&writeFromDate=&writeToDate=&x=56&y=19"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"🔎 Testing URL: {target_url}")
    try:
        resp = requests.get(target_url, headers=headers)
        soup = BeautifulSoup(resp.content.decode('euc-kr', 'replace'), 'html.parser')
        
        # Naver Research Table logic
        rows = soup.select("table.type_1 tr")
        print(f"   Found {len(rows)} rows in table.")
        
        for row in rows:
            tds = row.find_all('td')
            if len(tds) < 3: continue 
            
            title_link = row.find('a', href=True)
            if not title_link: continue
            
            title_text = title_link.text.strip()
            date_text = tds[4].text.strip() if len(tds) > 4 else "Unknown Date"
            
            print(f"   📄 [Candidate] {title_text} ({date_text})")
            
            # Check for PDF
            detail_url = "https://finance.naver.com/research/" + title_link['href']
            print(f"      🔗 Detail: {detail_url}")
            
            detail_resp = requests.get(detail_url, headers=headers)
            detail_soup = BeautifulSoup(detail_resp.content.decode('euc-kr', 'replace'), 'html.parser')
            
            pdf_a = None
            for a in detail_soup.find_all('a', href=True):
                if a['href'].lower().endswith('.pdf'):
                    pdf_a = a['href']
                    break
            
            if pdf_a:
                print(f"      ✅ PDF Found: {pdf_a}")
                # Try downloading first 1KB to verify it exists
                pdf_head = requests.get(pdf_a, headers=headers, stream=True)
                if pdf_head.status_code == 200:
                    print("      💾 Download Check: OK (200)")
                    return # Success
                else:
                    print(f"      ❌ Download Check: Failed ({pdf_head.status_code})")
            else:
                print("      ⚠️ No PDF found in detail page.")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_user_url()
