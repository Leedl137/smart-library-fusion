import asyncio
from playwright.async_api import async_playwright

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Screenshot: Streamlit Dashboard (wait longer)
        try:
            await page.goto("http://localhost:8501", timeout=60000)
            await page.wait_for_timeout(8000)
            await page.screenshot(path="scripts/screenshot_streamlit2.png", full_page=True)
            print("Streamlit screenshot saved")
        except Exception as e:
            print(f"Streamlit screenshot failed: {e}")
        
        # Screenshot: Vue Advanced Mining tab
        try:
            await page.goto("http://127.0.0.1:8080", timeout=30000)
            await page.wait_for_timeout(3000)
            # Click on "复杂行为挖掘" tab
            await page.click('text=复杂行为挖掘')
            await page.wait_for_timeout(2000)
            await page.screenshot(path="scripts/screenshot_vue_advanced.png", full_page=True)
            print("Vue Advanced screenshot saved")
        except Exception as e:
            print(f"Vue Advanced screenshot failed: {e}")
        
        # Screenshot: Vue Chat tab
        try:
            await page.goto("http://127.0.0.1:8080", timeout=30000)
            await page.wait_for_timeout(3000)
            await page.click('text=智能问答')
            await page.wait_for_timeout(2000)
            await page.screenshot(path="scripts/screenshot_vue_chat.png", full_page=True)
            print("Vue Chat screenshot saved")
        except Exception as e:
            print(f"Vue Chat screenshot failed: {e}")
        
        await browser.close()

asyncio.run(take_screenshots())
