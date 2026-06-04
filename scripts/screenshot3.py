import asyncio
from playwright.async_api import async_playwright

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Streamlit Dashboard
        try:
            await page.goto("http://localhost:8501", timeout=60000)
            await page.wait_for_timeout(10000)
            await page.screenshot(path="scripts/screenshot_streamlit_final.png", full_page=True)
            print("Streamlit screenshot saved")
        except Exception as e:
            print(f"Streamlit screenshot failed: {e}")
        
        await browser.close()

asyncio.run(take_screenshots())
