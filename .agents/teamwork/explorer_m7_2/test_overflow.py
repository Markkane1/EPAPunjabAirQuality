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
    uvicorn.run(app, host="127.0.0.1", port=8007, log_level="warning")

async def test_overflow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 360, "height": 640})
        await page.goto("http://127.0.0.1:8007/")
        await page.wait_for_timeout(2000)
        
        overflowing = await page.evaluate('''() => {
            const vpW = window.innerWidth;
            const elements = document.querySelectorAll('*');
            const res = [];
            for (const el of elements) {
                const rect = el.getBoundingClientRect();
                if (rect.right > vpW + 1) {
                    res.push({
                        tag: el.tagName,
                        cls: el.className,
                        id: el.id,
                        right: rect.right,
                        width: rect.width,
                        excess: rect.right - vpW
                    });
                }
            }
            return res;
        }''')
        print(f"Overflowing elements at 360px ({len(overflowing)} items):")
        for item in overflowing[:15]:
            print(item)
            
        await browser.close()

if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    import time
    time.sleep(3)
    try:
        asyncio.run(test_overflow())
    finally:
        server_process.terminate()
        server_process.join()
