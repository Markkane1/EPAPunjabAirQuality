import re
import sys

def srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def relative_luminance(hex_code):
    h = hex_code.lstrip('#')
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return 0.2126 * srgb_to_linear(r) + 0.7152 * srgb_to_linear(g) + 0.0722 * srgb_to_linear(b)

def contrast_ratio(hex1, hex2):
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    l_max = max(l1, l2)
    l_min = min(l1, l2)
    return (l_max + 0.05) / (l_min + 0.05)

with open('src/styles/tokens.css', 'r', encoding='utf-8') as f:
    css_content = f.read()

# Separate root and light mode
root_match = re.search(r':root\s*\{(.*?)\}', css_content, re.DOTALL)
light_match = re.search(r'\[data-theme=["\']?light["\']?\].*?\{(.*?)\}', css_content, re.DOTALL)

def extract_vars(block):
    vars_dict = {}
    for line in block.splitlines():
        line = line.strip()
        m = re.match(r'--(bg-[a-z\-]+|ink-[a-z\-]+|accent)\s*:\s*(#[0-9a-fA-F]{6})', line)
        if m:
            vars_dict[m.group(1)] = m.group(2)
    return vars_dict

dark_vars = extract_vars(root_match.group(1))
light_vars = extract_vars(light_match.group(1))

print('Dark mode extracted tokens:', dark_vars)
print('Light mode extracted tokens:', light_vars)

dark_surfaces = [k for k in dark_vars if k.startswith('bg-') and k != 'bg-overlay']
dark_inks = [k for k in dark_vars if k.startswith('ink-') or k == 'accent']

light_surfaces = [k for k in light_vars if k.startswith('bg-') and k != 'bg-overlay']
light_inks = [k for k in light_vars if k.startswith('ink-') or k == 'accent']

failures = []
results = []

print('\n--- DARK MODE AUDIT ---')
for s in dark_surfaces:
    for i in dark_inks:
        if i == 'ink-inverse':
            continue # ink-inverse is meant for light chips
        cr = contrast_ratio(dark_vars[i], dark_vars[s])
        passed = cr >= 7.0
        results.append(('dark', i, s, dark_vars[i], dark_vars[s], cr, passed))
        if not passed:
            failures.append(('dark', i, s, dark_vars[i], dark_vars[s], cr))
        print(f'{i} ({dark_vars[i]}) on {s} ({dark_vars[s]}): {cr:.2f}:1 -> {"PASS" if passed else "FAIL"}')

print('\n--- LIGHT MODE AUDIT ---')
for s in light_surfaces:
    for i in light_inks:
        if i == 'ink-inverse':
            continue # ink-inverse is meant for dark chips
        cr = contrast_ratio(light_vars[i], light_vars[s])
        passed = cr >= 7.0
        results.append(('light', i, s, light_vars[i], light_vars[s], cr, passed))
        if not passed:
            failures.append(('light', i, s, light_vars[i], light_vars[s], cr))
        print(f'{i} ({light_vars[i]}) on {s} ({light_vars[s]}): {cr:.2f}:1 -> {"PASS" if passed else "FAIL"}')

print('\n--- PEPC PALETTE INK AUDIT ---')
pepc_pairs = [
    ('pepc-good', '#00B050', '#000000'),
    ('pepc-satisfactory', '#92D050', '#000000'),
    ('pepc-moderate', '#FFFF00', '#000000'),
    ('pepc-unhealthy-sensitive', '#ED7D31', '#000000'),
    ('pepc-very-unhealthy', '#7030A0', '#ffffff'),
    ('pepc-emergency', '#4A154B', '#ffffff')
]
for name, bg, ink in pepc_pairs:
    cr = contrast_ratio(ink, bg)
    print(f'{name} ink ({ink}) on {bg}: {cr:.2f}:1 -> {"PASS" if cr >= 7.0 else "FAIL"}')
    if cr < 7.0:
        failures.append(('pepc', name, ink, bg, cr))

if failures:
    print(f'\nFAILURES DETECTED: {len(failures)}')
    for f in failures:
        print(f)
    sys.exit(1)
else:
    print(f'\nALL {len(results)} TEXT/SURFACE PAIRS EXCEED 7.0:1 (WCAG 2.1 AAA COMPLIANT)!')
