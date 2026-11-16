"""
Script to generate an institutional-grade Word document (.docx)
for the Punjab Air Quality Information System Brief.
"""

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from pathlib import Path

def set_cell_background(cell, hex_color):
    """Sets background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets internal padding for a cell in twips."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def add_callout(doc, text_lines, title=None, border_color="2B6CB0", bg_color="F7FAFC"):
    """Adds a callout box with a colored left border and light shading."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=120, bottom=120, left=200, right=150)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="none"/>
            <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>
            <w:bottom w:val="none"/>
            <w:right w:val="none"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    
    if title:
        run_title = p.add_run(title + "\n")
        run_title.bold = True
        run_title.font.name = "Calibri"
        run_title.font.size = Pt(10.5)
        run_title.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
        
    for i, line in enumerate(text_lines):
        if i > 0 or title:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
        run = p.add_run(line)
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def format_table(tbl, col_widths, headers, data, header_bg="1A365D", alt_bg="F7FAFC"):
    """Formats a document table with custom headers, alternating rows, and paddings."""
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    # Header Row
    hdr_cells = tbl.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].width = col_widths[i]
        set_cell_background(hdr_cells[i], header_bg)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for r in p.runs:
            r.bold = True
            r.font.name = "Calibri"
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            
    # Data Rows
    for r_idx, row_data in enumerate(data):
        row = tbl.add_row()
        cells = row.cells
        bg = alt_bg if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            cells[c_idx].text = str(val)
            cells[c_idx].width = col_widths[c_idx]
            set_cell_background(cells[c_idx], bg)
            set_cell_margins(cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(9)
                r.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    # Set light subtle border on all cells
    tblPr = tbl._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E0"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E0"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>
            <w:insideV w:val="none"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def build_brief_document(output_path: Path):
    doc = Document()
    
    # Page setup: Standard Letter, 0.75 in margins
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        
    # Styles Setup
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    normal_style.paragraph_format.line_spacing = 1.2
    normal_style.paragraph_format.space_after = Pt(4)

    # Helper functions
    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Calibri'
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(0x0F, 0x29, 0x42) # Deep navy
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Calibri'
        run.font.size = Pt(13)
        run.font.color.rgb = RGBColor(0x2B, 0x6C, 0xB0) # Slate blue
        return p

    def add_h3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Calibri'
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        if bold_prefix:
            r_pre = p.add_run(bold_prefix + ": ")
            r_pre.bold = True
            r_pre.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
        r_txt = p.add_run(text)
        r_txt.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
        return p

    # --- Title Banner ---
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run("PUNJAB AIR QUALITY INFORMATION SYSTEM")
    r_title.bold = True
    r_title.font.size = Pt(22)
    r_title.font.color.rgb = RGBColor(0x0F, 0x29, 0x42)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_after = Pt(6)
    r_sub = p_sub.add_run("Institutional Architecture Brief, Pipeline Specifications, Atmospheric Physics & System Evaluation")
    r_sub.font.size = Pt(12)
    r_sub.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

    # Document Meta Table
    meta_tbl = doc.add_table(rows=2, cols=4)
    meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_w = [Inches(1.6), Inches(1.8), Inches(1.6), Inches(2.0)]
    meta_data = [
        [("Document ID:", "PAQ-INST-BRIEF-2026"), ("Version:", "1.0.0 (Production Blueprint)"), ("Date:", "November 2026"), ("Classification:", "Institutional Technical Specification")],
        [("Target Airshed:", "Punjab Province (PK & IN)"), ("Backend Framework:", "FastAPI / TimescaleDB / PostGIS"), ("Frontend Stack:", "React 18 / Deck.gl / MapLibre GL"), ("Operational Status:", "Production Certified (144/144 Tests)")]
    ]
    for r_idx, row in enumerate(meta_tbl.rows):
        for c_idx, cell in enumerate(row.cells):
            cell.width = col_w[c_idx]
            label, val = meta_data[r_idx][c_idx]
            set_cell_background(cell, "F7FAFC")
            set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r1 = p.add_run(label + " ")
            r1.bold = True
            r1.font.size = Pt(8.5)
            r1.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)
            r2 = p.add_run(val)
            r2.font.size = Pt(8.5)
            r2.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)
            
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(8)
    p_div.paragraph_format.space_after = Pt(8)

    # --- SECTION 1: EXECUTIVE SUMMARY ---
    add_h1("1. Executive Summary: What the System Actually Is and Does")
    
    doc.add_paragraph(
        "The Punjab Air Quality System is an institutional environmental monitoring, geostatistical interpolation, "
        "and transboundary atmospheric transport intelligence workstation. It is engineered to monitor, evaluate, and counter "
        "the catastrophic winter smog emergencies that severely degrade public health across the Punjab airshed "
        "(encompassing 41 administrative districts in Pakistan and bordering states in Northern India)."
    )
    
    add_callout(
        doc,
        [
            "• End-to-End Mission: Ingest multi-source sensor and satellite data, isolate sensor errors, harmonize wind kinematics, impute unmonitored districts, and project live smoke plume advection across international frontiers.",
            "• Deconstructed Monolith: Replaced a legacy 9.61 MB single-file HTML prototype (where 94.5% of the payload was inlined JSON with 60+ global variables) with a modern four-tier decoupled micro-architecture.",
            "• Absolute Scientific Rigor: Operates on strict physical laws (Eulerian advection mass flux, Haversine geodesy, and anisotropic wind steering) rather than arbitrary visual Gaussian blurs."
        ],
        title="CORE MISSION & VALUE PROPOSITION"
    )

    doc.add_paragraph(
        "The system executes six mission-critical operations in continuous real time:"
    )
    add_bullet("Collects observations from seven decoupled data streams across ground AQMS, aerodrome weather, synoptic telegrams, satellite fires, regional networks, and chemical reanalysis.", "1. Multi-Stream Ingestion")
    add_bullet("Enforces a 4-tier hierarchical resolution chain (Station Anemometer → Nearest Aerodrome METAR ≤ 40km → Scaled ECMWF IFS Model → Geodesic IDW) to establish valid surface wind vectors even when ground vanes fail.", "2. Wind Kinematic Fusion")
    add_bullet("Suppresses zero/negative anomalies, applies rolling 7-hour median spike filters, enforces 3-hour logger hold purges, and blacklists erratic hardware (e.g. Station 172 Wazirabad's 140° vane offset).", "3. Quality Control (QC) Engine")
    add_bullet("Calculates discrete geodesic Inverse Distance Weighting (IDW, p=2, d0=5km) for unmonitored districts and dynamic anisotropic 2D concentration fields steered by wind direction.", "4. Geostatistical Imputation")
    add_bullet("Computes continuous piecewise linear air quality index values following statutory Punjab Environmental Protection Council (PEPC) rules, clamping values at 500 when PM2.5 exceeds 350 µg/m³.", "5. Statutory PEPC Indexing")
    add_bullet("Pushes sub-20 KB delta frames over Server-Sent Events (SSE) into an institutional Deck.gl v8 / MapLibre GL v3 cartographic workstation supporting 60 FPS sub-hourly timeline navigation.", "6. Real-Time Streaming & Workstation")

    # --- SECTION 2: THE 7 INGESTION PIPELINES ---
    add_h1("2. Detailed Pipeline Architecture (The 7 Data Streams)")
    doc.add_paragraph(
        "The system decouples data acquisition from analytical processing by deploying independent, asynchronous ingestion workers "
        "orchestrated via APScheduler cron daemons and Redis distributed locks. Every worker operates with strict fault isolation: "
        "the downtime or network failure of any single provider never degrades the remaining streams."
    )

    # Pipeline Summary Table
    add_h2("2.1 Global Stream Catalog & Integration Topology")
    stream_headers = ["Stream ID", "Provider / Source", "Data Modality", "Cadence", "Primary Storage Target"]
    stream_widths = [Inches(1.2), Inches(1.5), Inches(1.7), Inches(0.9), Inches(1.7)]
    stream_data = [
        ["STR-01-EPAPUNJAB", "EPA Punjab Portal", "Ground AQMS (9 pollutants + wind)", "Hourly (:05, :15)", "station_hourly_observations"],
        ["STR-02-METAR", "NOAA Aviation Weather", "Aviation Aerodrome Meteorology", "Hourly (:10)", "airport_meteorology"],
        ["STR-03-SYNOP", "WMO GTS via Ogimet", "Synoptic Surface Telegrams (FM-12)", "Hourly (:15)", "synoptic_observations"],
        ["STR-04-ECMWF-IFS", "Open-Meteo / ECMWF", "10m & 925 hPa Wind Grids (0.1° / 0.25°)", "Hourly & 6-Hourly", "ecmwf_wind_grid"],
        ["STR-05-FIRMS", "NASA Earthdata", "VIIRS 375m Satellite Thermal Fires", "Daily (03:00, 15:00Z)", "active_fires"],
        ["STR-06-IQAIR", "IQAir AirVisual", "Cross-Border Indian AQMS Clusters", "Hourly (:20)", "cross_border_aqi"],
        ["STR-07-CAMS", "Copernicus ECMWF", "Boundary PM2.5 Flux (117 Nodes)", "Daily (04:00Z Batch)", "transboundary_flux"],
        ["STR-CSV", "User Multipart CSV", "Custom Field Monitoring Campaigns", "On-Demand", "Dynamic In-Memory Re-IDW"]
    ]
    stream_tbl = doc.add_table(rows=1, cols=5)
    format_table(stream_tbl, stream_widths, stream_headers, stream_data)

    p_space = doc.add_paragraph()
    p_space.paragraph_format.space_before = Pt(6)

    # In-Depth Pipeline Details
    add_h2("2.2 Pipeline Deep-Dive & Processing Rules")

    # P1
    add_h3("Pipeline 1: EPA Punjab Public AQMS Ingestion (STR-01-EPAPUNJAB)")
    add_bullet("Component & Endpoint: src/pipelines/epa_punjab.py querying https://aqi.punjab.gov.pk/api/dashboard/current with mandatory User-Agent 'EMC-EPA-Punjab-AQ-dashboard/1.0'.")
    add_bullet("Monitored Coverage: 79 monitoring stations (74 fixed installations, 5 mobile laboratory vans) reporting PM2.5, PM10, NO2, SO2, CO, O3, NO, NOx, and wind.")
    add_bullet("Sanitization & Boundary Guards: Purges zero and negative values to null; preserves genuine severe smog peaks up to 5000 µg/m³ (flagged QC_EXCEEDANCE_EXTREME); localizes Asia/Karachi timestamps into UTC.")
    add_bullet("Resilience & Fallback: Implements asynchronous fan-out fallback over district endpoints (/api/district-stations/{name}) with asyncio.Semaphore(10) and a strict 3-second timeout to prevent worker starvation.")

    # P2
    add_h3("Pipeline 2: Aviation Weather METAR Worker (STR-02-METAR)")
    add_bullet("Component & Endpoint: src/pipelines/metar.py querying aviationweather.gov/api/data/metar for 12 regional ICAO aerodromes.")
    add_bullet("Target Stations: OPLA (Lahore Intl), OPFA (Faisalabad), OPMT (Multan), OPST (Sialkot), OPIS (Islamabad), OPRN (Nur Khan), OPRK (Rahim Yar Khan), OPBW (Bahawalpur), OPDG (Dera Ghazi Khan), OPSR (Sargodha AB), OPMI (Mianwali AB), and VIAR (Amritsar Intl, India).")
    add_bullet("Normalization & Decoding: Knots converted to SI meters per second (ws = knots * 0.514444); visibility in statute miles converted to meters; decodes present weather tokens (FU = smoke, HZ = haze, FG = fog).")
    add_bullet("Null vs. Calm Distinction: Eliminates telemetry dropouts by distinguishing null reporting from valid aerodynamic calm (0.0 <= ws < 0.50 m/s).")

    # P3
    add_h3("Pipeline 3: WMO GTS SYNOP Surface Observations (STR-03-SYNOP)")
    add_bullet("Component & Source: src/pipelines/synop.py decoding WMO FM-12 AAXX telegraphic bulletins via Ogimet gateway for WMO Blocks 415, 416, and 417.")
    add_bullet("Target Observatories: Lahore PBO (41640), Sialkot (41594), Multan (41675), Faisalabad (41624), Bahawalpur (41700), Jhelum (41598), and Islamabad (41571).")
    add_bullet("Telegraphic Parsing: Extracts wind unit indicator iw, wind direction (dd * 10°), wind speed (ff), surface barometric pressure, 2m temperature, and extreme speed overflow (Group 00fff).")

    # P4
    add_h3("Pipeline 4: ECMWF IFS Numerical Weather Prediction (STR-04-ECMWF-IFS)")
    add_bullet("Component & Model: src/pipelines/open_meteo.py ingesting ECMWF Integrated Forecasting System (IFS 0.25°/0.1°) data.")
    add_bullet("Kinematic Conversion: Converts polar speed and meteorological direction into Cartesian components (u = -ws*sin(theta), v = -ws*cos(theta)).")
    add_bullet("Surface Roughness Calibration: Applies empirical surface drag factor KR = 0.22686 to reconcile free-atmosphere grid winds with ground boundary-layer friction.")
    add_bullet("Multi-Level Spatial Grid: Ingests 225 nodes covering 27.5°N–34.5°N and 69.0°E–76.0°E at both 10m surface level and 925 hPa (transport altitude above surface obstacles).")

    # P5
    add_h3("Pipeline 5: NASA FIRMS Satellite Active Thermal Anomalies (STR-05-FIRMS)")
    add_bullet("Component & Platform: src/pipelines/firms.py interfacing with NASA EOSDIS / LANCE VIIRS 375m active fire telemetry.")
    add_bullet("Parameters Ingested: Acquisition timestamp, latitude/longitude, brightness temperature (T21, T31), Fire Radiative Power (FRP, MW), detection confidence, and satellite pass.")
    add_bullet("Geospatial Partitioning: PostGIS / Shapely spatial join classifies fire points into subnational administrative units (Pakistani Punjab, Indian Punjab, Haryana, Rajasthan, Sindh, KPK, J&K).")
    add_bullet("Gas Flaring Filter: Suppresses persistent non-agricultural industrial flaring anomalies in southern Rajasthan (lat < 27.0°N).")

    # P6
    add_h3("Pipeline 6: IQAir Cross-Border Regional Network (STR-06-IQAIR)")
    add_bullet("Component & Purpose: src/pipelines/iqair.py monitoring upwind airsheds in Northern India: Amritsar, Jalandhar, Ludhiana, Bathinda, Firozpur, New Delhi, and Jammu.")
    add_bullet("Regulatory Standard Alignment: Re-evaluates raw Indian particulate concentrations against official Punjab PEPC breakpoints to ensure direct legal and scientific comparability with Pakistani stations.")

    # P7
    add_h3("Pipeline 7: CAMS Transboundary PM2.5 Boundary Flux (STR-07-CAMS)")
    add_bullet("Component & Input: src/pipelines/cams.py ingesting Copernicus Atmosphere Monitoring Service regional aerosol reanalysis.")
    add_bullet("Boundary Node Discretization: Discretizes the 1,100 km international border into 117 coordinate nodes.")
    add_bullet("Normal Flux Advection: Calculates inward advective flux by computing the vector dot product of ECMWF 10m wind with inward border normal unit vectors: Phi_j = C_CAMS * (w_j · n_j).")

    # --- SECTION 3: PIPELINE INTEGRATION ---
    add_h1("3. Integration of Individual Pipelines: How the System Meshes Together")
    doc.add_paragraph(
        "A common pitfall in environmental monitoring systems is data fragmentation—where satellite maps, weather charts, and sensor tables "
        "exist in separate silos. The Punjab Air Quality System overcomes this through a centralized chronometric harmonization engine "
        "that binds all streams into a single synchronized state space."
    )

    add_callout(
        doc,
        [
            "1. Chronometric Pinning: Disparate network payloads arriving at arbitrary seconds are staged in memory and locked to the canonical UTC hour (T_H).",
            "2. Multi-Tier Wind Hierarchy: Ground Station Anemometer → Nearest METAR (<=40km) → Scaled ECMWF Model → Geodesic Vector IDW.",
            "3. Geostatistical Imputation (T1): Imputes 41 district centroids using Discrete Geodesic IDW (Haversine R=6371km, p=2, d0=5km clamp).",
            "4. Eulerian Advection Flux (T6/T7): Inter-district transport mass flux C_A * w_A * cos(delta_theta) * exp(-d/100km) with physical dimension guards.",
            "5. Transboundary Normal Chevrons (T8): Computes wind-border dot products across 39 border normals, triggering visual inflow chevrons when Phi > +0.25 m/s.",
            "6. Continuous Piecewise Linear PEPC AQI (T9): Half-open intervals (BP_{i-1}, BP_i] with statutory 500 ceiling cap when PM2.5 > 350 µg/m³."
        ],
        title="MULTI-TIER INTEGRATION & HARMONIZATION CORE"
    )

    add_h2("3.1 Chronometric Staging & Atomic Persistence")
    doc.add_paragraph(
        "The ChronometricStagingBuffer (src/pipelines/staging_buffer.py) acts as the single point of synchronization. "
        "When an ingestion tick triggers (either on a live cron schedule or via manual API dispatch), the buffer reconciles all feeds "
        "for target hour T_H. Once validation and mathematical transforms complete, the buffer executes an atomic write across:"
    )
    add_bullet("station_hourly_observations (TimescaleDB hypertable partitioned by 30-day chunks).")
    add_bullet("district_hourly_aggregates (TimescaleDB hypertable containing aggregated and IDW-imputed district records).")
    add_bullet("airport_meteorology, synoptic_observations, active_fires, cross_border_aqi, and transboundary_flux tables.")
    add_bullet("Redis 7.2 in-memory cache, storing precomputed spatial surface grids and summary JSON frames with a 7-day TTL.")

    add_h2("3.2 The 5 Schema Traps & Normalization Protections")
    doc.add_paragraph(
        "To ensure total software stability against real-world data deformities, the data normalizer (src/domain/normalizer/dataNormalizer.ts "
        "and dataNormalizer.py) systematically resolves five critical schema traps:"
    )
    add_bullet("Centroid Inversion Trap: Reverses inverted [latitude, longitude] arrays into standard geospatial [longitude, latitude] coordinates while preserving polygon boundary rings.", "Trap 1")
    add_bullet("Aerodrome Null vs. Calm: Accurately differentiates telemetry dropouts from aerodynamic calm (speed < 0.50 m/s), preventing false calm reports.", "Trap 2")
    add_bullet("Station 172 Wazirabad Blacklist: Mechanically blocks wind vector rendering for Station 172 due to a permanent 140° hardware vane offset, marking the anemometer as blacklisted.", "Trap 3")
    add_bullet("Dynamic Station Counts: Dynamically reconciles active station counts (74 fixed vs. 5 mobile) against database catalog metadata.", "Trap 4")
    add_bullet("Estimation Flag Unification: Merges conflicting raw flags ('est', 'is_monitored') into a single strict boolean 'is_estimated', triggering map cross-hatching.", "Trap 5")

    # --- SECTION 4: OVERALL SYSTEM ARCHITECTURE ---
    add_h1("4. Overall System Architecture & Workstation Console")
    doc.add_paragraph(
        "The complete system is organized into a four-tier architecture, maintaining absolute separation of concerns between data ingestion, "
        "storage, delivery, and cartographic rendering."
    )

    arch_headers = ["System Tier", "Core Technologies", "Primary Responsibilities", "SLA / Latency"]
    arch_widths = [Inches(1.2), Inches(1.8), Inches(2.3), Inches(1.2)]
    arch_data = [
        ["Tier 1: Ingestion", "Python 3.11+, HTTPX, Pydantic v2, APScheduler", "Asynchronous polling of 7 external streams, zero-purge, 7h median spike filter, 3h hold filter", "5–15 sec per cycle"],
        ["Tier 2: Persistence & Processing", "PostgreSQL 16, TimescaleDB, PostGIS, Redis 7.2", "Chunk-partitioned hypertables, PostGIS spatial geometries, continuous aggregates, Redis fast cache", "<5 ms query latency"],
        ["Tier 3: API Gateway", "FastAPI, Uvicorn, SSE / WebSockets, OpenAPI 3.1", "REST contracts (/api/v1/*), real-time delta pushes (<20 KB), static asset root serving", "<10 ms TTFB"],
        ["Tier 4: Workstation Presentation", "React 18, TypeScript, Deck.gl v8, MapLibre GL v3", "Rigid 100vw x 100vh CSS Grid, 5 GPU layers, sub-hourly 60 FPS lerp scrubber, WCAG AAA tokens", "60 FPS rendering"]
    ]
    arch_tbl = doc.add_table(rows=1, cols=4)
    format_table(arch_tbl, arch_widths, arch_headers, arch_data)

    p_space2 = doc.add_paragraph()
    p_space2.paragraph_format.space_before = Pt(6)

    add_h2("4.1 The 5 Hardware-Accelerated Deck.gl Cartographic Layers")
    doc.add_paragraph(
        "Rather than drawing monolithic HTML5 canvas pixels or relying on heavyweight 3D engines, the workstation implements "
        "an interleaved MapLibre GL + Deck.gl MapboxOverlay rendering pipeline composed of five distinct layers:"
    )
    add_bullet("Layer 0 (Continuous Spatial Surface): 2D wind-steered anisotropic IDW concentration surface with dynamic distance-based opacity decay (45 km to 140 km alpha taper).")
    add_bullet("Layer 1 (District Choropleth & Labels): 41 administrative boundaries colored by PEPC statutory tiers, diagonal polygon cross-hatching for estimated districts, and greedy AABB collision-free label placement.")
    add_bullet("Layer 2 (Vector Wind Field): Planar wind arrows with velocity-proportional scaling; Station 172 suppressed.")
    add_bullet("Layer 3 (Advection Transport Flux & Chevrons): Dynamic Bezier curves showing inter-district mass flux, and 39 border normal chevrons indicating transboundary smoke influx.")
    add_bullet("Layer 4 (Stations & Aerodromes): 79 monitoring stations (including the 13 Lahore micro-network sites) and 12 ICAO aerodromes with interactive click telemetry.")

    add_h2("4.2 Five-Zone Command Console Layout")
    doc.add_paragraph(
        "The frontend enforces a strict 100vw x 100vh CSS Grid divided into five dedicated operational zones:"
    )
    add_bullet("Zone 1 (Top Command Bar): System identity, live streaming vs. offline fallback badge, assertive ARIA live hazard alert, 9-pollutant selector, CSV upload adapter, and QA drawer toggle.")
    add_bullet("Zone 2 (Spatial Control Dock): 5-layer visibility toggles, transboundary mass-balance attribution split bar, and 41-district statutory ranking table with auto-centering.")
    add_bullet("Zone 3 (Planimetric Map Canvas): Strict 2D cartographic view (pitch locked to 0, rotation disabled) covering the Punjab airshed.")
    add_bullet("Zone 4 (Receptor Inspector): Detailed site metadata, 9-parameter sub-index table, 16-sector CPF polar rose (with Nk < 6 sample suppression), and 216-hour QC sparkline chart.")
    add_bullet("Zone 5 (Precision Timeline Scrubber): 216-hour timeline, transport playback controls (1x, 2x, 4x, 8x), max AQI horizon sparkline, and GPU update triggers.")

    # --- SECTION 5: PROS ---
    add_h1("5. Pros of the System as a Whole")
    add_bullet("Unlike commercial dashboards that produce smoothed radial heatmaps, every calculation in this system obeys atmospheric kinematics: anisotropic wind elongation, Gaussian plume distance decay, and vector dot product boundary flux.", "1. Atmospheric Physics Fidelity")
    add_bullet("The workstation boots instantly and functions completely offline using pre-indexed baseline datasets if PostgreSQL or external networks are unavailable. Once connected, it seamlessly upgrades to live streaming.", "2. Air-Gapped Disaster Resilience")
    add_bullet("Adheres to the rigorous '/impeccable' institutional standard: high-contrast WCAG 2.1 AAA color tokens (>= 7.0:1), clean IBM Plex typography, monospaced tabular figures, and zero decorative emojis or 3D pitch distortion.", "3. Institutional UI/UX Ergonomics")
    add_bullet("The custom animation engine throttles React state updates to 15 Hz while interpolating canvas positions at 60 FPS, eliminating frame drops and garbage collection churn.", "4. Sub-Hourly Continuous Scrubbing")
    add_bullet("Built with strict circuit breakers, exponential backoff, and asynchronous fallbacks. A failure in government scrapers or foreign gateways never halts the local dashboard.", "5. Isolated Microservice Reliability")
    add_bullet("Certified by a 144-test opaque-box E2E test suite covering boundary values, mathematical invariants, physical guards, and real-world smog event scenarios.", "6. Comprehensive Verification")

    # --- SECTION 6: CONS & LIMITATIONS ---
    add_h1("6. Cons and Limitations of the System as a Whole")
    add_bullet("While Punjab covers 205,344 km² and 110 million people, physical regulatory stations are heavily concentrated in Lahore, Faisalabad, and Rawalpindi. Large southern districts (Rajanpur, Layyah) have zero ground monitors and rely entirely on mathematical IDW imputation.", "1. Ground Sensor Scarcity")
    add_bullet("If deployed in basic Linux or Windows environments where PostgreSQL lacks TimescaleDB or PostGIS binaries, the system degrades to standard unpartitioned SQL heap tables and CPU Haversine math, which can degrade query speeds as years of data accumulate.", "2. Database Extension Dependencies")
    add_bullet("The EPA Punjab portal frequently modifies its HTML/JSON output, throttles client IPs, or experiences server crashes during intense smog episodes, requiring ongoing maintenance of scraper headers and fallback paths.", "3. External API Fragility")
    add_bullet("The system uses 2D kinematic mass-flux advection. It does not simulate 3D vertical chemical reactions, such as secondary inorganic aerosol formation (e.g., SO2 and NOx converting into ammonium sulfate/nitrate in high-humidity winter fog).", "4. Absence of 3D Photochemical Modeling")
    add_bullet("The current interactive timeline scrubber is hardcoded to an indexed 216-hour window (9 days). Accessing multi-year historical archives requires querying backend REST endpoints rather than dragging the scrubber.", "5. Scrubber Timeline Horizon Bounds")

    # --- SECTION 7: FUTURE ENHANCEMENTS ---
    add_h1("7. Recommended System Enhancements")
    doc.add_paragraph(
        "To elevate the Punjab Air Quality System into a predictive, proactive environmental command and enforcement center, "
        "the following architectural expansions are recommended:"
    )

    add_bullet("Integrate open-source WRF-Chem or CAMx chemical transport models to project 3D planetary boundary layer heights, nocturnal temperature inversions, and vertical smoke plume trapping.", "1. 3D Eulerian Photochemical Modeling")
    add_bullet("Deploy a Spatio-Temporal Graph Neural Network (ST-GNN) or Temporal Fusion Transformer trained on historical meteorology, satellite fire radiative power, and ground sensors to deliver accurate 24h, 48h, and 72h predictive district AQI forecasts.", "2. AI/ML Predictive Smog Forecasting")
    add_bullet("Incorporate chemical speciation inputs (Black Carbon, PM2.5/PM10 ratios, CO/CO2 combustion indices) with Positive Matrix Factorization (PMF) to dynamically attribute pollution sources (vehicular vs. brick kilns vs. cross-border stubble fires).", "3. Automated Source Apportionment")
    add_bullet("Build a crowd-sourced IoT ingestion gateway with dynamic empirical calibration curves against reference Beta-Attenuation Monitors (BAM-1020), expanding monitoring into rural unmonitored districts.", "4. Low-Cost IoT Sensor Mesh Calibration")
    add_bullet("Automate geofenced webhook dispatch to environmental enforcement squads when industrial corridors exceed emissions limits during stagnant meteorological conditions.", "5. Automated Regulatory Enforcement Webhooks")

    # --- SECTION 8: SUMMARY MATRIX ---
    add_h1("8. Strategic Summary Matrix")
    matrix_headers = ["Evaluation Dimension", "Current Operational Reality", "Strategic Next Step"]
    matrix_widths = [Inches(1.8), Inches(2.4), Inches(2.3)]
    matrix_data = [
        ["Core Paradigm", "Institutional atmospheric physics & monitoring workstation", "Predictive policy simulation & enforcement dispatch platform"],
        ["Data Modality", "7 external streams (ground, aviation, synop, model, satellite)", "Ingest Sentinel-5P TROPOMI satellite trace gases & IoT meshes"],
        ["Meteorological Engine", "4-tier wind hierarchy (Station -> METAR -> ECMWF -> IDW)", "3D atmospheric sounding & boundary layer height integration"],
        ["Spatial Interpolation", "Geodesic IDW (T1) and anisotropic wind-steered IDW (T2)", "Graph Neural Network spatio-temporal machine learning"],
        ["Storage Architecture", "PostgreSQL 16 + TimescaleDB + PostGIS + Redis Cache", "Multi-node high-availability database cluster with automated retention"],
        ["Frontend Workstation", "React 18, Deck.gl v8, MapLibre GL v3, WCAG 2.1 AAA, 60 FPS lerp", "Automated PDF regulatory brief generator & mobile enforcement PWA"]
    ]
    matrix_tbl = doc.add_table(rows=1, cols=3)
    format_table(matrix_tbl, matrix_widths, matrix_headers, matrix_data)

    # Save document
    doc.save(str(output_path))
    print(f"Document successfully created at: {output_path}")

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    out_file = repo_root / "docs" / "Punjab_Air_Quality_System_Brief.docx"
    build_brief_document(out_file)
