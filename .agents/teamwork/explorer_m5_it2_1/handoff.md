# Investigation & Remediation Blueprint Report: Defect D1 (CSV Quarantine Inspector UI Feedback)

**Author:** `explorer_m5_it2_1` (Technical Explorer, Milestone M5 Iteration 2)  
**Parent Orchestrator ID:** `dfe9ab49-5b73-4c71-b636-dccdcc9080ee`  
**Working Directory:** `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_m5_it2_1`  
**Target Files Analyzed:**
- `src/frontend/static/js/ui.js` (lines 610–638, lines 20–27, 92–106)
- `src/frontend/static/js/api.js` (lines 182–198)
- `src/frontend/static/js/app.js` (lines 408–417)
- `src/frontend/dashboard.html` (lines 320–338)
- `src/frontend/static/css/tokens.css` (lines 166–211)
- `src/api/routes/ingest.py` (lines 11–52)
- `src/api/schemas/ingest.py` (lines 6–27)
- `src/services/ingestion_service.py` (lines 60–90, 112–130)
- `tests/integration/test_m5_resilience_challenge.py` (lines 300–422)

---

## 1. Observation

### 1.1 Direct Inspection of Source Code

#### 1. In `src/frontend/static/js/ui.js:613-637`:
```javascript
613:   async handleCsvUpload() {
614:     const file = this.dom.csvFileInput.files[0];
615:     if (!file) {
616:       alert('Please select a valid CSV file.');
617:       return;
618:     }
619: 
620:     try {
621:       this.dom.csvUploadSubmit.disabled = true;
622:       this.dom.csvUploadSubmit.textContent = 'Uploading & Validating...';
623: 
624:       const result = await this.app.apiClient.uploadCSV(file);
625:       alert(`CSV Upload Success: ${result.valid_rows} valid records merged into telemetry.`);
626:       if (this.dom.csvModal) this.dom.csvModal.setAttribute('hidden', '');
627:       this.app.onCsvIngested(result);
628:     } catch (err) {
629:       alert(`CSV Upload Failed: ${err.message}`);
630:       if (this.dom.csvQuarantineArea) {
631:         this.dom.csvQuarantineArea.innerHTML = `<div style="color: #ff5e5e; font-size: 12px; margin-top: 8px;"><b>Error:</b> ${err.message}</div>`;
632:       }
633:     } finally {
634:       this.dom.csvUploadSubmit.disabled = false;
635:       this.dom.csvUploadSubmit.textContent = 'Upload Dataset';
636:     }
637:   }
```

#### 2. In `src/frontend/static/js/api.js:182-198`:
```javascript
182:   async uploadCSV(file, allowMissingCoords = false) {
183:     const formData = new FormData();
184:     formData.append('file', file);
185:     formData.append('allow_missing_coords', allowMissingCoords ? 'true' : 'false');
186: 
187:     const resp = await fetch(`${this.baseUrl}/api/v1/ingest/csv`, {
188:       method: 'POST',
189:       body: formData,
190:     });
191: 
192:     const result = await resp.json();
193:     if (!resp.ok) {
194:       throw new Error(result.detail || result.message || 'CSV Ingestion Failed');
195:     }
196:     this.mode = 'user_csv';
197:     return result;
198:   }
```

#### 3. In `src/frontend/static/js/app.js:413-416`:
```javascript
413:   onCsvIngested(result) {
414:     console.log('CSV Ingestion Complete:', result);
415:     this.ui.updateLiveStatus('user_csv');
416:   }
```

#### 4. In `src/api/schemas/ingest.py:6-27` and `src/services/ingestion_service.py:73-86, 112-125`:
When an uploaded CSV dataset fails validation (e.g. `invalid_out_of_bounds.csv` where all 6 rows exceed bounding limits, or `invalid_missing_columns.csv` where required headers are absent), the backend API returns **HTTP 200 OK** with `CSVIngestResponse`:
```python
class CSVIngestResponse(BaseModel):
    status: str  # "success" | "partial_quarantine" | "failed"
    filename: str
    total_rows: int
    valid_rows: int
    quarantined_rows: int
    merged_observations_count: int = 0
    errors: List[str] = []
    quarantine_records: Optional[List[QuarantineDetail]] = None
    quarantined_records: Optional[List[QuarantineDetail]] = None
```
Each `QuarantineDetail` entry contains:
- `row_number: int` (1-based row number in CSV)
- `station_id: Optional[str]`
- `error_type: str` (e.g. `COORDINATES_OUT_OF_BOUNDS`, `VALUE_OUT_OF_RANGE`, etc.)
- `error_message: str` (e.g. `Latitude 45.5 out of [27, 35]`)
- `raw_record: Dict[str, Any]` (key-value dictionary of raw CSV row tokens)

