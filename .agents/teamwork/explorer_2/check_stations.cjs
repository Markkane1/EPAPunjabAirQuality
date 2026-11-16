const fs = require('fs');
const stations = JSON.parse(fs.readFileSync('data/baseline/stations.json', 'utf8'));
const lahore = stations.filter(s => (s.district || '').toLowerCase() === 'lahore' || s.isLahore);
console.log('Total stations:', stations.length);
console.log('Lahore stations:', lahore.length);
console.log('Fixed:', stations.filter(s => !s.mobile).length);
console.log('Mobile:', stations.filter(s => s.mobile).length);
