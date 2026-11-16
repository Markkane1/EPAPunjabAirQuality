"""
Automated Modernized Single-File Offline HTML Bundler (GAP-EXT-01).
Compiles the modernized React Web GIS analytical workstation into a single,
self-contained, zero-dependency offline HTML file for air-gapped emergency deployment.
Produces: dist/Punjab_Air_Quality_Offline_Dashboard.html
"""
import argparse
from pathlib import Path
import re
import sys


def bundle_offline_dashboard(
    dist_dir: Path = None,
    output_path: Path = None,
) -> Path:
    project_root = Path(__file__).resolve().parent.parent
    dist = dist_dir or (project_root / "dist")
    assets_dir = dist / "assets"
    
    html_entry = dist / "workstation.html"
    if not html_entry.exists():
        html_entry = dist / "index.html"
    if not html_entry.exists():
        raise FileNotFoundError(f"Neither workstation.html nor index.html found in {dist}")

    out_file = output_path or (dist / "Punjab_Air_Quality_Offline_Dashboard.html")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    html_content = html_entry.read_text(encoding="utf-8")

    # 1. Inline CSS stylesheets
    def replace_css(match):
        css_href = match.group(1).lstrip("/")
        css_file = dist / css_href
        if not css_file.exists():
            css_file = assets_dir / Path(css_href).name
        if css_file.exists():
            css_text = css_file.read_text(encoding="utf-8")
            return f"<style>/* Inlined from {css_file.name} */\n{css_text}</style>"
        return match.group(0)

    html_content = re.sub(
        r'<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"[^>]*>',
        replace_css,
        html_content,
        flags=re.IGNORECASE,
    )

    # 2. Remove modulepreload links since code will be inlined
    html_content = re.sub(
        r'<link[^>]*rel="modulepreload"[^>]*>',
        "",
        html_content,
        flags=re.IGNORECASE,
    )

    # 3. Inline JavaScript modules in correct dependency order
    # React vendor -> MapLibre vendor -> DeckGL vendor -> Main index chunk
    js_files_in_order = []
    if assets_dir.exists():
        # Identify vendor files
        vendors = sorted([f for f in assets_dir.glob("*-vendor-*.js")])
        index_chunks = sorted([f for f in assets_dir.glob("index-*.js")])
        # Sort react first, then maplibre, then deckgl
        react_v = [f for f in vendors if "react" in f.name.lower()]
        map_v = [f for f in vendors if "map" in f.name.lower()]
        deck_v = [f for f in vendors if "deck" in f.name.lower()]
        other_v = [f for f in vendors if f not in react_v and f not in map_v and f not in deck_v]
        js_files_in_order = react_v + map_v + deck_v + other_v + index_chunks

    inlined_scripts = []
    for js_path in js_files_in_order:
        if js_path.is_file() and not js_path.name.endswith(".map"):
            js_code = js_path.read_text(encoding="utf-8")
            inlined_scripts.append(f"<script type=\"module\">/* Inlined from {js_path.name} */\n{js_code}\n</script>")

    # Replace external script tag or inject into body
    if re.search(r'<script[^>]*type="module"[^>]*src="[^"]*"[^>]*></script>', html_content):
        # Replace the first module script tag with all inlined scripts
        all_scripts_str = "\n".join(inlined_scripts)
        html_content = re.sub(
            r'<script[^>]*type="module"[^>]*src="[^"]*"[^>]*></script>',
            lambda _: all_scripts_str,
            html_content,
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        # Append before </body>
        all_scripts_str = "\n".join(inlined_scripts)
        html_content = html_content.replace("</body>", f"{all_scripts_str}\n</body>")

    out_file.write_text(html_content, encoding="utf-8")
    return out_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bundle Modernized Workstation into Standalone Single-File HTML")
    parser.add_argument("--out", default=None, help="Output single-file HTML path")
    args = parser.parse_args()

    out_p = Path(args.out) if args.out else None
    res = bundle_offline_dashboard(output_path=out_p)
    print(f"[SUCCESS] Standalone Single-File Workstation bundled: {res} ({res.stat().st_size / 1024:.1f} KB)")
