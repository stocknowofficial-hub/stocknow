import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from watcher.tasks.report_watcher import check_blackrock, check_kiwoom

async def test_scrapers():
    print("🧪 [Test] Running Real Scrapers manually...")
    
    print("\n---------------------------------------------------")
    print("🏛️ [1] BlackRock Scraper Test")
    print("---------------------------------------------------")
    await check_blackrock()
    
    print("\n---------------------------------------------------")
    print("🇰🇷 [2] Kiwoom Scraper Test (Selenium)")
    print("---------------------------------------------------")
    await check_kiwoom()

    print("\n---------------------------------------------------")
    print("✅ Test Completed.")

if __name__ == "__main__":
    asyncio.run(test_scrapers())
