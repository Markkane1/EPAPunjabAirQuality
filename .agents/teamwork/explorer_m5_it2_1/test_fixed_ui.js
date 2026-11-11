function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

class MockUIController {
  constructor(app, dom) {
    this.app = app;
    this.dom = dom;
  }

  renderCsvQuarantineReport(result) {
    if (!this.dom.csvQuarantineArea) return;
    const records = result.quarantined_records || result.quarantine_records || [];
    const errors = result.errors || [];
    const validCount = result.valid_rows || 0;
    const quarantinedCount = result.quarantined_rows || records.length;
    const isTotalFailure = validCount === 0;

    let html = '';
    if (isTotalFailure) {
      html += `
        <div class="quarantine-banner banner-failed" style="margin-top: 10px; padding: 10px 12px; background: rgba(255, 107, 94, 0.15); border: 1px solid #ff6b5e; border-radius: 4px; color: #ff7a6b; font-size: 12px;">
          <div style="font-weight: 700; margin-bottom: 4px;">⚠️ CSV Validation Failed: 0 Valid Records Merged</div>
          <div>All ${quarantinedCount || result.total_rows || 0} row(s) were quarantined or invalid. Current telemetry dataset remains unchanged.</div>
        </div>
      `;
    } else {
      html += `
        <div class="quarantine-banner banner-warning" style="margin-top: 10px; padding: 10px 12px; background: rgba(237, 125, 49, 0.15); border: 1px solid #ED7D31; border-radius: 4px; color: #f09553; font-size: 12px;">
          <div style="font-weight: 700; margin-bottom: 4px;">ℹ️ Partial Ingestion: ${validCount} Records Merged</div>
          <div>${quarantinedCount} row(s) were quarantined due to schema or validation errors. Review the quarantine table below.</div>
        </div>
      `;
    }

    if (errors.length > 0) {
      html += `
        <div class="quarantine-errors" style="margin-top: 8px; padding: 8px 12px; background: rgba(0, 0, 0, 0.25); border: 1px solid var(--border-subtle); border-radius: 4px; font-size: 12px; color: var(--ink-primary);">
          <div style="font-weight: 600; color: #ff7a6b; margin-bottom: 4px;">Top-Level Schema Errors:</div>
          <ul style="margin: 0; padding-left: 18px;">
            ${errors.map(err => `<li>${escapeHtml(err)}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    if (records.length > 0) {
      html += `
        <div class="quarantine-table-wrap" style="margin-top: 10px; max-height: 240px; overflow-y: auto; overflow-x: auto; border: 1px solid var(--border-subtle); border-radius: 4px; background: var(--bg-canvas);">
          <table class="quarantine-table" style="width: 100%; border-collapse: collapse; font-size: 11px; text-align: left;">
            <thead>
              <tr style="position: sticky; top: 0; background: var(--bg-panel-elevated); z-index: 2; border-bottom: 1px solid var(--border-strong);">
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Row #</th>
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Station ID</th>
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Error Type</th>
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Error Message</th>
                <th style="padding: 6px 8px; font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; color: var(--ink-secondary); white-space: nowrap;">Raw Row Data</th>
              </tr>
            </thead>
            <tbody>
              ${records.map(rec => `
                <tr style="border-bottom: 1px solid var(--border-subtle);">
                  <td style="padding: 6px 8px; font-family: var(--font-mono); font-weight: 600; color: var(--accent); white-space: nowrap; text-align: center;">${rec.row_number ?? '-'}</td>
                  <td style="padding: 6px 8px; font-family: var(--font-mono); color: var(--ink-primary); white-space: nowrap;">${escapeHtml(rec.station_id || '-')}</td>
                  <td style="padding: 6px 8px; white-space: nowrap;"><span style="display: inline-block; padding: 2px 6px; font-family: var(--font-mono); font-size: 10px; font-weight: 600; color: #ff6b5e; background: rgba(255, 107, 94, 0.15); border-radius: 3px;">${escapeHtml(rec.error_type || 'VALIDATION_ERROR')}</span></td>
                  <td style="padding: 6px 8px; font-family: var(--font-body); font-size: 11px; color: var(--ink-primary); line-height: 1.3; max-width: 200px; word-break: break-word;">${escapeHtml(rec.error_message || 'Malformed record')}</td>
                  <td style="padding: 6px 8px; max-width: 220px;"><pre style="margin: 0; padding: 3px 5px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-secondary); background: rgba(0,0,0,0.3); border-radius: 2px; overflow-x: auto; white-space: pre-wrap; word-break: break-all;">${escapeHtml(JSON.stringify(rec.raw_record || {}))}</pre></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    this.dom.csvQuarantineArea.innerHTML = html;
  }

  async handleCsvUpload() {
    const file = this.dom.csvFileInput.files[0];
    if (!file) {
      alert('Please select a valid CSV file.');
      return;
    }

    try {
      this.dom.csvUploadSubmit.disabled = true;
      this.dom.csvUploadSubmit.textContent = 'Uploading & Validating...';

      const result = await this.app.apiClient.uploadCSV(file);
      const hasQuarantine = (result.quarantined_rows > 0) || (result.status === 'partial_quarantine') || (result.status === 'failed');
      const hasErrors = result.errors && result.errors.length > 0;
      const validCount = result.valid_rows || 0;

      if (hasQuarantine || hasErrors || validCount === 0) {
        // Render detailed quarantine inspector table & banner
        this.renderCsvQuarantineReport(result);

        if (validCount === 0) {
          alert(`CSV Ingestion Failed: 0 valid records merged. ${result.quarantined_rows || result.total_rows || 0} record(s) quarantined. Review quarantine details below.`);
          // Do NOT close modal, do NOT switch to user_csv
        } else {
          alert(`CSV Ingestion Warning: ${validCount} valid records merged into telemetry, but ${result.quarantined_rows} record(s) were quarantined. Review quarantine details below.`);
          // Valid records exist -> update app telemetry
          this.app.onCsvIngested(result);
        }
      } else {
        // Complete success with zero quarantined rows
        if (this.dom.csvQuarantineArea) this.dom.csvQuarantineArea.innerHTML = '';
        if (this.dom.csvModal) this.dom.csvModal.setAttribute('hidden', '');
        alert(`CSV Upload Success: ${validCount} valid records merged into telemetry.`);
        this.app.onCsvIngested(result);
      }
    } catch (err) {
      alert(`CSV Upload Failed: ${err.message}`);
      if (this.dom.csvQuarantineArea) {
        this.dom.csvQuarantineArea.innerHTML = `<div style="color: #ff6b5e; font-size: 12px; margin-top: 8px;"><b>Error:</b> ${escapeHtml(err.message)}</div>`;
      }
    } finally {
      this.dom.csvUploadSubmit.disabled = false;
      this.dom.csvUploadSubmit.textContent = 'Upload Dataset';
    }
  }
}

// Test Case 1: Total Failure (invalid_out_of_bounds.csv)
const quarantineDiv1 = { innerHTML: '' };
const modalDiv1 = { hidden: false, setAttribute(k, v) { this[k] = v; } };
const submitBtn1 = { disabled: false, textContent: '' };
const alerts1 = [];
global.alert = (msg) => alerts1.push(msg);

const mockApp1 = {
  apiClient: {
    uploadCSV: async (file) => ({
      status: 'failed',
      filename: file.name,
      total_rows: 6,
      valid_rows: 0,
      quarantined_rows: 6,
      quarantined_records: [
        { row_number: 2, station_id: 'PK_OOB_001', error_type: 'COORDINATES_OUT_OF_BOUNDS', error_message: 'Latitude 45.5 out of [27, 35]', raw_record: { lat: 45.5 } },
        { row_number: 3, station_id: 'PK_OOB_002', error_type: 'COORDINATES_OUT_OF_BOUNDS', error_message: 'Longitude 85.2 out of [69, 76]', raw_record: { lon: 85.2 } }
      ],
      errors: []
    })
  },
  onCsvIngested: (r) => { mockApp1.ingested = r; }
};

const ui1 = new MockUIController(mockApp1, {
  csvFileInput: { files: [{ name: 'invalid_out_of_bounds.csv' }] },
  csvUploadSubmit: submitBtn1,
  csvModal: modalDiv1,
  csvQuarantineArea: quarantineDiv1
});

ui1.handleCsvUpload().then(() => {
  console.log('--- Case 1 (Total Failure) ---');
  console.log('Alert text:', alerts1[0]);
  console.log('Modal dismissed (should be false):', modalDiv1.hidden === '');
  console.log('Quarantine area empty (should be false):', quarantineDiv1.innerHTML === '');
  console.log('Quarantine table contains Row #:', quarantineDiv1.innerHTML.includes('Row #'));
  console.log('Quarantine table contains Station ID:', quarantineDiv1.innerHTML.includes('Station ID'));
  console.log('Quarantine table contains Error Type:', quarantineDiv1.innerHTML.includes('Error Type'));
  console.log('Quarantine table contains Error Message:', quarantineDiv1.innerHTML.includes('Error Message'));
  console.log('Quarantine table contains Raw Row Data:', quarantineDiv1.innerHTML.includes('Raw Row Data'));
  console.log('App ingested (should be undefined):', mockApp1.ingested);

  // Test Case 2: Partial Quarantine (valid_rows > 0 and quarantined_rows > 0)
  const quarantineDiv2 = { innerHTML: '' };
  const modalDiv2 = { hidden: false, setAttribute(k, v) { this[k] = v; } };
  const alerts2 = [];
  global.alert = (msg) => alerts2.push(msg);

  const mockApp2 = {
    apiClient: {
      uploadCSV: async (file) => ({
        status: 'partial_quarantine',
        filename: file.name,
        total_rows: 10,
        valid_rows: 8,
        quarantined_rows: 2,
        quarantined_records: [
          { row_number: 4, station_id: 'STN_4', error_type: 'NEGATIVE_VAL', error_message: 'Negative value', raw_record: { v: -10 } }
        ],
        errors: []
      })
    },
    onCsvIngested: (r) => { mockApp2.ingested = r; }
  };

  const ui2 = new MockUIController(mockApp2, {
    csvFileInput: { files: [{ name: 'partial.csv' }] },
    csvUploadSubmit: { disabled: false, textContent: '' },
    csvModal: modalDiv2,
    csvQuarantineArea: quarantineDiv2
  });

  ui2.handleCsvUpload().then(() => {
    console.log('--- Case 2 (Partial Quarantine) ---');
    console.log('Alert text:', alerts2[0]);
    console.log('Modal dismissed (should be false):', modalDiv2.hidden === '');
    console.log('Quarantine area empty (should be false):', quarantineDiv2.innerHTML === '');
    console.log('App ingested (should be defined):', mockApp2.ingested ? mockApp2.ingested.status : null);

    // Test Case 3: Complete Success (valid_rows > 0 and quarantined_rows === 0)
    const quarantineDiv3 = { innerHTML: 'old errors' };
    const modalDiv3 = { hidden: false, setAttribute(k, v) { this[k] = v; } };
    const alerts3 = [];
    global.alert = (msg) => alerts3.push(msg);

    const mockApp3 = {
      apiClient: {
        uploadCSV: async (file) => ({
          status: 'success',
          filename: file.name,
          total_rows: 10,
          valid_rows: 10,
          quarantined_rows: 0,
          quarantined_records: [],
          errors: []
        })
      },
      onCsvIngested: (r) => { mockApp3.ingested = r; }
    };

    const ui3 = new MockUIController(mockApp3, {
      csvFileInput: { files: [{ name: 'valid.csv' }] },
      csvUploadSubmit: { disabled: false, textContent: '' },
      csvModal: modalDiv3,
      csvQuarantineArea: quarantineDiv3
    });

    ui3.handleCsvUpload().then(() => {
      console.log('--- Case 3 (Complete Success) ---');
      console.log('Alert text:', alerts3[0]);
      console.log('Modal dismissed (should be true):', modalDiv3.hidden === '');
      console.log('Quarantine area cleared (should be true):', quarantineDiv3.innerHTML === '');
      console.log('App ingested (should be defined):', mockApp3.ingested ? mockApp3.ingested.status : null);
    });
  });
});
