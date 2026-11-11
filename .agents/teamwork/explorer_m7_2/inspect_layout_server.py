import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, r"c:\Users\Asif\Downloads\Punjab Air Quality")

import uvicorn
from multiprocessing import Process
from playwright.async_api import async_playwright

def run_server():
    os.chdir(r"c:\Users\Asif\Downloads\Punjab Air Quality")
    import sys
    sys.path.insert(0, r"c:\Users\Asif\Downloads\Punjab Air Quality")
    from src.api.main import app
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Test 714x1024 viewport
        page = await browser.new_page(viewport={"width": 714, "height": 1024})
        
        await page.goto("http://127.0.0.1:8001/")
        await page.wait_for_timeout(3000)
        
        # Measure bounding rects
        elements = [
            "body",
            ".app-container",
            ".zone-1-header",
            ".zone-2-pollutants",
            ".console-body",
            ".zone-3-viewport",
            ".viewport-canvas-container",
            "#mainMapCanvas",
            ".scrubber-deck",
            ".zone-4-sidebar",
        ]
        
        print("\n--- ELEMENT BOUNDS & STYLES AT 714px VIEWPORT ---")
        for sel in elements:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                box = await loc.bounding_box()
                style = await loc.evaluate("el => ({ width: getComputedStyle(el).width, maxWidth: getComputedStyle(el).maxWidth, minWidth: getComputedStyle(el).minWidth, gridTemplateColumns: getComputedStyle(el).gridTemplateColumns, display: getComputedStyle(el).display })")
                print(f"{sel:27} Box: {box} | Computed: {style}")
            else:
                print(f"{sel:27} NOT FOUND")
                
        # Also inspect all instrument cards
        cards = await page.locator(".zone-4-sidebar .instrument-card").all()
        print(f"\nTotal visible sidebar cards: {len(cards)}")
        for i, card in enumerate(cards):
            box = await card.bounding_box()
            h2 = await card.locator("h2").first.text_content() if await card.locator("h2").count() > 0 else "No H2"
            print(f"Card {i} ({h2}): width={box['width'] if box else 'None'}, left={box['x'] if box else 'None'}")
            
        # Take a screenshot to inspect
        ss_path = Path(r"c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m7_2\viewport_714_loaded.png")
        await page.screenshot(path=str(ss_path), full_page=True)
        print(f"\nScreenshot saved to {ss_path}")
        
        await browser.close()

if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    import time
    time.sleep(3)
    try:
        asyncio.run(inspect())
    finally:
        server_process.terminate()
        server_process.join()
