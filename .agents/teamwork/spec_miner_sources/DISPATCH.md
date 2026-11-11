## 2026-11-10T11:07:10Z
You are the Data Sources Investigator (teamwork_spec_miner).
Your working directory is: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_sources\
Read ORIGINAL_REQUEST.md at: c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\ORIGINAL_REQUEST.md

Your primary objective is to investigate the authoritative source file:
c:\Users\Asif\Downloads\Punjab Air Quality\index.html

Focus strictly on Requirement R1: Data Source and Stream Inventory.
Analyze index.html to discover and document:
1. Every external API endpoint and data stream (URL, HTTP method, query parameters, headers, authentication if any).
2. Expected payload formats and response schemas (JSON structure, fields, units, coordinate systems).
3. Polling frequency, update triggers, and refresh cadence.
4. Fallback mechanisms, error handling, mock/cached data fallbacks, timeouts, retry logic.
5. Cross-reference all known data sources mentioned in requirements:
   - EPA Punjab (Environmental Protection Agency Punjab monitoring stations)
   - METAR (aviation weather reports)
   - WMO SYNOP (surface synoptic observations)
   - ECMWF IFS via Open-Meteo (meteorological forecasts, boundary layer height, wind, temperature)
   - NASA FIRMS (Fire Information for Resource Management System - MODIS/VIIRS thermal anomalies / crop fires)
   - IQAir (air quality station data / sensor feeds)
   - Any other third-party services, tile servers, or static assets referenced.

STRICT CONSTRAINT: Do not modify index.html or any codebase files. This is an exploration task only.
Write your comprehensive catalog to:
c:\Users\Asif\Downloads\Punjab Air Quality\.agents\teamwork\spec_miner_sources\sources_catalog.md
When finished, write your handoff.md in your working directory and notify the orchestrator with send_message.
