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
    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="warning")

async def test_grid_behavior():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Test 714px
        page = await browser.new_page(viewport={"width": 714, "height": 1024})
        await page.goto("http://127.0.0.1:8005/")
        await page.wait_for_timeout(2000)
        
        # Test 1: As is (with .deep-dive-panel overriding)
        res1 = await page.evaluate('''() => {
            const cb = document.querySelector('.console-body');
            const sb = document.querySelector('.zone-4-sidebar');
            const card = document.querySelector('.zone-4-sidebar .instrument-card');
            return {
                cbDisplay: getComputedStyle(cb).display,
                sbWidth: getComputedStyle(sb).width,
                cardWidth: getComputedStyle(card).width,
            };
        }''')
        print("As-is at 714px:", res1)
        
        # Test 2: If we remove .deep-dive-panel from #panel-console
        res2 = await page.evaluate('''() => {
            const cb = document.querySelector('.console-body');
            cb.classList.remove('deep-dive-panel');
            const sb = document.querySelector('.zone-4-sidebar');
            const card = document.querySelector('.zone-4-sidebar .instrument-card');
            return {
                cbDisplay: getComputedStyle(cb).display,
                cbGridCols: getComputedStyle(cb).gridTemplateColumns,
                sbWidth: getComputedStyle(sb).width,
                cardWidth: getComputedStyle(card).width,
            };
        }''')
        print("Without deep-dive-panel at 714px:", res2)
        
        # Test 3: At Desktop 1440px without deep-dive-panel
        await page.set_viewport_size({"width": 1440, "height": 900})
        await page.wait_for_timeout(500)
        res3 = await page.evaluate('''() => {
            const cb = document.querySelector('.console-body');
            const sb = document.querySelector('.zone-4-sidebar');
            const vp = document.querySelector('.zone-3-viewport');
            return {
                cbDisplay: getComputedStyle(cb).display,
                cbGridCols: getComputedStyle(cb).gridTemplateColumns,
                vpWidth: getComputedStyle(vp).width,
                sbWidth: getComputedStyle(sb).width,
            };
        }''')
        print("Without deep-dive-panel at 1440px:", res3)
        
        await browser.close()

if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    import time
    time.sleep(3)
    try:
        asyncio.run(test_grid_behavior())
    finally:
        server_process.terminate()
        server_process.join()
