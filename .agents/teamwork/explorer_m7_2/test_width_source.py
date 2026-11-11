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
    uvicorn.run(app, host="127.0.0.1", port=8004, log_level="warning")

async def test_width_source():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://127.0.0.1:8004/")
        await page.wait_for_timeout(2000)
        
        # Test why sidebar is 427.609px
        res = await page.evaluate('''() => {
            const sidebar = document.querySelector('.zone-4-sidebar');
            const all = sidebar.querySelectorAll('*');
            const widths = [];
            for (const el of all) {
                const rect = el.getBoundingClientRect();
                const cs = window.getComputedStyle(el);
                if (rect.width > 350 || el.scrollWidth > 350) {
                    widths.push({
                        tag: el.tagName,
                        cls: el.className,
                        id: el.id,
                        rectWidth: rect.width,
                        scrollWidth: el.scrollWidth,
                        text: (el.innerText || '').slice(0, 30)
                    });
                }
            }
            return widths;
        }''')
        for r in res[:20]:
            print(r)
        await browser.close()

if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    import time
    time.sleep(3)
    try:
        asyncio.run(test_width_source())
    finally:
        server_process.terminate()
        server_process.join()
