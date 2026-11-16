const fs = require('fs');
const path = require('path');

const cssFile = fs.readdirSync('dist/assets').find(f => f.endsWith('.css'));
const cssContent = fs.readFileSync(path.join('dist/assets', cssFile), 'utf8');

// Find all class names in src/components, src/workstation, src/App.tsx
const jsxClasses = new Set();
function scan(dir) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) scan(full);
    else if (/\.(tsx|ts)$/.test(ent.name)) {
      const text = fs.readFileSync(full, 'utf8');
      const matches = text.matchAll(/className=(?:\{cn\()?["'`]([^"'`]+)["'`]/g);
      for (const m of matches) {
        m[1].split(/\s+/).forEach(cls => {
          if (cls && !cls.includes('$') && !cls.includes('{')) jsxClasses.add(cls);
        });
      }
    }
  }
}

scan('src/components');
scan('src/workstation');

console.log('Total unique class names in JSX:', jsxClasses.size);

let missing = 0;
let present = 0;
const missingClasses = [];
for (const cls of jsxClasses) {
  // Simple check if class selector exists in css
  const escaped = cls.replace(/[\[\]\(\)\.:\/#%]/g, '\\$&');
  const regex = new RegExp(`\\.${escaped}(?=[^\\w-]|\$)`);
  if (regex.test(cssContent)) {
    present++;
  } else {
    missing++;
    missingClasses.push(cls);
  }
}

console.log('Classes present in CSS:', present);
console.log('Classes MISSING from CSS:', missing);
console.log('Sample missing classes (first 30):', missingClasses.slice(0, 30));
