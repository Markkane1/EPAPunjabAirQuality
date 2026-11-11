import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0, r"c:\Users\Asif\Downloads\Punjab Air Quality")
import uvicorn
from multiprocessing import Process
from playwright.async_api import async_playwright

def run_server():
    os.chdir(r"c:\Users\Asif\Downloads\Punjab Air Quality")
    import sys
    sys.path.insert(0, r"c:\Users\Asif\Downloads\Punjab Air Quality")
    from src.api.main import app
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")

async def test_desktop():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://127.0.0.1:8002/")
        await page.wait_for_timeout(2000)
        
        display = await page.locator(".console-body").evaluate("el => getComputedStyle(el).display")
        grid_cols = await page.locator(".console-body").evaluate("el => getComputedStyle(el).gridTemplateColumns")
        flex_dir = await page.locator(".console-body").evaluate("el => getComputedStyle(el).flexDirection")
        vp_box = await page.locator(".zone-3-viewport").bounding_box()
        sb_box = await page.locator(".zone-4-sidebar").bounding_box()
        
        print(f"Desktop 1440px: display={display}, gridCols={grid_cols}, flexDir={flex_dir}")
        print(f"Viewport box: {vp_box}")
        print(f"Sidebar box: {sb_box}")
        await browser.close()

if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    import time
    time.sleep(3)
    try:
        asyncio.run(test_desktop())
    finally:
        server_process.terminate()
        server_process.join()
