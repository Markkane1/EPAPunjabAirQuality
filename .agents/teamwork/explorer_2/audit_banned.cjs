const fs = require('fs');
const path = require('path');

const emojiRegex = /[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F000}-\u{1F02F}\u{1F0A0}-\u{1F0FF}\u{1F100}-\u{1F64F}\u{1F680}-\u{1F6FF}]/u;

function scanDir(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const ent of entries) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      if (ent.name !== 'node_modules' && ent.name !== '.git' && ent.name !== 'dist' && ent.name !== '__pycache__') {
        scanDir(full);
      }
    } else if (/\.(tsx?|css|html|json)$/.test(ent.name) && !ent.name.endsWith('.d.ts')) {
      const text = fs.readFileSync(full, 'utf8');
      const lines = text.split('\n');
      lines.forEach((line, idx) => {
        if (emojiRegex.test(line)) {
          console.log(`EMOJI: ${full}:${idx + 1}: ${line.trim()}`);
        }
        if (/backdrop-filter|backdrop-blur/i.test(line) && !line.includes('none !important')) {
          console.log(`BACKDROP: ${full}:${idx + 1}: ${line.trim()}`);
        }
        if (/(?<!-)box-shadow|drop-shadow|shadow-[a-z0-9]+/i.test(line) && !line.includes('none !important') && !line.includes('shadow-none')) {
          console.log(`SHADOW: ${full}:${idx + 1}: ${line.trim()}`);
        }
        if (/\bpitch\s*:\s*[1-9]/i.test(line) || /\bmaxPitch\s*:\s*[1-9]/i.test(line) || /\bbearing\s*:\s*[1-9]/i.test(line)) {
          console.log(`3D_PITCH: ${full}:${idx + 1}: ${line.trim()}`);
        }
      });
    }
  }
}

scanDir('src');
