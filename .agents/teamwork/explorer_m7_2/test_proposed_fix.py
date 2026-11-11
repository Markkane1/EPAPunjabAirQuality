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
    uvicorn.run(app, host="127.0.0.1", port=8008, log_level="warning")

# The proposed CSS patch to test
PROPOSED_CSS = """
/* Fix Specificity Conflict: Ensure .console-body remains grid */
main.console-body {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) clamp(320px, 25vw, 360px);
  gap: 16px;
  align-items: start;
  width: 100%;
}

/* Tablet & Mobile Breakpoints */
@media (max-width: 1100px) {
  main.console-body {
    grid-template-columns: minmax(0, 1fr) !important;
    gap: 16px;
  }
  
  /* On tablet (768px - 1100px), arrange sidebar cards into a 2-column fluid grid */
  .zone-4-sidebar {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
    width: 100%;
  }
  
  /* Provincial summary spans both columns on tablet */
  .zone-4-sidebar > .instrument-card:first-child {
    grid-column: 1 / -1;
  }
}

@media (max-width: 767px) {
  /* On mobile (<768px), stack sidebar cards in a single fluid 100% column */
  .zone-4-sidebar {
    display: flex !important;
    flex-direction: column;
    gap: 14px;
    width: 100%;
  }
}

/* Eliminate Canvas Container Aspect Ratio Conflict & Overflow */
.viewport-canvas-container {
  position: relative;
  width: 100%;
  aspect-ratio: auto !important;
  height: clamp(380px, 55vh, 680px) !important;
  min-height: 0 !important;
  background: var(--geo-sea);
  overflow: hidden;
}

canvas.map-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100% !important;
  height: 100% !important;
  display: block;
}

/* Responsive Scrubber Deck */
.scrubber-deck {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 16px;
}

.scrubber-playback-group {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.range-scrubber-input {
  flex: 1 1 100% !important;
  min-width: 0 !important;
}

.scrubber-options-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* Mobile Header & Readout Protection */
@media (max-width: 767px) {
  .zone-1-header {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
    padding: 12px;
  }
  
  .brand-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  
  .header-status-group {
    flex-wrap: wrap;
    justify-content: space-between;
  }
  
  .clock-readout {
    width: auto !important;
    font-size: 11px !important;
    padding: 3px 6px !important;
  }
  
  .nav-tabs-group {
    overflow-x: auto;
    padding-bottom: 4px;
    -webkit-overflow-scrolling: touch;
  }
  
  .nav-tab-btn {
    white-space: nowrap;
    flex-shrink: 0;
  }
}

/* Ultra-mobile padding guard (<360px) */
@media (max-width: 360px) {
  body {
    padding: 6px 8px 24px !important;
  }
}
"""

async def test_proposed_fix():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("http://127.0.0.1:8008/")
        await page.wait_for_timeout(2000)
        
        # Inject proposed CSS
        await page.add_style_tag(content=PROPOSED_CSS)
        await page.wait_for_timeout(500)
        
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
        
        print("\n=== VERIFICATION OF PROPOSED RESPONSIVE CSS ===")
        for w, h, label in breakpoints:
            await page.set_viewport_size({"width": w, "height": h})
            await page.wait_for_timeout(300)
            
            data = await page.evaluate('''() => {
                const doc = document.documentElement;
                const body = document.body;
                const cb = document.querySelector('.console-body');
                const vp = document.querySelector('.zone-3-viewport');
                const sb = document.querySelector('.zone-4-sidebar');
                const card = document.querySelector('.zone-4-sidebar .instrument-card');
                
                return {
                    docScrollWidth: doc.scrollWidth,
                    viewportWidth: window.innerWidth,
                    hasOverflow: doc.scrollWidth > window.innerWidth,
                    overflowPx: Math.max(0, doc.scrollWidth - window.innerWidth),
                    cbGridCols: getComputedStyle(cb).gridTemplateColumns,
                    vpWidth: Math.round(parseFloat(getComputedStyle(vp).width)),
                    sbWidth: Math.round(parseFloat(getComputedStyle(sb).width)),
                    cardWidth: card ? Math.round(parseFloat(getComputedStyle(card).width)) : 0,
                    sbDisplay: getComputedStyle(sb).display,
                    sbCols: getComputedStyle(sb).gridTemplateColumns
                };
            }''')
            print(f"[{w:4}x{h:4}] {label:24} Overflow: {data['hasOverflow']} (+{data['overflowPx']}px) | VP: {data['vpWidth']:4}px | SB: {data['sbWidth']:4}px ({data['sbDisplay']}) | Card: {data['cardWidth']:4}px")
            
        # Take screenshot at 714x1024 to verify zero void
        await page.set_viewport_size({"width": 714, "height": 1024})
        await page.wait_for_timeout(500)
        ss_path = Path(r"c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m7_2\viewport_714_fixed.png")
        await page.screenshot(path=str(ss_path), full_page=True)
        print(f"\nScreenshot of fixed 714px layout saved to {ss_path}")
        
        await browser.close()

if __name__ == "__main__":
    server_process = Process(target=run_server)
    server_process.start()
    import time
    time.sleep(3)
    try:
        asyncio.run(test_proposed_fix())
    finally:
        server_process.terminate()
        server_process.join()
