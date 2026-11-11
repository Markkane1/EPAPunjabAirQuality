// Test prototype of quarantine table rendering logic and watchdog simulation
function renderQuarantineTable(records, result) {
  let html = '<div class="quarantine-inspector">';
  html += '<table><thead><tr><th>Row</th><th>Station</th><th>Error Type</th><th>Message</th></tr></thead><tbody>';
  records.forEach(r => {
    html += `<tr><td>${r.row_number}</td><td>${r.station_id || '-'}</td><td>${r.error_type}</td><td>${r.error_message}</td></tr>`;
  });
  html += '</tbody></table></div>';
  return html;
}

const mockRecords = [
  { row_number: 2, station_id: 'STN-1', error_type: 'COORDINATES_OUT_OF_BOUNDS', error_message: 'Lat 45.5 out of [27, 35]' },
  { row_number: 3, station_id: 'STN-2', error_type: 'COORDINATES_OUT_OF_BOUNDS', error_message: 'Lon 85.2 out of [69, 76]' }
];

const html = renderQuarantineTable(mockRecords, { status: 'failed' });
console.log('HTML length:', html.length);
console.log('Contains table:', html.includes('<table'));
console.log('Contains Row header:', html.includes('<th>Row</th>'));
console.log('Contains Error Type:', html.includes('COORDINATES_OUT_OF_BOUNDS'));

// Test Jitter calculation
const delays = [];
for (let i = 0; i < 50; i++) {
  const base = Math.min(30000, 2000 * Math.pow(1.5, 1)); // 3000
  const timeout = base * (0.5 + Math.random() * 0.5);
  delays.push(timeout);
}
const minDelay = Math.min(...delays);
const maxDelay = Math.max(...delays);
const avgDelay = delays.reduce((a, b) => a + b, 0) / delays.length;
const variance = delays.reduce((a, b) => a + Math.pow(b - avgDelay, 2), 0) / delays.length;
console.log('Jitter bounds:', minDelay.toFixed(1), 'to', maxDelay.toFixed(1));
console.log('Variance:', variance.toFixed(1));
