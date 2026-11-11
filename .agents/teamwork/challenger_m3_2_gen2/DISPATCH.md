## 2026-11-11T04:02:01Z
You are challenger_m3_2_gen2 (Archetype: teamwork_challenger).
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m3_2_gen2\
Project root: c:\Users\Asif\Downloads\Punjab Air Quality
Original request path: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
Scope document: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md

Your task is to perform empirical, code-executing adversarial challenge testing on Milestone M3: Data Pipelines & CSV Ingestion Engine, focusing on meteorological decoders and multi-pollutant aggregation.

Target modules to challenge:
- src/pipelines/metar.py
- src/pipelines/synop.py
- src/pipelines/csv_adapter.py

Key focus areas for your stress tests:
1. WMO SYNOP Telegraphic Decoder (AAXX):
   - Token collision resistance: Section 1 indicator group `iRixhVV` (token 3) which commonly begins with `1` (e.g., `11560`) must NOT collide with temperature group `1snTTT`.
   - Wind group `Nddff`: Calm wind (`dd=00`), variable wind (`dd=99`), storm speeds (>99 kt parsed via `00fff` auxiliary group in Section 3).
   - Wind units: knots-to-m/s conversion factor `0.514444` for $i_w \in (3, 4)$, native m/s for $i_w \in (0, 1)$.
   - Negative temperature parsing (`sn=1`).
2. NOAA METAR Parser:
   - Coverage of all 12 aerodromes (`OPLA, OPFA, OPMT, OPST, OPIS, OPRN, OPRK, OPBW, OPDG, OPSR, OPMI, VIAR`).
   - Metric visibility regex `\s(\d{4})\s` override in `rawOb` over statute-to-meter conversion.
   - Present weather token decoding: `FU, HZ, BR, FG, DU, RA, TS`.
   - Variable wind (`VRB`) retention of speed with direction set to None.
   - Temporal alignment window `[-35 min, +25 min]` around top-of-hour.
3. User CSV multi-pollutant row merging:
   - Ingest multiple rows sharing the same `(station_id, timestamp)` with different pollutants (e.g. Row 1: PM2.5 = 120.0, Row 2: PM10 = 250.0).
   - Verify `get_merged_observations()` merges them into a single coherent Observation entity with both values populated.
   - Verify PEPC statutory composite AQI recalculation ($\max(I_{\text{PM2.5}}, I_{\text{PM10}})$) on merged observations.

Write your adversarial tests in tests/integration/test_m3_adversarial_challenge.py.
Run the tests using pytest: `python -m pytest tests/integration/test_m3_adversarial_challenge.py -v`.
Deliver your final verdict (CONFIRM or REQUEST_CHANGES) in:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m3_2_gen2\handoff.md
Update progress.md as you work. When complete, send a message to orchestrator with your verdict.
