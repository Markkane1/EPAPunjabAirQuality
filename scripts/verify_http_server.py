import asyncio
import httpx
from httpx import ASGITransport
from src.api.main import create_application

async def main():
    app = create_application()
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Root /
        r_root = await client.get("/")
        assert r_root.status_code == 200
        assert "miniGridContainer" in r_root.text
        assert "panel-grid" in r_root.text
        assert "panel-lahore" in r_root.text
        assert "lahoreMapCanvas" in r_root.text
        print("[✓ PASS] GET /: HTTP 200, contains miniGridContainer, panel-grid, panel-lahore, lahoreMapCanvas")

        # 2. tokens.css
        r_css = await client.get("/static/css/tokens.css")
        assert r_css.status_code == 200
        assert ".minis" in r_css.text
        assert ".mbar" in r_css.text
        assert ".mticks" in r_css.text
        print("[✓ PASS] GET /static/css/tokens.css: HTTP 200, contains .minis, .mbar, .mticks")

        # 3. canvas.js
        r_canvas = await client.get("/static/js/canvas.js")
        assert r_canvas.status_code == 200
        assert "export const BP =" in r_canvas.text
        assert "export const aqiBar =" in r_canvas.text
        print("[✓ PASS] GET /static/js/canvas.js: HTTP 200, contains statutory BP and aqiBar")

        # 4. ui.js
        r_ui = await client.get("/static/js/ui.js")
        assert r_ui.status_code == 200
        assert "updateLegend(pollutantKey)" in r_ui.text
        assert "NOX" in r_ui.text
        print("[✓ PASS] GET /static/js/ui.js: HTTP 200, contains updated legend and NOX handling")

        # 5. app.js
        r_app = await client.get("/static/js/app.js")
        assert r_app.status_code == 200
        assert "initMinis()" in r_app.text
        assert "drawMinis()" in r_app.text
        assert "drawLahore()" in r_app.text
        print("[✓ PASS] GET /static/js/app.js: HTTP 200, contains initMinis, drawMinis, drawLahore")

        # 6. baseline_data.json
        r_base = await client.get("/static/data/baseline_data.json")
        assert r_base.status_code == 200
        print("[✓ PASS] GET /static/data/baseline_data.json: HTTP 200, size =", len(r_base.content))

    print(">>> ALL HTTP ENDPOINTS VERIFIED SUCCESSFULLY <<<")

asyncio.run(main())
