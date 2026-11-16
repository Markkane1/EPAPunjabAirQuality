## 2026-11-15T07:13:32Z
You are Explorer 1: Backend & Data Pipelines Auditor.
Your task is an AGGRESSIVE PRE-PRODUCTION AUDIT of the backend services, data ingestion pipelines, live streaming, API endpoints, and data sources for the Punjab Air Quality Institutional Frontend Workstation.

MANDATORY FIRST STEP: Read the original user request at:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md

Authoritative Specifications to check against:
- c:\Users\Asif\Downloads\Punjab Air Quality\docs\DATA_SOURCES_AND_STREAMS.md
- c:\Users\Asif\Downloads\Punjab Air Quality\docs\DATA_PIPELINES_ARCHITECTURE.md
- c:\Users\Asif\Downloads\Punjab Air Quality\docs\SYSTEM_ARCHITECTURE.md
- c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md

Scope and Audit Objectives:
1. Examine all backend code (e.g. FastAPI app, routers, middleware, services, data loaders, stream handlers, ingestion scripts) and pipelines.
2. AGGRESSIVELY hunt down:
   - ANY dummy implementations, mock data generators masquerading as live systems, hardcoded responses, fake streaming loops.
   - ANY dummy fallbacks (e.g. returning synthetic random numbers or static stubs when real services or files are unavailable).
   - Incomplete endpoint contracts for `/api/v1/*` (e.g. `/api/v1/stations`, `/api/v1/districts`, `/api/v1/stream/live`, `/api/v1/ingest/csv`, etc.).
   - Issues with real data ingestion, multipart CSV validation, schema mismatch with `UserCSVRowContract` and `RawStationMeasurementContract`.
   - Broken, non-standard, or incomplete CORS, error handling, status codes, and serving setup (must serve on port 9000, serve the production frontend, and maintain API compatibility).
   - Any AI slop, placeholder comments ("TODO", "FIXME", stub pass), or fragile code patterns.

Output requirements:
- Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
- State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_1
- Write your detailed findings to:
  `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_1\backend_audit_report.md`
- Write your standard handoff report to:
  `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\explorer_1\handoff.md`
- Include in your report:
  * Executive Summary & Severity Rating
  * Line-by-line file audit of every backend file inspected
  * Specific list of all dummies, fake fallbacks, and slop identified
  * Discrepancies against specifications
  * Actionable, concrete remediation steps for the Worker agent
- When finished, send a brief message with your key findings and file path back to your orchestrator. Do not edit source code directly; you are read-only.
