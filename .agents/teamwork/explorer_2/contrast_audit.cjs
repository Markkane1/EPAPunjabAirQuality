function parseHex(hex) {
  hex = hex.trim().replace('#', '');
  if (hex.length === 3) {
    hex = hex.split('').map(c => c + c).join('');
  }
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return [r, g, b];
}

function relLuminance([r, g, b]) {
  const [sR, sG, sB] = [r, g, b].map(v => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * sR + 0.7152 * sG + 0.0722 * sB;
}

function contrastRatio(hex1, hex2) {
  const l1 = relLuminance(parseHex(hex1));
  const l2 = relLuminance(parseHex(hex2));
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

// Dark Mode Tokens from tokens.css
const darkSurfaces = {
  '--bg-canvas': '#0f1716',
  '--bg-panel': '#152120',
  '--bg-panel-elevated': '#1c2b2a',
  '--bg-dock': '#131e1d',
  '--bg-inspector': '#152120',
  '--bg-command-bar': '#111a19',
  '--bg-scrubber': '#111a19'
};

const darkInks = {
  '--ink-primary': '#e3ece9',
  '--ink-secondary': '#c0cfcb',
  '--ink-tertiary': '#a8bbb5',
  '--accent': '#5fc4c4'
};

console.log('=== DARK MODE CONTRAST AUDIT (Target >= 7.0:1) ===');
for (const [inkName, inkHex] of Object.entries(darkInks)) {
  for (const [surfName, surfHex] of Object.entries(darkSurfaces)) {
    const cr = contrastRatio(inkHex, surfHex);
    const pass = cr >= 7.0;
    console.log(`${pass ? 'PASS' : 'FAIL'} | ${inkName} (${inkHex}) vs ${surfName} (${surfHex}): ${cr.toFixed(2)}:1`);
  }
}

// Light Mode Tokens from tokens.css
const lightSurfaces = {
  '--bg-canvas': '#eef1ef',
  '--bg-panel': '#fbfcfb',
  '--bg-panel-elevated': '#ffffff',
  '--bg-dock': '#e8ecea',
  '--bg-inspector': '#fbfcfb',
  '--bg-command-bar': '#f4f6f5',
  '--bg-scrubber': '#f4f6f5'
};

const lightInks = {
  '--ink-primary': '#17221f',
  '--ink-secondary': '#34423e',
  '--ink-tertiary': '#3d4c48',
  '--accent': '#084e51'
};

console.log('\n=== LIGHT MODE CONTRAST AUDIT (Target >= 7.0:1) ===');
for (const [inkName, inkHex] of Object.entries(lightInks)) {
  for (const [surfName, surfHex] of Object.entries(lightSurfaces)) {
    const cr = contrastRatio(inkHex, surfHex);
    const pass = cr >= 7.0;
    console.log(`${pass ? 'PASS' : 'FAIL'} | ${inkName} (${inkHex}) vs ${surfName} (${surfHex}): ${cr.toFixed(2)}:1`);
  }
}

// PEPC Palettes and their designated inks
const pepc = [
  { tier: 'Good', bg: '#00B050', ink: '#000000' },
  { tier: 'Satisfactory', bg: '#92D050', ink: '#000000' },
  { tier: 'Moderate', bg: '#FFFF00', ink: '#000000' },
  { tier: 'Unhealthy (Sens)', bg: '#ED7D31', ink: '#000000' },
  { tier: 'Unhealthy', bg: '#FF0000', ink: '#ffffff' },
  { tier: 'Very Unhealthy', bg: '#7030A0', ink: '#ffffff' },
  { tier: 'Hazardous', bg: '#C00000', ink: '#ffffff' },
  { tier: 'Emergency', bg: '#4A154B', ink: '#ffffff' },
];

console.log('\n=== PEPC STATUTORY INK ON CHIP CONTRAST AUDIT ===');
for (const p of pepc) {
  const cr = contrastRatio(p.ink, p.bg);
  const passAAA = cr >= 7.0;
  const passAA = cr >= 4.5;
  console.log(`${passAAA ? 'PASS AAA' : passAA ? 'PASS AA' : 'FAIL'} | ${p.tier} (${p.ink} on ${p.bg}): ${cr.toFixed(2)}:1`);
}