### 1.2 Empirical Failure Reproduction

Running a headless Node.js simulation matching `test_csv_client_side_quarantine_inspector_defect_empirically`:
```bash
node -e "
import { UIController } from './src/frontend/static/js/ui.js';
const qDiv = { innerHTML: '' };
const mDiv = { hidden: false, setAttribute(k, v) { this[k] = v; } };
const mockApp = {
  apiClient: {
    uploadCSV: async () => ({
      status: 'failed',
      valid_rows: 0,
      quarantined_rows: 6,
      quarantined_records: [{ row_number: 2, error_type: 'OOB', error_message: 'Out of bounds', raw_record: { row: 2 } }]
    })
  },
  onCsvIngested: (r) => { mockApp.status = r.status; }
};
global.alert = (msg) => console.log('ALERT:', msg);
const ui = Object.create(UIController.prototype);
ui.app = mockApp;
ui.dom = { csvFileInput: { files: [{ name: 'test.csv' }] }, csvUploadSubmit: {}, csvModal: mDiv, csvQuarantineArea: qDiv };
ui.handleCsvUpload().then(() => {
  console.log('Modal hidden:', mDiv.hidden === '');
  console.log('Quarantine area empty:', qDiv.innerHTML === '');
  console.log('App status:', mockApp.status);
});
"
```

**Verbatim Console Output:**
```
ALERT: CSV Upload Success: 0 valid records merged into telemetry.
Modal hidden: true
Quarantine area empty: true
App status: failed
```

### 1.3 Four Specific Breakages Identified
1. **Misleading Alert (False Success)**: `ui.js:625` unconditionally pops an alert saying `"CSV Upload Success: 0 valid records merged into telemetry."` despite zero valid records and a failed status.
2. **Premature Modal Dismissal**: `ui.js:626` executes `this.dom.csvModal.setAttribute('hidden', '')`, immediately closing the modal dialog and preventing the operator from seeing any error context.
3. **Quarantine Inspector Suppression**: `#csvQuarantineArea` remains completely empty (`innerHTML == ""`). The line-by-line validation errors generated by the backend validation engine are never rendered.
4. **Invalid System State Transition**: `api.js:196` and `app.js:415` unconditionally set `mode = 'user_csv'` and switch the header badge to `USER CSV DATASET`, falsely signaling that custom data is active when 0 rows were merged.

---

## 2. Logic Chain

```
[Observation 1.1: Backend Protocol for CSV Ingestion]
  └──> Ingestion endpoint returns HTTP 200 OK with CSVIngestResponse JSON.
  └──> If validation fails: status="failed", valid_rows=0, quarantined_rows=N, quarantined_records=[...].
  └──> If partial validation: status="partial_quarantine", valid_rows=M, quarantined_rows=N, quarantined_records=[...].

[Observation 1.1 & 1.2: Current Client Processing]
  └──> fetch() succeeds -> resp.ok is TRUE -> no exception thrown.
  └──> api.js unconditionally executes: this.mode = 'user_csv'.
  └──> ui.js:625 unconditionally alerts "CSV Upload Success: 0 valid records...".
  └──> ui.js:626 unconditionally closes the modal dialog.
  └──> ui.js never touches #csvQuarantineArea on 200 OK responses.
  └──> app.js unconditionally updates live status badge to "USER CSV DATASET".

[Logic Deduction: What Remediation Must Accomplish]
  └──> 1. In api.js:uploadCSV():
         Only set this.mode = 'user_csv' IF result.valid_rows > 0.
         Return the full result payload so the UI controller can inspect report details.
  └──> 2. In ui.js:handleCsvUpload():
         Inspect result.valid_rows, result.quarantined_rows, result.status, and result.errors.
         Case A (Total Failure, valid_rows === 0):
           - Do NOT close modal.
           - Alert operator of validation failure.
           - Render high-visibility banner + scrollable table in #csvQuarantineArea.
           - Do NOT switch app mode to 'user_csv'.
         Case B (Partial Quarantine, valid_rows > 0 && quarantined_rows > 0):
           - Do NOT close modal (allow inspection of quarantined records).
           - Alert operator with warning (M records merged, N quarantined).
           - Render high-visibility warning banner + scrollable table in #csvQuarantineArea.
           - Invoke this.app.onCsvIngested(result) to merge valid telemetry.
         Case C (Complete Success, valid_rows > 0 && quarantined_rows === 0):
           - Clear #csvQuarantineArea.
           - Close modal (hidden='').
           - Alert operator of complete success.
           - Invoke this.app.onCsvIngested(result).
  └──> 3. In app.js:onCsvIngested():
         Add defensive guard checking if result.valid_rows > 0 before updating status badge.
```

