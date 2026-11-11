function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

const mockReport = {
  status: 'failed',
  filename: 'invalid_out_of_bounds.csv',
  total_rows: 6,
  valid_rows: 0,
  quarantined_rows: 6,
  quarantined_records: [
    { row_number: 2, station_id: 'PK_OOB_001', error_type: 'COORDINATES_OUT_OF_BOUNDS', error_message: 'Latitude 45.5 out of [27, 35]', raw_record: { timestamp: '2026-11-10T12:00:00Z', station_id: 'PK_OOB_001', latitude: '45.5000' } },
    { row_number: 3, station_id: 'PK_OOB_002', error_type: 'COORDINATES_OUT_OF_BOUNDS', error_message: 'Longitude 85.2 out of [69, 76]', raw_record: { timestamp: '2026-11-10T12:00:00Z', station_id: 'PK_OOB_002', longitude: '85.2000' } }
  ],
  errors: []
};

function renderQuarantine(result) {
  const records = result.quarantined_records || result.quarantine_records || [];
  const errors = result.errors || [];
  const validCount = result.valid_rows || 0;
  const quarantinedCount = result.quarantined_rows || records.length;
  const isTotalFailure = validCount === 0;

  let html = '';
  if (isTotalFailure) {
    html += '<div class="quarantine-banner banner-failed">Validation Failed: 0 Valid Records Merged</div>';
  }
  if (records.length > 0) {
    html += '<table class="quarantine-table"><thead><tr><th>Row #</th><th>Station ID</th><th>Error Type</th><th>Error Message</th><th>Raw Row Data</th></tr></thead><tbody>';
    for (const rec of records) {
      html += `<tr><td>${rec.row_number}</td><td>${rec.station_id}</td><td>${rec.error_type}</td><td>${rec.error_message}</td><td>${JSON.stringify(rec.raw_record)}</td></tr>`;
    }
    html += '</tbody></table>';
  }
  return html;
}

const out = renderQuarantine(mockReport);
console.log('Generated HTML length:', out.length);
console.log('Contains Row #:', out.includes('Row #'));
console.log('Contains Station ID:', out.includes('Station ID'));
console.log('Contains Error Type:', out.includes('Error Type'));
console.log('Contains Error Message:', out.includes('Error Message'));
console.log('Contains Raw Row Data:', out.includes('Raw Row Data'));
