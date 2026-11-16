## Task Assignment: Milestone M1-M2 Challenger (Challenger 1)

### Working Directory
`c:\Users\Asif\Downloads\Punjab Air Quality`

### State Folder
`c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m1m2_1`

### Authoritative Files to Read
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\PROJECT.md`
- `c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m1m2_1\handoff.md`
- `src/domain/normalizer/dataNormalizer.ts`
- `src/domain/math/`

### Objective
Empirically stress-test the implementation of `dataNormalizer.ts` and `src/domain/math/`.
Generate adversarial inputs for:
1. Centroid inversion edge cases (e.g. invalid bounds, already inverted coords).
2. Aerodrome wind dropouts (null, NaN, negative, calm < 0.50 m/s vs active).
3. Station 172 Wazirabad blacklist bypass attempts (case variations, ID as int vs string).
4. Physical dimension guard in flux calculations (AQI vs PM2.5, PM10).
5. PEPC continuous half-open intervals, 500 ceiling clamp, 7h median spike filter, 3h logger hold with i >= 2 index guard and AQI exemption.
Provide empirical results and an overall verdict: `APPROVE` or `REQUEST_CHANGES` in `handoff.md`.


## 2026-11-14T08:50:27Z
You are challenger_m1m2_1.
Working directory: c:\Users\Asif\Downloads\Punjab Air Quality
State folder: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m1m2_1
Read DISPATCH.md in your state folder.
MANDATORY: Read ORIGINAL_REQUEST.md at c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md before starting work.

Empirically challenge and stress-test dataNormalizer.ts and src/domain/math/ delivered by worker_m1m2_1.
Test:
1. Centroid inversion edge cases.
2. Aerodrome wind dropouts (null vs calm < 0.50 m/s vs active).
3. Station 172 Wazirabad blacklist suppression.
4. Physical dimension guard in flux.ts (AQI returns null, PM2.5 works).
5. PEPC 500 ceiling clamp for PM2.5 > 350 ug/m3, 7h median spike filter, 3h logger hold with i >= 2 guard and AQI exemption.
Provide empirical findings and overall verdict: APPROVE or REQUEST_CHANGES in handoff.md and send message.
