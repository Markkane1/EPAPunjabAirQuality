# DISPATCH: Challenger 2 (Adversarial Cartography & Physics Invariant Stress Tester)
Date: 2026-11-15T08:16:00Z
Target: Empirical adversarial verification of domain physics T1-T11, Station 172 blacklist, flux physical guards, and mathematical boundaries.

## 2026-11-15T08:10:47Z
You are Challenger 2: Adversarial Physics & Mathematical Invariant Stress Tester.
Your task is to EMPIRICALLY AND ADVERSARIALLY STRESS-TEST the domain physics calculations (T1–T11), Station 172 blacklisting, and mathematical boundary constraints.

MANDATORY FIRST STEP: Read the original user request at:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md

Artifacts to stress-test:
- `src/domain/math/` (both Python and TypeScript implementations)
- `src/domain/normalizer/` (both `dataNormalizer.ts` and `normalizer.py`)
- Authoritative spec: `docs/TRANSFORMATION_LOGIC_SPEC.md`
- Worker Handoff: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_1\handoff.md

Stress-Test Objectives:
1. Station 172 Blacklist Stress Test: Adversarially query Station 172 in both Python and TypeScript with integer `172`, string `"172"`, case variations `"wazirabad"`, `"WAZIRABAD"`, `"pk_waz_001"`. Verify that all queries return blacklisted, and no wind vectors are rendered or blended for Station 172.
2. T1 Singularity Clamp: Test Haversine distance with $d=0$ (identical station and target coords). Verify distance is clamped to $d_0 = 5.0$ km and weight remains finite without division-by-zero or NaN.
3. T6 Physical Dimension Guard: Call advection flux calculation with `pollutant = "AQI"`. Verify that it strictly locks to PM2.5 mass or returns null/empty, never computing mass flux on dimensionless index units.
4. T9 Scale Boundaries: Test PM2.5 concentrations at $350.0$, $350.1$, $500.0$, $5000.0$. Verify continuous half-open interval breakpoints and strict 500 ceiling clamp.
5. T10 Temporal QC: Stress-test 3h hold filter at indices $i=0, 1, 2$ with duplicate values, and verify AQI values are exempt from logger hold suppression.
6. Execute TypeScript test suites:
   - `npx tsx tests/unit/test_challenger_m1m2.ts`
   - `npx tsx tests/unit/test_challenger_m3m4.ts`
   - `npx tsx tests/unit/test_challenger_m5.ts`
   All must pass with 0 failures.

Output requirements:
- State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_2
- Output handoff report: `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_2\handoff.md`
- Include:
  * Verdict: APPROVE or REQUEST_CHANGES
  * Numerical verification values and edge-case test outputs
- Send a brief message back to orchestrator upon completion.
