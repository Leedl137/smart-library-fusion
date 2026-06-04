import asyncio
from playwright.async_api import async_playwright

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Screenshot 1: Vue Frontend
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            await page.goto("http://127.0.0.1:8080", timeout=30000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path="scripts/screenshot_vue.png", full_page=True)
            print("Vue frontend screenshot saved: scripts/screenshot_vue.png")
        except Exception as e:
            print(f"Vue frontend screenshot failed: {e}")
        await page.close()
        
        # Screenshot 2: Streamlit Dashboard
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            await page.goto("http://localhost:8501", timeout=30000)
            await page.wait_for_timeout(5000)
            await page.screenshot(path="scripts/screenshot_streamlit.png", full_page=True)
            print("Streamlit screenshot saved: scripts/screenshot_streamlit.png")
        except Exception as e:
            print(f"Streamlit screenshot failed: {e}")
        await page.close()
        
        # Screenshot 3: API Docs
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            await page.goto("http://127.0.0.1:8080/docs", timeout=30000)
            await page.wait_for_timeout(3000)
            await page.screenshot(path="scripts/screenshot_docs.png", full_page=True)
            print("API docs screenshot saved: scripts/screenshot_docs.png")
        except Exception as e:
            print(f"API docs screenshot failed: {e}")
        await page.close()
        
        await browser.close()

asyncio.run(take_screenshots())
