"""
Empirical Verification & Adversarial Stress Harness for Milestone 1
Adversarial Challenger: challenger_m1_1

Validates:
1. W3C WCAG 2.1 relative luminance and contrast ratio calculations.
2. Full matrix of 56 text/surface combinations (28 dark + 28 light).
3. Statutory PEPC color contrast analysis for chip indicators.
4. Banned dependency audit in package.json, package-lock.json, and node_modules.
"""

import os
import re
import sys
import json

def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def relative_luminance(hex_str):
    h = hex_str.strip().lstrip('#')
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)

def contrast_ratio(hex1, hex2):
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def test_contrast():
    print("================================================================================")
    print(" 1. EMPIRICAL WCAG 2.1 AAA CONTRAST RATIO VERIFICATION (src/styles/tokens.css)")
    print("================================================================================")
    
    tokens_path = os.path.join('src', 'styles', 'tokens.css')
    if not os.path.exists(tokens_path):
        print(f"ERROR: {tokens_path} not found!")
        return False

    with open(tokens_path, 'r', encoding='utf-8') as f:
        css_content = f.read()

    root_match = re.search(r':root\s*\{(.*?)\n\}', css_content, re.DOTALL)
    light_match = re.search(r'\[data-theme=["\']light["\']\][^{]*\{(.*?)\n\}', css_content, re.DOTALL)

    def parse_vars(block):
        vars_dict = {}
        for line in block.splitlines():
            line = line.strip()
            m = re.match(r'--([a-zA-Z0-9_-]+)\s*:\s*(#[0-9a-fA-F]{6})', line)
            if m:
                vars_dict['--' + m.group(1)] = m.group(2)
        return vars_dict

    dark_vars = parse_vars(root_match.group(1)) if root_match else {}
    light_vars = parse_vars(light_match.group(1)) if light_match else {}

    surfaces = ['--bg-canvas', '--bg-panel', '--bg-panel-elevated', '--bg-dock', '--bg-inspector', '--bg-command-bar', '--bg-scrubber']
    inks = ['--ink-primary', '--ink-secondary', '--ink-tertiary', '--accent']

    all_passed = True

    print("\n--- DARK MODE MATRIX (Required: CR >= 7.000:1) ---")
    dark_results = []
    for s in surfaces:
        s_hex = dark_vars.get(s)
        s_lum = relative_luminance(s_hex)
        for i in inks:
            i_hex = dark_vars.get(i)
            i_lum = relative_luminance(i_hex)
            cr = contrast_ratio(s_hex, i_hex)
            passed = cr >= 7.0000
            if not passed:
                all_passed = False
            dark_results.append((s, s_hex, s_lum, i, i_hex, i_lum, cr, passed))
            status = "PASS AAA" if passed else "FAIL AAA"
            print(f"  {s:<20} ({s_hex}, L={s_lum:.5f}) vs {i:<16} ({i_hex}, L={i_lum:.5f}) -> CR: {cr:6.3f}:1 -> {status}")

    print("\n--- LIGHT MODE MATRIX (Required: CR >= 7.000:1) ---")
    light_results = []
    for s in surfaces:
        s_hex = light_vars.get(s)
        s_lum = relative_luminance(s_hex)
        for i in inks:
            i_hex = light_vars.get(i)
            i_lum = relative_luminance(i_hex)
            cr = contrast_ratio(s_hex, i_hex)
            passed = cr >= 7.0000
            if not passed:
                all_passed = False
            light_results.append((s, s_hex, s_lum, i, i_hex, i_lum, cr, passed))
            status = "PASS AAA" if passed else "FAIL AAA"
            print(f"  {s:<20} ({s_hex}, L={s_lum:.5f}) vs {i:<16} ({i_hex}, L={i_lum:.5f}) -> CR: {cr:6.3f}:1 -> {status}")

    dark_min = min(dark_results, key=lambda x: x[6])
    light_min = min(light_results, key=lambda x: x[6])

    print("\n--- MATRIX SUMMARY ---")
    print(f"  Total surface/text pairs tested: {len(dark_results) + len(light_results)} (28 dark + 28 light)")
    print(f"  Dark mode minimum CR:  {dark_min[6]:.4f}:1 ({dark_min[0]} vs {dark_min[3]})")
    print(f"  Light mode minimum CR: {light_min[6]:.4f}:1 ({light_min[0]} vs {light_min[3]})")
    print(f"  All 56 pairs meet WCAG 2.1 AAA (>= 7.000:1): {all_passed}")

    print("\n--- ADVERSARIAL STRESS TEST: STATUTORY PEPC COLOR CHIPS ---")
    pepc_chips = [
        ('pepc-good', '#00B050', '#000000'),
        ('pepc-satisfactory', '#92D050', '#000000'),
        ('pepc-moderate', '#FFFF00', '#000000'),
        ('pepc-unhealthy-sensitive', '#ED7D31', '#000000'),
        ('pepc-unhealthy', '#FF0000', '#ffffff'),
        ('pepc-very-unhealthy', '#7030A0', '#ffffff'),
        ('pepc-hazardous', '#C00000', '#ffffff'),
        ('pepc-emergency', '#4A154B', '#ffffff')
    ]
    for name, bg, ink in pepc_chips:
        cr = contrast_ratio(bg, ink)
        note = "PASS AAA" if cr >= 7.0 else ("PASS AA (4.5:1)" if cr >= 4.5 else "BELOW 4.5:1 (Statutory Color Guard)")
        print(f"  {name:<26} bg={bg} ink={ink} -> CR: {cr:6.3f}:1 -> {note}")

    return all_passed

def test_banned_dependencies():
    print("\n================================================================================")
    print(" 2. BANNED DEPENDENCY AUDIT (tailwindcss, lucide-react, heroicons, feather-icons)")
    print("================================================================================")
    
    banned = ['tailwindcss', 'lucide-react', 'heroicons', 'feather-icons', '@heroicons/react', 'feather-icons-react']
    found = []

    # Check package.json
    if os.path.exists('package.json'):
        with open('package.json', 'r') as f:
            pkg = json.load(f)
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            for b in banned:
                if b in deps:
                    found.append(f"package.json: {b}")

    # Check package-lock.json
    if os.path.exists('package-lock.json'):
        with open('package-lock.json', 'r') as f:
            lock = json.load(f)
            packages = lock.get('packages', {})
            for p in packages.keys():
                for b in banned:
                    if b in p:
                        found.append(f"package-lock.json: {p}")

    # Check node_modules directories
    if os.path.exists('node_modules'):
        for root, dirs, files in os.walk('node_modules'):
            for d in dirs:
                for b in ['tailwind', 'lucide', 'heroicon', 'feather']:
                    if b in d.lower():
                        found.append(f"node_modules dir: {os.path.join(root, d)}")

    print(f"  Banned items detected: {len(found)}")
    if found:
        for f in found:
            print(f"    FOUND: {f}")
        return False
    else:
        print("  VERIFIED: Zero banned dependencies present in package.json, package-lock.json, or node_modules.")
        return True

def main():
    c_ok = test_contrast()
    d_ok = test_banned_dependencies()
    print("\n================================================================================")
    if c_ok and d_ok:
        print(" FINAL CHALLENGE RESULT: ALL EMPIRICAL CHECKS PASSED")
        print("================================================================================")
        sys.exit(0)
    else:
        print(" FINAL CHALLENGE RESULT: EMPIRICAL CHECKS FAILED")
        print("================================================================================")
        sys.exit(1)

if __name__ == '__main__':
    main()
