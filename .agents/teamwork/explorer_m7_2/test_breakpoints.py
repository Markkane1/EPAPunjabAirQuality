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
    uvicorn.run(app, host="127.0.0.1", port=8006, log_level="warning")

async def test_breakpoints():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://127.0.0.1:8006/")
        await page.wait_for_timeout(2000)
        
        # Test with .deep-dive-panel removed to test true layout intended behavior
        await page.evaluate("() => document.querySelector('.console-body').classList.remove('deep-dive-panel')")
        
        breakpoints = [
            (1600, 900, "Large Desktop"),
            (1366, 768, "Standard Desktop"),
            (1200, 800, "Small Desktop"),
            (1024, 768, "Tablet Landscape"),
            (768, 1024, "Tablet Portrait"),
            (714, 1024, "User Screenshot Viewport"),
            (480, 800, "Large Mobile"),
            (360, 640, "Standard Mobile"),
            (320, 568, "Minimum Mobile")
        ]
        
        print("\n=== RESPONSIVE BREAKPOINT AUDIT ===")
        for w, h, label in breakpoints:
            await page.set_viewport_size({"width": w, "height": h})
            await page.wait_for_timeout(300)
            
            data = await page.evaluate('''() => {
                const doc = document.documentElement;
                const body = document.body;
                const app = document.querySelector('.app-container');
                const cb = document.querySelector('.console-body');
                const vp = document.querySelector('.zone-3-viewport');
                const sb = document.querySelector('.zone-4-sidebar');
                const card = document.querySelector('.zone-4-sidebar .instrument-card');
                const canvas = document.querySelector('#mainMapCanvas');
                const header = document.querySelector('.zone-1-header');
                
                return {
                    docScrollWidth: doc.scrollWidth,
                    viewportWidth: window.innerWidth,
                    hasOverflow: doc.scrollWidth > window.innerWidth,
                    overflowPx: doc.scrollWidth - window.innerWidth,
                    cbGridCols: getComputedStyle(cb).gridTemplateColumns,
                    vpWidth: getComputedStyle(vp).width,
                    sbWidth: getComputedStyle(sb).width,
                    cardWidth: card ? getComputedStyle(card).width : 'none',
                    headerHeight: getComputedStyle(header).height,
                    canvasWidth: canvas ? getComputedStyle(canvas).width : 'none',
                    canvasHeight: canvas ? getComputedStyle(canvas).height : 'none',
                };
            }''')
            print(f"[{w}x{h}] {label:24} Overflow: {data['hasOverflow']} (+{data['overflowPx']}px) | GridCols: {data['cbGridCols']} | SB: {data['sbWidth']} | Card: {data['cardWidth']}")
            
        await browser.close()

if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    import time
    time.sleep(3)
    try:
        asyncio.run(test_breakpoints())
    finally:
        server_process.terminate()
        server_process.join()
