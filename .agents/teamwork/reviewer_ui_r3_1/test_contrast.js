// Color contrast calculation according to WCAG 2.1
function sRGBtoLin(c) {
  c = c / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}
function relLuminance(r, g, b) {
  return 0.2126 * sRGBtoLin(r) + 0.7152 * sRGBtoLin(g) + 0.0722 * sRGBtoLin(b);
}
function contrastRatio(l1, l2) {
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

// Background is --bg-panel (#111615)
const bgBase = [0x11, 0x16, 0x15];
const whiteLum = relLuminance(255, 255, 255);

const PEPC_COLORS = [
  { tier: 'Good', rgb: [0, 176, 80] },
  { tier: 'Satisfactory', rgb: [146, 208, 80] },
  { tier: 'Moderate', rgb: [255, 192, 0] },
  { tier: 'Unhealthy', rgb: [255, 0, 0] },
  { tier: 'Very Unhealthy', rgb: [112, 48, 160] },
  { tier: 'Severe', rgb: [192, 0, 0] },
  { tier: 'Hazardous', rgb: [128, 0, 0] },
];

console.log('=== WCAG AAA Contrast Evaluation (Threshold >= 7.0:1) ===');
let allPass = true;
for (const { tier, rgb } of PEPC_COLORS) {
  // Composite rgba(rgb, 0.18) over bgBase
  const alpha = 0.18;
  const compR = Math.round(rgb[0] * alpha + bgBase[0] * (1 - alpha));
  const compG = Math.round(rgb[1] * alpha + bgBase[1] * (1 - alpha));
  const compB = Math.round(rgb[2] * alpha + bgBase[2] * (1 - alpha));

  const compLum = relLuminance(compR, compG, compB);
  const cr = contrastRatio(whiteLum, compLum);
  const passAAA = cr >= 7.0;
  if (!passAAA) allPass = false;
  console.log(`Tier ${tier.padEnd(16)}: Comp RGB(${compR},${compG},${compB}) -> Contrast: ${cr.toFixed(2)}:1 [AAA: ${passAAA ? 'PASS' : 'FAIL'}]`);
}
console.log('All PEPC tiers pass WCAG AAA:', allPass);