---

## 3. Caveats

1. **Test Suite Invalidation Notice**: Challenger 2's test `test_csv_client_side_quarantine_inspector_defect_empirically` in `tests/integration/test_m5_resilience_challenge.py:338-422` currently asserts that the defect *exists* (`assert "CSV Upload Success: 0 valid records" in data["alert"]`, `assert data["modalDismissed"] is True`, `assert data["quarantineAreaEmpty"] is True`). Once the fix is applied, that assertion will fail unless the test assertions are inverted to verify the remediated behavior (`modalDismissed is False`, `quarantineAreaEmpty is False`, `alert contains "CSV Ingestion Failed"`).
2. **Top-Level Header Errors vs Row Errors**: When a file is missing required columns (e.g. `invalid_missing_columns.csv`), `result.quarantined_records` is empty, but `result.errors` contains `["Missing required header columns: latitude, longitude"]`. The quarantine renderer must handle both `quarantined_records` (row-level table) and `errors` (schema-level error box).
3. **Modal Sizing**: The default `.modal-box` in `tokens.css` has `max-width: 580px`. A 5-column table (Row #, Station ID, Error Type, Error Message, Raw Row Data) is much more legible if `.modal-box` is expanded to `max-width: 760px` or if `#csvModal .modal-box` has `max-width: 760px; width: 92%;`.

---

## 4. Conclusion & Precise Remediation Blueprint

### 4.1 Component Blueprint 1: `src/frontend/static/js/api.js`
In `api.js::uploadCSV(file, allowMissingCoords = false)`:
- Do not set `this.mode = 'user_csv'` unconditionally.
- Only assign `this.mode = 'user_csv'` if `result.valid_rows > 0`.
- Return `result` to caller.

```javascript
  async uploadCSV(file, allowMissingCoords = false) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('allow_missing_coords', allowMissingCoords ? 'true' : 'false');

    const resp = await fetch(`${this.baseUrl}/api/v1/ingest/csv`, {
      method: 'POST',
      body: formData,
    });

    const result = await resp.json();
    if (!resp.ok) {
      throw new Error(result.detail || result.message || 'CSV Ingestion Failed');
    }
    
    // Only transition client mode to 'user_csv' if valid observations were ingested
    if (result.valid_rows > 0) {
      this.mode = 'user_csv';
    }
    return result;
  }
```

---

### 4.2 Component Blueprint 2: `src/frontend/static/js/app.js`
In `app.js::onCsvIngested(result)`:
- Add defensive guard to ensure that if `result.valid_rows === 0` or `result.status === 'failed'`, the app state does NOT switch to `user_csv`.

```javascript
  onCsvIngested(result) {
    if (!result || result.valid_rows === 0 || result.status === 'failed') {
      console.warn('Ignoring CSV ingestion with 0 valid records:', result);
      return;
    }
    console.log('CSV Ingestion Complete:', result);
    this.ui.updateLiveStatus('user_csv');
  }
```

---

### 4.3 Component Blueprint 3: `src/frontend/static/js/ui.js`

Add an HTML sanitizer helper `escapeHtml(str)` at top of module (or file scope):
```javascript
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
```

Add dedicated renderer method `renderCsvQuarantineReport(result)` to `UIController`:
```javascript
  renderCsvQuarantineReport(result) {
    if (!this.dom.csvQuarantineArea) return;

    const records = result.quarantined_records || result.quarantine_records || [];
    const errors = result.errors || [];
    const validCount = result.valid_rows || 0;
    const quarantinedCount = result.quarantined_rows || records.length;
    const isTotalFailure = validCount === 0;

    let html = '';

    // Status / Alert banner
    if (isTotalFailure) {
      html += `
        <div class="quarantine-banner banner-failed" style="margin-top: 10px; padding: 10px 12px; background: rgba(255, 107, 94, 0.15); border: 1px solid #ff6b5e; border-radius: 4px; color: #ff7a6b; font-size: 12px;">
          <div style="font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 14px;">⚠️</span> CSV Validation Failed: 0 Valid Records Merged
          </div>
          <div>All ${quarantinedCount || result.total_rows || 0} row(s) were quarantined or invalid. Current telemetry dataset remains unchanged.</div>
        </div>
      `;
    } else {
      html += `
        <div class="quarantine-banner banner-warning" style="margin-top: 10px; padding: 10px 12px; background: rgba(237, 125, 49, 0.15); border: 1px solid #ED7D31; border-radius: 4px; color: #f09553; font-size: 12px;">
          <div style="font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 14px;">ℹ️</span> Partial Ingestion: ${validCount} Records Merged
          </div>
          <div>${quarantinedCount} row(s) were quarantined due to schema or validation errors. Review the quarantine table below.</div>
        </div>
      `;
    }

    // Top-Level Schema Errors (e.g. missing columns)
    if (errors.length > 0) {
      html += `
        <div class="quarantine-errors" style="margin-top: 8px; padding: 8px 12px; background: rgba(0, 0, 0, 0.25); border: 1px solid var(--border-subtle); border-radius: 4px; font-size: 12px; color: var(--ink-primary);">
          <div style="font-weight: 600; color: #ff7a6b; margin-bottom: 4px;">Top-Level Schema Errors:</div>
          <ul style="margin: 0; padding-left: 18px;">
            ${errors.map(err => `<li style="margin-bottom: 2px;">${escapeHtml(err)}</li>`).join('')}
          </ul>
        </div>
      `;
    }

    // High-visibility scrollable table for row-level quarantine records
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
              ${records.map(rec => {
                const rowNum = rec.row_number ?? '-';
                const stationId = escapeHtml(rec.station_id || '-');
                const errType = escapeHtml(rec.error_type || 'VALIDATION_ERROR');
                const errMsg = escapeHtml(rec.error_message || 'Malformed record');
                const rawData = rec.raw_record ? escapeHtml(JSON.stringify(rec.raw_record)) : '-';
                return `
                  <tr style="border-bottom: 1px solid var(--border-subtle);">
                    <td style="padding: 6px 8px; font-family: var(--font-mono); font-weight: 600; color: var(--accent); white-space: nowrap; text-align: center;">${rowNum}</td>
                    <td style="padding: 6px 8px; font-family: var(--font-mono); color: var(--ink-primary); white-space: nowrap;">${stationId}</td>
                    <td style="padding: 6px 8px; white-space: nowrap;"><span style="display: inline-block; padding: 2px 6px; font-family: var(--font-mono); font-size: 10px; font-weight: 600; color: #ff6b5e; background: rgba(255, 107, 94, 0.15); border-radius: 3px;">${errType}</span></td>
                    <td style="padding: 6px 8px; font-family: var(--font-body); font-size: 11px; color: var(--ink-primary); line-height: 1.3; max-width: 200px; word-break: break-word;">${errMsg}</td>
                    <td style="padding: 6px 8px; max-width: 220px;"><pre style="margin: 0; padding: 3px 5px; font-family: var(--font-mono); font-size: 10px; color: var(--ink-secondary); background: rgba(0,0,0,0.3); border-radius: 2px; overflow-x: auto; white-space: pre-wrap; word-break: break-all;">${rawData}</pre></td>
                  </tr>
                `;
              }).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    this.dom.csvQuarantineArea.innerHTML = html;
  }
```

Rewrite `handleCsvUpload()` in `src/frontend/static/js/ui.js:613-637`:
```javascript
  async handleCsvUpload() {
    const file = this.dom.csvFileInput.files[0];
    if (!file) {
      alert('Please select a valid CSV file.');
      return;
    }

    // Reset previous quarantine error messages
    if (this.dom.csvQuarantineArea) {
      this.dom.csvQuarantineArea.innerHTML = '';
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
          // Keep modal open, do NOT switch app state to user_csv
        } else {
          alert(`CSV Ingestion Warning: ${validCount} valid records merged into telemetry, but ${result.quarantined_rows} record(s) were quarantined. Review quarantine details below.`);
          // Valid rows merged -> update app telemetry
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
        this.dom.csvQuarantineArea.innerHTML = `<div style="color: #ff5e5e; font-size: 12px; margin-top: 8px;"><b>Error:</b> ${escapeHtml(err.message)}</div>`;
      }
    } finally {
      this.dom.csvUploadSubmit.disabled = false;
      this.dom.csvUploadSubmit.textContent = 'Upload Dataset';
    }
  }
```

In `bindEvents()` in `ui.js`:
Add file input change handler to clear stale quarantine errors when selecting a new file:
```javascript
    if (this.dom.csvFileInput) {
      this.dom.csvFileInput.addEventListener('change', () => {
        if (this.dom.csvQuarantineArea) {
          this.dom.csvQuarantineArea.innerHTML = '';
        }
      });
    }
```

---

### 4.4 Component Blueprint 4: CSS Tokens Enhancement (`src/frontend/static/css/tokens.css`)

Update modal container width and declare quarantine classes:
```css
/* Modal Box Legibility Upgrade for Quarantine Inspector */
.modal-box {
  background: var(--bg-panel);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  max-width: 760px; /* Increased from 580px to accommodate 5-column quarantine table */
  width: 92%;
  max-height: 85vh;
  overflow-y: auto;
}

/* CSV Quarantine Inspector Styling */
.quarantine-table-wrap {
  max-height: 240px;
  overflow-y: auto;
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-canvas);
}

.quarantine-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.quarantine-table th {
  position: sticky;
  top: 0;
  background: var(--bg-panel-elevated);
  color: var(--ink-secondary);
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-strong);
  z-index: 2;
  white-space: nowrap;
}

.quarantine-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--ink-primary);
  vertical-align: top;
}
```

---

## 5. Verification Method

### 5.1 Verification Commands

1. **Verify Quarantine Inspector in Node.js (Unit Simulation)**:
Run the verified simulation script in `.agents/teamwork/explorer_m5_it2_1/test_fixed_ui.js`:
```bash
node .agents/teamwork/explorer_m5_it2_1/test_fixed_ui.js
```
Expected output:
```
--- Case 1 (Total Failure) ---
Alert text: CSV Ingestion Failed: 0 valid records merged. 6 record(s) quarantined. Review quarantine details below.
Modal dismissed (should be false): false
Quarantine area empty (should be false): false
Quarantine table contains Row #: true
Quarantine table contains Station ID: true
Quarantine table contains Error Type: true
Quarantine table contains Error Message: true
Quarantine table contains Raw Row Data: true
App ingested (should be undefined): undefined
--- Case 2 (Partial Quarantine) ---
Alert text: CSV Ingestion Warning: 8 valid records merged into telemetry, but 2 record(s) were quarantined. Review quarantine details below.
Modal dismissed (should be false): false
Quarantine area empty (should be false): false
App ingested (should be defined): partial_quarantine
--- Case 3 (Complete Success) ---
Alert text: CSV Upload Success: 10 valid records merged into telemetry.
Modal dismissed (should be true): true
Quarantine area cleared (should be true): true
App ingested (should be defined): success
```

2. **Verify Adversarial Integration Test Suite (Post-Remediation)**:
After worker updates `ui.js`, `api.js`, and adjusts test assertions in `tests/integration/test_m5_resilience_challenge.py`:
```bash
python -m pytest tests/integration/test_m5_resilience_challenge.py -v
```
All 9 tests must pass with 0 failures.

3. **Verify Full Regression Suite (494+ tests)**:
```bash
python -m pytest tests/ -q
```
Expected: 494+ passed, 0 failures.

### 5.2 Invalidation Conditions
This remediation blueprint would be invalidated if:
- Uploading a failed CSV dismisses the modal or leaves `#csvQuarantineArea` empty.
- An alert claiming "CSV Upload Success: 0 valid records" is displayed when 0 rows were merged.
- The status badge transitions to `USER CSV DATASET` when `valid_rows === 0`.
- The quarantine table fails to render all 5 required columns (`Row #`, `Station ID`, `Error Type`, `Error Message`, `Raw Row Data`).
