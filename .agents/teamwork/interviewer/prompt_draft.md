Build the full end-to-end Punjab Air Quality monitoring, processing, and visualization system according to the specifications in docs/, organizing the codebase with clean architecture, software engineering principles, component-driven design patterns, and high reusability to support both live external streams and custom user datasets.

Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
Integrity mode: development

## Reference Specifications
- docs/ARCHITECTURE_OVERVIEW.md
- docs/DATA_SOURCES_AND_STREAMS.md
- docs/TRANSFORMATION_LOGIC_SPEC.md
- docs/DATA_PIPELINES_ARCHITECTURE.md
- docs/SYSTEM_ARCHITECTURE.md
- docs/UI_UX_SPECIFICATION.md

## Requirements

### R1. Archive Existing Workspace Artifacts
Move existing project files (index.html and the collector/ directory) into a new directory named "original System", while preserving docs/ and .agents/ in the project root.

### R2. Data Pipeline & Ingestion Engine
Implement modular data ingestion pipelines adhering to docs/DATA_SOURCES_AND_STREAMS.md and docs/DATA_PIPELINES_ARCHITECTURE.md. Connect to accessible live external data feeds where available, extract station metadata and historical records from the original artifacts for baseline data templating, and provide clear interfaces allowing the system to ingest and test against user-provided CSV and custom datasets.

### R3. Transformation Logic Implementation
Implement the scientific transformation algorithms as defined in docs/TRANSFORMATION_LOGIC_SPEC.md, including IDW spatial interpolation, CPF polar roses, pollutant flux calculations, and PEPC breakpoint calculations, adhering to clean architecture with decoupled pure functions and documented mathematical inputs/outputs.

### R4. Core Services & Backend Architecture
Implement the backend architecture and API services specified in docs/SYSTEM_ARCHITECTURE.md and docs/ARCHITECTURE_OVERVIEW.md, maintaining strict boundary separation between data sources, business logic, storage adapters, and presentation interfaces.

### R5. Component-Driven UI/UX Dashboard
Implement the interactive user interface specified in docs/UI_UX_SPECIFICATION.md, adhering to component-driven design patterns, responsive layouts, clear visual hierarchy, accessible color palettes, and real-time visualization components.

### R6. Automated Verification and Test Suite
Implement automated test suites covering pipeline data ingestion, mathematical transformation algorithms, backend API contracts, and UI component rendering against the specifications in docs/.

## Acceptance Criteria

### Workspace Archival
- [ ] index.html and collector/ are relocated under original System/.
- [ ] docs/ remains intact in the workspace root.

### Pipeline and Ingestion
- [ ] Pipeline modules ingest data from configured live endpoints or fallback to schema-conforming templates seeded from station data in original System/index.html.
- [ ] An ingestion adapter exists that accepts and validates user-provided CSV datasets conforming to the specification schema.

### Transformation Logic
- [ ] Automated tests verify IDW spatial interpolation, CPF polar rose calculations, flux calculations, and PEPC breakpoints against known reference fixtures with deterministic output matching docs/TRANSFORMATION_LOGIC_SPEC.md.

### System Architecture & APIs
- [ ] Clean architecture boundaries are established with isolated domain models, business logic, data access abstractions, and API routing.
- [ ] Backend API endpoints serve station metadata, live/current readings, historical trends, and spatial interpolation outputs.

### UI/UX Interface
- [ ] Frontend dashboard renders station map, pollutant breakdown metrics, wind/flux indicators, and historical trend charts according to docs/UI_UX_SPECIFICATION.md.
- [ ] Interactive UI components respond to filter, station selection, and time-range queries without unhandled errors.

### Automated Test Verification
- [ ] Unit and integration test suites pass completely via automated test runners with zero failures.
