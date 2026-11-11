import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Emulate 714x1024 viewport
        page = await browser.new_page(viewport={"width": 714, "height": 1024})
        
        # Load local dashboard.html via file URL
        html_path = Path(r"c:\Users\Asif\Downloads\Punjab Air Quality\src\frontend\dashboard.html").resolve()
        await page.goto(f"file:///{html_path.as_posix()}")
        await page.wait_for_timeout(1000)
        
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
            ".instrument-card",
        ]
        
        for sel in elements:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                box = await loc.bounding_box()
                style = await loc.evaluate("el => ({ width: getComputedStyle(el).width, maxWidth: getComputedStyle(el).maxWidth, flex: getComputedStyle(el).flex, gridTemplateColumns: getComputedStyle(el).gridTemplateColumns })")
                print(f"{sel:25} Box: {box} | Computed: {style}")
            else:
                print(f"{sel:25} NOT FOUND")
                
        # Also inspect all instrument cards
        cards = await page.locator(".instrument-card").all()
        print(f"\nTotal instrument cards: {len(cards)}")
        for i, card in enumerate(cards):
            box = await card.bounding_box()
            h2 = await card.locator("h2").first.text_content() if await card.locator("h2").count() > 0 else "No H2"
            print(f"Card {i} ({h2}): width={box['width'] if box else 'None'}, left={box['x'] if box else 'None'}")
            
        # Take a screenshot to inspect
        ss_path = Path(r"c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m7_2\viewport_714_inspect.png")
        await page.screenshot(path=str(ss_path), full_page=True)
        print(f"\nScreenshot saved to {ss_path}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
