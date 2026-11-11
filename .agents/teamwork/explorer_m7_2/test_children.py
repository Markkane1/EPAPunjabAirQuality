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
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="warning")

async def test_children():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://127.0.0.1:8003/")
        await page.wait_for_timeout(2000)
        
        sidebar = page.locator(".zone-4-sidebar")
        print("Sidebar computed:", await sidebar.evaluate("el => ({ width: getComputedStyle(el).width, alignSelf: getComputedStyle(el).alignSelf, flex: getComputedStyle(el).flex, maxWidth: getComputedStyle(el).maxWidth })"))
        
        cards = await sidebar.locator(".instrument-card").all()
        for i, card in enumerate(cards):
            info = await card.evaluate("el => ({ tag: el.tagName, id: el.id, className: el.className, width: getComputedStyle(el).width, box: el.getBoundingClientRect() })")
            print(f"Card {i}: {info}")
            
        await browser.close()

if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    import time
    time.sleep(3)
    try:
        asyncio.run(test_children())
    finally:
        server_process.terminate()
        server_process.join()
