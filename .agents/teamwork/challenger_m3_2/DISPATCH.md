## 2026-11-10T14:17:14Z
From: dfe9ab49-5b73-4c71-b636-dccdcc9080ee
Priority: MESSAGE_PRIORITY_HIGH

You are challenger_m3_2 (Archetype: teamwork_challenger). Your working directory is c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\challenger_m3_2\

MANDATORY FIRST STEP: Read the following authoritative documents before testing:
1. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md
2. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\orchestrator\PROJECT.md
3. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_architecture\handoff.md
4. c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\worker_m3_pipeline_active\handoff.md
5. docs/DATA_SOURCES_AND_STREAMS.md
6. docs/DATA_PIPELINES_ARCHITECTURE.md

CHALLENGE OBJECTIVE:
Perform empirical adversarial testing and stress verification of Milestone M3 pipeline modules.
Stress-test:
- METAR parser against weird weather tokens, variable wind (`VRB02KT`), missing temperature/dewpoint, extreme wind gusts.
- SYNOP decoder against truncated telegrams, missing groups, negative temperatures.
- CSV adapter multi-pollutant row merging (e.g. Town Hall PM2.5 and PM10 on separate lines merging to calculate correct composite PEPC AQI).
Write an adversarial test file in `tests/integration/test_m3_adversarial_challenge.py` and run `python -m pytest tests/integration/test_m3_adversarial_challenge.py -v`.
Deliver verdict: CONFIRM or REJECT in handoff.md and send a message when done.
