/**
 * EPA Punjab Air Quality Monitoring, Processing, and Visualization System
 * Institutional Telemetry CSV Ingestion Modal with Quarantine Inspector
 *
 * Implements:
 * - Multipart upload to POST /api/v1/ingest/csv with allow_missing_coords flag
 * - Client-side validation: file extension, non-zero file size
 * - Detailed error display for schema violations
 * - Structured Dead Letter Quarantine Table inside #csvQuarantineArea
 * - WCAG 2.1 AAA contrast, 1px structural hairlines, tabular-nums formatting
 */

import React, { useState } from 'react';
import { Upload, AlertTriangle } from '../common/icons';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import type { CSVIngestResponse, QuarantineDetail } from '../../services/api';
import { apiService } from '../../services/api';

export interface CSVIngestModalProps {
  onUpload?: (file: File, allowMissingCoords: boolean) => Promise<CSVIngestResponse>;
  onSuccessMerged?: (result: CSVIngestResponse) => void;
  triggerButton?: React.ReactNode;
}

export const CSVIngestModal: React.FC<CSVIngestModalProps> = ({
  onUpload,
  onSuccessMerged,
  triggerButton,
}) => {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [allowMissingCoords, setAllowMissingCoords] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [response, setResponse] = useState<CSVIngestResponse | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    setValidationError(null);
    setResponse(null);
    if (!selected) {
      setFile(null);
      return;
    }
    if (!selected.name.toLowerCase().endsWith('.csv')) {
      setValidationError('Invalid file type. Only .csv files are supported.');
      setFile(null);
      return;
    }
    if (selected.size === 0) {
      setValidationError('Selected file is empty (0 bytes).');
      setFile(null);
      return;
    }
    setFile(selected);
  };

  const handleSubmit = async () => {
    if (!file) return;
    setUploading(true);
    setValidationError(null);
    try {
      const res = onUpload
        ? await onUpload(file, allowMissingCoords)
        : await apiService.uploadCSV(file, allowMissingCoords);

      setResponse(res);
      if (res.valid_rows > 0 && res.status !== 'failed') {
        onSuccessMerged?.(res);
      }
    } catch (err: any) {
      setValidationError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const quarantinedRecords: QuarantineDetail[] =
    response?.quarantined_records ?? response?.quarantine_records ?? [];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {triggerButton ?? (
          <Button
            variant="outline"
            size="sm"
            data-testid="ingest-csv-trigger"
            className="h-8 gap-1.5 rounded-none text-xs font-medium"
          >
            <Upload size={14} strokeWidth={1.25} /> Ingest CSV
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-2xl rounded-none border-border bg-background p-6">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm uppercase tracking-wider">
            EPA Telemetry CSV Ingestion & Quality Quarantine
          </DialogTitle>
          <DialogDescription className="font-mono text-xs text-muted-foreground">
            Multipart upload to POST /api/v1/ingest/csv. Validates coordinates, statutory pollutants, and temporal holds.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 space-y-4">
          <div className="space-y-2">
            <label htmlFor="csv-file-input" className="font-mono text-xs font-medium text-foreground">
              Select Ingestion CSV File
            </label>
            <Input
              id="csv-file-input"
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileChange}
              disabled={uploading}
              className="rounded-none font-mono text-xs"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="allowCoords"
              checked={allowMissingCoords}
              onChange={(e) => setAllowMissingCoords(e.target.checked)}
              disabled={uploading}
              className="h-4 w-4 rounded-none"
            />
            <label htmlFor="allowCoords" className="font-mono text-xs text-muted-foreground">
              Allow canonical catalog coordinate resolution for recognized stations
            </label>
          </div>

          <div className="flex items-center justify-between border-t border-border pt-4">
            <Button
              onClick={handleSubmit}
              disabled={!file || uploading}
              data-testid="csv-upload-submit"
              className="rounded-none font-mono text-xs"
            >
              {uploading ? 'Processing & Validating…' : 'Upload & Commit Dataset'}
            </Button>
            {response && (
              <Badge
                variant="outline"
                className={`rounded-none font-mono text-xs ${
                  response.status === 'success'
                    ? 'border-emerald-500/40 text-emerald-500'
                    : response.status === 'partial_quarantine'
                    ? 'border-amber-500/40 text-amber-500'
                    : 'border-rose-500/40 text-rose-500'
                }`}
              >
                {response.status.toUpperCase()}: {response.valid_rows} VALID / {response.quarantined_rows} QUARANTINED
              </Badge>
            )}
          </div>

          {validationError && (
            <div className="border border-rose-500/40 bg-rose-500/10 p-3 font-mono text-xs text-rose-400">
              <div className="flex items-center gap-1.5 font-bold">
                <AlertTriangle size={14} strokeWidth={1.25} />
                <span>Validation Error</span>
              </div>
              <p className="mt-1">{validationError}</p>
            </div>
          )}

          {response?.errors && response.errors.length > 0 && (
            <div className="border border-rose-500/40 bg-rose-500/10 p-3 font-mono text-xs text-rose-400">
              <span className="font-bold">Schema Rejection Errors:</span>
              <ul className="list-disc pl-5 mt-1 space-y-0.5">
                {response.errors.map((e, idx) => (
                  <li key={idx}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {/* QUARANTINE INSPECTOR AREA */}
          <div id="csvQuarantineArea" className="mt-4">
            {quarantinedRecords.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-semibold uppercase text-muted-foreground">
                    Quarantine Inspection Log ({quarantinedRecords.length} records rejected)
                  </span>
                  <span className="font-mono text-[11px] text-rose-400">
                    Review non-conformant rows below
                  </span>
                </div>
                <div className="max-h-48 overflow-auto border border-border">
                  <table className="w-full text-left font-mono text-xs border-collapse">
                    <thead className="bg-muted text-muted-foreground border-b border-border sticky top-0">
                      <tr>
                        <th className="p-2 border-r border-border">Row</th>
                        <th className="p-2 border-r border-border">Station ID</th>
                        <th className="p-2 border-r border-border">Error Code</th>
                        <th className="p-2">Error Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {quarantinedRecords.map((r, idx) => (
                        <tr key={idx} className="border-b border-border/50 hover:bg-muted/50">
                          <td className="p-2 border-r border-border tabular-nums font-semibold">{r.row_number}</td>
                          <td className="p-2 border-r border-border">{r.station_id || 'N/A'}</td>
                          <td className="p-2 border-r border-border text-rose-400">{r.error_type}</td>
                          <td className="p-2 text-muted-foreground">{r.error_message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
