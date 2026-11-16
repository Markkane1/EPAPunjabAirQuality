"""
Comprehensive institutional brief generator (v2 - Deep Technical Pass)
for the Punjab Air Quality Information and Atmospheric Transport System.
Outputs directly to: docs/Punjab_Air_Quality_System_Brief.docx
"""

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from pathlib import Path

def set_cell_background(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
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

def add_callout(doc, text_lines, title=None, border_color="1A365D", bg_color="F7FAFC"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.8)
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=120, bottom=120, left=180, right=150)
    
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
        run_title.font.color.rgb = RGBColor(0x0F, 0x29, 0x42)
        
    for i, line in enumerate(text_lines):
        if i > 0 or title:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
        run = p.add_run(line)
        run.font.name = "Calibri"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def format_table(tbl, col_widths, headers, data, header_bg="0F2942", alt_bg="F7FAFC"):
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    # Header Row
    hdr_cells = tbl.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].width = col_widths[i]
        set_cell_background(hdr_cells[i], header_bg)
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=120, right=120)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for r in p.runs:
            r.bold = True
            r.font.name = "Calibri"
            r.font.size = Pt(9)
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
            set_cell_margins(cells[c_idx], top=80, bottom=80, left=100, right=100)
            p = cells[c_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(8.5)
                r.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

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

def add_footer(section):
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("Punjab Air Quality Information System | Deep Architectural & Operational Brief — Page ")
    run.font.name = "Calibri"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x71, 0x80, 0x96)
    
    # Page field
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)

def generate_full_brief(output_path: Path):
    doc = Document()
    
    # Page setup
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        add_footer(section)

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)
    normal_style.paragraph_format.line_spacing = 1.18
    normal_style.paragraph_format.space_after = Pt(4)

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(15)
        run.font.color.rgb = RGBColor(0x0F, 0x29, 0x42)
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(0x1B, 0x4D, 0x89)
        return p

    def add_h3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(10.5)
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
            r_pre.font.color.rgb = RGBColor(0x0F, 0x29, 0x42)
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
    r_sub = p_sub.add_run("Exhaustive Technical & Operational System Architecture Specification (Deep Pass)")
    r_sub.font.size = Pt(11.5)
    r_sub.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

    # Document Metadata Table
    meta_tbl = doc.add_table(rows=2, cols=4)
    meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_w = [Inches(1.5), Inches(1.8), Inches(1.6), Inches(2.1)]
    meta_data = [
        [("Document ID:", "PAQ-TECH-DEEP-2026"), ("Version:", "2.0.0 (Master Deep Architecture)"), ("Date:", "November 16, 2026"), ("Target Airshed:", "Punjab Province (PK & IN)")],
        [("Backend Engine:", "FastAPI / TimescaleDB / PostGIS"), ("Caching & Bus:", "Redis 7.2 Pub/Sub & Caching"), ("Frontend Engine:", "React 18 / Deck.gl v8 / MapLibre v3"), ("Test Certification:", "144/144 Tests Passed (Tiers 1–5)")]
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
            r2.font.color.rgb = RGBColor(0x0F, 0x29, 0x42)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ==========================================
    # CHAPTER 1: MISSION & GROUND REALITY
    # ==========================================
    add_h1("1. System Purpose & Operational Reality: What the System Actually Does")
    
    doc.add_paragraph(
        "The Punjab Air Quality System is an institutional-grade environmental telemetry, geostatistical interpolation, "
        "and transboundary atmospheric transport intelligence platform. The system operates across the entire geographical territory "
        "of Punjab, Pakistan (41 administrative districts, 79 active environmental monitoring stations, 12 aviation aerodromes, "
        "and 7 synoptic observatories), as well as adjacent cross-border airsheds in Northern India (Punjab-IN, Haryana, Rajasthan, "
        "and Jammu & Kashmir)."
    )

    add_callout(
        doc,
        [
            "• Ground Reality: The Indo-Gangetic Plain undergoes extreme nocturnal radiation temperature inversions from October to February. "
            "Surface air cools faster than upper air layers, forming a thermal 'lid' at 100–300 meters altitude that traps primary particulate emissions "
            "(PM2.5, PM10), sulfur dioxide, and nitrogen oxides. Surface wind speeds routinely drop below 0.5 m/s (aerodynamic calm), causing severe smog accumulation.",
            "• Legacy Fragility Deconstruction: The original production baseline existed as an extreme single-file monolith (index.html, 9.61 MB) "
            "where 94.5% of the file footprint consisted of hardcoded inlined historical observations (window.DATA, 9.08 MB) and 60+ unencapsulated global variables. "
            "The new system completely decouples this monolith into an asynchronous, distributed four-tier architecture.",
            "• Absolute Scientific Rigor: Every visual plume, vector arrow, and district index on screen is backed by deterministic atmospheric kinematics "
            "and statutory Punjab Environmental Protection Council (PEPC) linear piecewise breakpoints."
        ],
        title="OPERATIONAL GROUND REALITY & SYSTEM MISSION"
    )

    doc.add_paragraph("In continuous operational practice, the system executes six core capabilities every hour:")
    add_bullet("Asynchronously queries 7 independent external streams plus custom user uploads, parsing heterogeneous protocols (REST JSON, WMO FM-12 telegrams, raw METAR aviation strings, NetCDF/GRIB boundary fluxes, and VIIRS thermal anomaly CSVs).", "1. Multi-Stream Ingestion & Normalization")
    add_bullet("Applies statutory quality control cleaning rules: zero-suppression, 7-hour rolling median spike filters (vi > 4Mi and vi > 3ref), 3-hour sensor freeze hold detection (with i >= 2 guard), and physical hardware blacklists.", "2. Automated Quality Control & Vane Blacklisting")
    add_bullet("Resolves wind vectors through a 4-tier hierarchical fallback chain (Ground Station Anemometer → Nearest Aerodrome METAR <= 40km → Scaled ECMWF IFS Model → Geodesic IDW Vector Imputation).", "3. Kinematic Wind Reconciliation")
    add_bullet("Imputes missing pollutant concentrations across unmonitored districts using Discrete Geodesic IDW (Haversine R=6371km, p=2, d0=5km clamp) and generates continuous anisotropic wind-steered 2D concentration fields.", "4. Geostatistical Surface Modeling")
    add_bullet("Calculates pairwise inter-district advection mass flux links (capped at 180 km and 35° divergence cones) and transboundary cross-border mass flux across 39 border normal vectors.", "5. Atmospheric Transport & Mass Balance")
    add_bullet("Publishes delta frames over Server-Sent Events (SSE) to an institutional React 18 / Deck.gl v8 cartographic workstation operating at 60 FPS with sub-hourly timeline lerp.", "6. Real-Time Streaming Workstation")

    # ==========================================
    # CHAPTER 2: THE 7 INGESTION PIPELINES
    # ==========================================
    add_h1("2. Detailed Pipeline Architecture (The 7 External Streams + CSV & Simulation)")
    doc.add_paragraph(
        "Each data provider is isolated into an independent ingestion microservice in src/pipelines/. "
        "A failure, timeout, or rate-limit in any single external provider is isolated by circuit breakers and never blocks "
        "or contaminates other data streams."
    )

    # Table of streams
    stream_headers = ["Stream ID", "Provider / Platform", "Protocol & Format", "Cadence", "Storage Target", "Key Parameters"]
    stream_widths = [Inches(1.1), Inches(1.3), Inches(1.2), Inches(0.9), Inches(1.2), Inches(1.3)]
    stream_data = [
        ["STR-01-EPAPUNJAB", "EPA Punjab Portal", "HTTPS REST (JSON)", "Hourly (:05, :15)", "station_hourly_obs", "PM2.5, PM10, NO2, SO2, CO, O3, Wind"],
        ["STR-02-METAR", "NOAA Aviation Weather", "HTTPS REST (JSON/rawOb)", "Hourly (:10)", "airport_meteorology", "Wind, Gust, Vis, Temp, Dew, IFR/VFR"],
        ["STR-03-SYNOP", "WMO GTS via Ogimet", "HTTPS GET (FM-12 AAXX)", "Hourly (:15)", "synoptic_observations", "Surface Pressure, Temp, Dew, 10m Wind"],
        ["STR-04-ECMWF-IFS", "Open-Meteo / ECMWF", "HTTPS REST (JSON)", "Hourly (:00) & 6h", "ecmwf_wind_grid", "10m & 925hPa Wind Vectors (225 nodes)"],
        ["STR-05-FIRMS", "NASA Earthdata", "HTTPS REST (CSV)", "Daily (03, 15 UTC)", "active_fires", "VIIRS 375m FRP, Brightness Temp, Pass"],
        ["STR-06-IQAIR", "IQAir AirVisual", "HTTPS REST (JSON)", "Hourly (:20)", "cross_border_aqi", "Cross-Border Indian Cluster AQMS"],
        ["STR-07-CAMS", "Copernicus ECMWF", "HTTPS OGC / NetCDF", "Daily (04:00 UTC)", "transboundary_flux", "Boundary PM2.5 Inflow (117 nodes)"],
        ["STR-CSV", "User Multipart CSV", "HTTP POST /api/v1/ingest/csv", "On-Demand", "In-Memory Re-IDW", "Field campaign sensor transects"]
    ]
    stream_tbl = doc.add_table(rows=1, cols=6)
    format_table(stream_tbl, stream_widths, stream_headers, stream_data)

    doc.add_paragraph().paragraph_format.space_before = Pt(6)

    # Detailed sub-sections for each pipeline
    add_h2("2.1 Pipeline 1: EPA Punjab Public Portal & Ground AQMS (STR-01-EPAPUNJAB)")
    add_bullet("Component & Target: src/pipelines/epa_punjab.py querying https://aqi.punjab.gov.pk/api/dashboard/current with mandatory User-Agent 'EMC-EPA-Punjab-AQ-dashboard/1.0'.")
    add_bullet("Network Topology & Fallback Fan-Out: If the primary dashboard endpoint times out or returns HTTP 5xx, the worker immediately executes an asynchronous fallback fan-out: queries GET /api/district-stations/{district_name} across missing districts using asyncio.gather bounded by asyncio.Semaphore(10) with a 3.0-second per-district timeout. This bounds worst-case execution to <15 seconds, preventing worker starvation.")
    add_bullet("GIS Coordinate Correction Registry: Overrides erratic portal coordinates with verified surveying coordinates for Gulberg III, Sialkot, Wazirabad, Sahiwal, and Rawalpindi.")
    add_bullet("Pydantic Boundary Validation: Validates records against RawStationMeasurement schema; rejects values >5000 µg/m³; preserves extreme smog peaks (>1000 µg/m³) with tag QC_EXCEEDANCE_EXTREME; converts Asia/Karachi timestamps to UTC.")

    add_h2("2.2 Pipeline 2: Aviation Weather METAR Worker (STR-02-METAR)")
    add_bullet("Component & Target: src/pipelines/metar.py querying NOAA Aviation Weather Center for 12 regional ICAO aerodromes (OPLA, OPFA, OPMT, OPST, OPIS, OPRN, OPRK, OPBW, OPDG, OPSR, OPMI, and VIAR).")
    add_bullet("Temporal Observation Matching: For each aerodrome, selects the observation closest to canonical hour T_H within window [-35 min, +25 min].")
    add_bullet("Unit Normalization: Converts wind speed in knots to meters per second (ws = wspd * 0.514444); converts visibility in statute miles to meters (vis = visib * 1609.344); decodes weather tokens (FU = smoke, HZ = haze, FG = fog).")
    add_bullet("Aerodrome Null vs. Calm Distinction: Crucially differentiates sensor dropouts (null) from true aerodynamic calm (0.0 <= ws < 0.50 m/s), ensuring calm conditions are correctly accounted for in atmospheric dispersion.")

    add_h2("2.3 Pipeline 3: WMO GTS SYNOP Surface Observations (STR-03-SYNOP)")
    add_bullet("Component & Target: src/pipelines/synop.py decoding WMO FM-12 AAXX telegraphic bulletins via Ogimet gateway for WMO Blocks 415, 416, and 417.")
    add_bullet("Target Stations: Primary regional synoptic observatories: Lahore PBO (41640), Sialkot (41594), Multan (41675), Faisalabad (41624), Bahawalpur (41700), Jhelum (41598), and Islamabad (41571).")
    add_bullet("Telegraphic Decoding: Parses raw telegram lines: extracts wind unit indicator iw (0/1 -> m/s, 3/4 -> knots), wind direction (dd * 10°), wind speed (ff), barometric pressure, 2m dry-bulb temperature, and extreme speed overflow (Group 00fff).")

    add_h2("2.4 Pipeline 4: ECMWF IFS Numerical Weather Prediction (STR-04-ECMWF-IFS)")
    add_bullet("Component & Target: src/pipelines/open_meteo.py querying Open-Meteo ECMWF IFS 0.25°/0.1° model for 41 district administrative centroids and a 225-node regional 2D grid.")
    add_bullet("Polar-to-Cartesian Kinematic Conversion: Derives orthogonal velocity components: u = -ws * sin(theta * pi / 180), v = -ws * cos(theta * pi / 180).")
    add_bullet("Surface Roughness Calibration: Multiplies free-atmosphere model wind velocities by empirical surface drag coefficient KR = 0.22686 to reconcile model output with ground-level friction.")
    add_bullet("Dual Vertical Levels: Extracts winds at 10m (surface boundary layer) and 925 hPa (~750m above ground level, representing uninhibited regional transport above ground obstacles).")

    add_h2("2.5 Pipeline 5: NASA FIRMS Satellite Active Thermal Anomalies (STR-05-FIRMS)")
    add_bullet("Component & Target: src/pipelines/firms.py interfacing with NASA EOSDIS / LANCE VIIRS 375m active fire data (bounding box 69.0°E–76.5°E, 27.5°N–34.5°N).")
    add_bullet("Physical Fire Radiative Power (FRP): Ingests fire radiative power in Megawatts (MW) and brightness temperature to quantify the thermal intensity of seasonal crop residue stubble burning.")
    add_bullet("Spatial Join & Jurisdiction Allocation: Uses PostGIS/Shapely spatial intersection to classify fires into Pakistani Punjab, Indian Punjab, Haryana, Rajasthan, Sindh, KPK, and J&K.")
    add_bullet("Industrial Gas Flaring Suppression: Automatically filters out persistent non-agricultural flares in oil/gas extraction fields of southern Rajasthan (lat < 27.0°N).")

    add_h2("2.6 Pipeline 6: IQAir Cross-Border Regional Network (STR-06-IQAIR)")
    add_bullet("Component & Target: src/pipelines/iqair.py querying upwind monitoring clusters in Northern India: Amritsar, Jalandhar, Ludhiana, Bathinda, Firozpur, New Delhi, and Jammu.")
    add_bullet("Regulatory Normalization: Ingests raw PM2.5/PM10 concentrations and re-evaluates them using the statutory Punjab PEPC AQI breakpoint schedule, ensuring direct legal and scientific comparability with Pakistani stations.")

    add_h2("2.7 Pipeline 7: CAMS Transboundary PM2.5 Boundary Flux (STR-07-CAMS)")
    add_bullet("Component & Target: src/pipelines/cams.py ingesting Copernicus Atmosphere Monitoring Service regional aerosol reanalysis at 117 discretized boundary coordinate nodes along the 1,100 km international border.")
    add_bullet("Boundary Normal Dot Product: Calculates inward mass flux by taking the vector dot product of ECMWF 10m wind with inward border normal unit vectors: Phi_j = C_CAMS * (w_j · n_j). Chevrons trigger when Phi_j > +0.25 m/s.")

    add_h2("2.8 Auxiliary Pipelines: Multipart User CSV Ingestion & Simulation Pump")
    add_bullet("CSV Ingestion Adapter: POST /api/v1/ingest/csv validated against UserCSVRowContract (enforcing lat [27.0, 35.0], lon [69.0, 76.0], conc <= 5000 µg/m³), dynamically re-interpolating surfaces without server restart.", "STR-CSV")
    add_bullet("Simulation Pump: src/pipelines/simulation_pump.py replays 216 hours of baseline measurements at 1x, 2x, 4x, 8x speeds with full spatial and temporal fidelity for training and emergency drills.", "Simulation Engine")

    # ==========================================
    # CHAPTER 3: INTEGRATION & MATH TRANSFORMS
    # ==========================================
    add_h1("3. Pipeline Integration & The Mathematical Transformation Engine")
    doc.add_paragraph(
        "The system's core engineering achievement is how disparate network streams are harmonized into a mathematically "
        "coherent environmental model. Every calculation is performed deterministically using eleven core mathematical transformations (T1–T11)."
    )

    add_callout(
        doc,
        [
            "1. Discrete Geodesic IDW (T1): Imputes unmonitored districts using Haversine distance with 5.0 km singularity clamping: "
            "d_clamped = max(d, 5.0 km), w_i = 1 / (d_clamped)^2, C_target = sum(w_i * C_i) / sum(w_i).",
            "2. Anisotropic Wind-Steered Continuous IDW (T2): Modulates spatial concentration fields downwind along prevailing wind vectors: "
            "w_i = w_0 * max(0.30, 1.0 + 0.70 * cos(alpha) * min(1.0, ws / 1.5)) with distance-dependent alpha decay (45 to 140 km).",
            "3. Multi-Tier Wind Hierarchy: Local Station Anemometer → Nearest Aerodrome METAR (<=40km) → Scaled ECMWF IFS Model (KR=0.22686) → Geodesic Vector IDW.",
            "4. Inter-District Advection Mass Flux (T6): Pairwise mass transport C_a * w_a * cos(delta_theta) * exp(-d / 100km). "
            "Enforces physical dimension guards (returns empty for dimensionless AQI), distance cap <=180 km, and divergence cone <=35°.",
            "5. Transboundary Border Inflow (T8): Dot product of 39 border normal vectors with wind w_j · n_j > +0.25 m/s.",
            "6. Continuous Half-Open PEPC AQI Scale (T9): Linear interpolation across (BP_{i-1}, BP_i] with 500 ceiling clamp for PM2.5 > 350 µg/m³."
        ],
        title="CORE MATHEMATICAL & INTEGRATION PRINCIPLES"
    )

    add_h2("3.1 The 4-Tier Hierarchical Wind Reconciliation Algorithm")
    doc.add_paragraph(
        "Wind governs all atmospheric advection. To eliminate telemetry voids caused by broken, iced, or miscalibrated ground anemometers, "
        "the system implements a four-tier fallback resolution chain for every district and monitoring station:"
    )
    add_bullet("Tier 1: Ground Station Anemometer. Validated for physical sanity (0.0 <= ws <= 30.0 m/s, 0° <= theta <= 360°). Checked against hardware blacklists (Station 172 Wazirabad is hard-blocked due to a 140° vane installation offset).")
    add_bullet("Tier 2: Nearest Aviation Aerodrome METAR. If station wind is invalid or missing, the system searches within a 40 km Haversine radius for an active ICAO aerodrome (OPLA, OPFA, etc.).")
    add_bullet("Tier 3: Calibrated ECMWF IFS NWP Model. If no aerodrome is within 40 km, the district centroid model wind vector is pulled and scaled by ground friction factor KR = 0.22686.")
    add_bullet("Tier 4: Geodesic Vector IDW. As a final failover, orthogonal u and v components are interpolated from reporting regional stations.")

    add_h2("3.2 Chronometric Staging & Atomic Persistence")
    doc.add_paragraph(
        "The ChronometricStagingBuffer (src/pipelines/staging_buffer.py) collects all asynchronous observations for canonical hour T_H. "
        "Upon triggering harmonize_and_commit():"
    )
    add_bullet("Sanitizes all sensor readings, nullifying zeroes and negative concentrations.")
    add_bullet("Maps station names and IDs to canonical relational station entities.")
    add_bullet("Calculates PEPC sub-indices and particulate-governed composite AQI: AQI = max(I_PM2.5, I_PM10).")
    add_bullet("Aggregates station values into district means; executes Discrete Geodesic IDW (T1) for unmonitored districts, setting is_estimated = true.")
    add_bullet("Atomically commits records to TimescaleDB hypertables and pushes precomputed 5px grid surfaces and summary JSON packets into Redis 7.2 (7-day TTL).")

    add_h2("3.3 The 5 Schema Traps & Defensive Normalization")
    doc.add_paragraph("The normalizer systematically neutralizes five historical schema traps:")
    add_bullet("Centroid Inversion: Inverts [latitude, longitude] arrays into standard geospatial [longitude, latitude] coordinates while preserving polygon boundary rings.", "Trap 1")
    add_bullet("Aerodrome Null vs. Calm: Accurately differentiates telemetry dropouts from aerodynamic calm (speed < 0.50 m/s), preventing false calm reports.", "Trap 2")
    add_bullet("Station 172 Wazirabad Blacklist: Mechanically blocks wind vector rendering for Station 172 due to a permanent 140° hardware vane offset, marking the anemometer as blacklisted.", "Trap 3")
    add_bullet("Dynamic Station Counts: Dynamically reconciles active station counts (74 fixed vs. 5 mobile) against database catalog metadata.", "Trap 4")
    add_bullet("Estimation Flag Unification: Merges conflicting raw flags ('est', 'is_monitored') into a single strict boolean 'is_estimated', triggering map cross-hatching.", "Trap 5")

    # ==========================================
    # CHAPTER 4: SYSTEM ARCHITECTURE & WORKSTATION
    # ==========================================
    add_h1("4. Overall System Architecture & The Presentation Workstation")
    doc.add_paragraph(
        "The workstation is engineered to institutional military/utility command room standards: "
        "rigid 100vw x 100vh CSS Grid, zero emojis, high-contrast WCAG 2.1 AAA color tokens (>= 7.0:1), "
        "and locked 2D planimetric cartography (MapLibre GL v3 + Deck.gl v8 MapboxOverlay)."
    )

    # 4-Tier Architecture Table
    arch_headers = ["Architecture Tier", "Components & Stack", "Core Responsibilities", "Performance Target"]
    arch_widths = [Inches(1.2), Inches(1.8), Inches(2.3), Inches(1.2)]
    arch_data = [
        ["Tier 1: Ingestion", "Python 3.11+, HTTPX, Pydantic v2, APScheduler", "Asynchronous polling of 7 streams, outlier QC, coordinate reconciliation", "5–15 sec / cycle"],
        ["Tier 2: Persistence & Processing", "PostgreSQL 16, TimescaleDB, PostGIS, Redis 7.2", "Chunked hypertables, PostGIS geometries, continuous aggregates, Redis cache", "<5 ms query latency"],
        ["Tier 3: API Gateway", "FastAPI, Uvicorn, SSE, OpenAPI 3.1", "REST endpoints (/api/v1/*), real-time delta pushes (<20 KB), static serving", "<10 ms TTFB"],
        ["Tier 4: Workstation Console", "React 18, TypeScript, Deck.gl v8, MapLibre GL v3", "5-layer GPU rendering, 5-zone UI layout, sub-hourly 60 FPS lerp scrubber", "60 FPS rendering"]
    ]
    arch_tbl = doc.add_table(rows=1, cols=4)
    format_table(arch_tbl, arch_widths, arch_headers, arch_data)

    doc.add_paragraph().paragraph_format.space_before = Pt(6)

    add_h2("4.1 The 5 Hardware-Accelerated Deck.gl Cartographic Layers")
    add_bullet("Layer 0 (Continuous Spatial Surface): 2D wind-steered anisotropic IDW concentration surface with dynamic distance-based opacity decay (45 km to 140 km alpha taper).")
    add_bullet("Layer 1 (District Choropleth & Labels): 41 administrative boundaries colored by PEPC statutory tiers, diagonal polygon cross-hatching for estimated districts, and greedy AABB collision-free label placement.")
    add_bullet("Layer 2 (Vector Wind Field): Planar wind arrows with velocity-proportional scaling; Station 172 suppressed.")
    add_bullet("Layer 3 (Advection Transport Flux & Chevrons): Dynamic Bezier curves showing inter-district mass flux, and 39 border normal chevrons indicating transboundary smoke influx.")
    add_bullet("Layer 4 (Stations & Aerodromes): 79 monitoring stations (including the 13 Lahore micro-network sites) and 12 ICAO aerodromes with interactive click telemetry.")

    add_h2("4.2 The 5-Zone Institutional Console Layout")
    add_bullet("Zone 1 (Top Command Bar): System identity, live streaming vs. offline fallback badge, assertive ARIA live hazard alert, 9-pollutant selector, CSV upload adapter, and QA drawer toggle.")
    add_bullet("Zone 2 (Spatial Control Dock): 5-layer visibility toggles, transboundary mass-balance attribution split bar, and 41-district statutory ranking table with auto-centering.")
    add_bullet("Zone 3 (Planimetric Map Canvas): Strict 2D cartographic view (pitch locked to 0, rotation disabled) covering the Punjab airshed.")
    add_bullet("Zone 4 (Receptor Inspector): Detailed site metadata, 9-parameter sub-index table, 16-sector CPF polar rose (with Nk < 6 sample suppression), and 216-hour QC sparkline chart.")
    add_bullet("Zone 5 (Precision Timeline Scrubber): 216-hour timeline, transport playback controls (1x, 2x, 4x, 8x), max AQI horizon sparkline, and GPU update triggers.")

    add_h2("4.3 The Sub-Hourly Continuous Lerp Engine")
    doc.add_paragraph(
        "A critical engineering innovation is the temporal interpolation engine in src/App.tsx. "
        "Directly coupling 60 FPS requestAnimationFrame canvas loops to React state causes severe reconciler churn and frame drops. "
        "The system decouples them: the requestAnimationFrame loop interpolates time continuously (hourIndex + lerpAlpha) at 60 FPS, "
        "while React state updates are throttled to 15 Hz (~66 ms) or integer hour boundaries. This ensures silky-smooth transport animations "
        "without CPU/GPU thrashing."
    )

    # ==========================================
    # CHAPTER 5: PROS
    # ==========================================
    add_h1("5. Pros of the System as a Whole")
    add_bullet("Every plume stretching, transport arrow, and border chevron represents physical kinematics: anisotropic wind elongation, exponential distance decay mass flux, and vector dot product boundary flux.", "1. Atmospheric Physics Fidelity")
    add_bullet("The workstation boots instantly and functions completely offline using pre-indexed baseline datasets if PostgreSQL or external networks are unavailable. Once connected, it seamlessly upgrades to live streaming.", "2. Air-Gapped Disaster Resilience")
    add_bullet("Adheres to the rigorous '/impeccable' institutional standard: high-contrast WCAG 2.1 AAA color tokens (>= 7.0:1), clean IBM Plex typography, monospaced tabular figures, and zero decorative emojis or 3D pitch distortion.", "3. Institutional UI/UX Ergonomics")
    add_bullet("The custom animation engine throttles React state updates to 15 Hz while interpolating canvas positions at 60 FPS, eliminating frame drops and garbage collection churn.", "4. Sub-Hourly Continuous Scrubbing")
    add_bullet("Built with strict circuit breakers, exponential backoff, and asynchronous fallbacks. A failure in government scrapers or foreign gateways never halts the local dashboard.", "5. Isolated Microservice Reliability")
    add_bullet("Certified by a 144-test opaque-box E2E test suite covering boundary values, mathematical invariants, physical guards, and real-world smog event scenarios.", "6. Comprehensive Verification")

    # ==========================================
    # CHAPTER 6: CONS & LIMITATIONS
    # ==========================================
    add_h1("6. Cons, Systemic Vulnerabilities & Limitations")
    add_bullet("While Punjab covers 205,344 km² and 110 million people, physical regulatory stations are heavily concentrated in Lahore, Faisalabad, and Rawalpindi. Large southern districts (Rajanpur, Layyah) have zero ground monitors and rely entirely on mathematical IDW imputation.", "1. Ground Sensor Scarcity")
    add_bullet("If deployed in basic Linux or Windows environments where PostgreSQL lacks TimescaleDB or PostGIS binaries, the system degrades to standard unpartitioned SQL heap tables and CPU Haversine math, which can degrade query speeds as years of data accumulate.", "2. Database Extension Dependencies")
    add_bullet("The EPA Punjab portal frequently modifies its HTML/JSON output, throttles client IPs, or experiences server crashes during intense smog episodes, requiring ongoing maintenance of scraper headers and fallback paths.", "3. External API Fragility")
    add_bullet("The system uses 2D kinematic mass-flux advection. It does not simulate 3D vertical chemical reactions, such as secondary inorganic aerosol formation (e.g., SO2 and NOx converting into ammonium sulfate/nitrate in high-humidity winter fog).", "4. Absence of 3D Photochemical Modeling")
    add_bullet("The current interactive timeline scrubber is hardcoded to an indexed 216-hour window (9 days). Accessing multi-year historical archives requires querying backend REST endpoints rather than dragging the scrubber.", "5. Scrubber Timeline Horizon Bounds")

    # ==========================================
    # CHAPTER 7: FUTURE ENHANCEMENTS
    # ==========================================
    add_h1("7. Recommended System Enhancements & Engineering Roadmap")
    doc.add_paragraph(
        "To elevate the Punjab Air Quality System into a predictive, proactive environmental command and enforcement center, "
        "the following architectural expansions are recommended:"
    )

    add_bullet("Integrate open-source WRF-Chem or CAMx chemical transport models to project 3D planetary boundary layer heights, nocturnal temperature inversions, and vertical smoke plume trapping.", "1. 3D Eulerian Photochemical Modeling")
    add_bullet("Deploy a Spatio-Temporal Graph Neural Network (ST-GNN) or Temporal Fusion Transformer trained on historical meteorology, satellite fire radiative power, and ground sensors to deliver accurate 24h, 48h, and 72h predictive district AQI forecasts.", "2. AI/ML Predictive Smog Forecasting")
    add_bullet("Incorporate chemical speciation inputs (Black Carbon, PM2.5/PM10 ratios, CO/CO2 combustion indices) with Positive Matrix Factorization (PMF) to dynamically attribute pollution sources (vehicular vs. brick kilns vs. cross-border stubble fires).", "3. Automated Source Apportionment")
    add_bullet("Build a crowd-sourced IoT ingestion gateway with dynamic empirical calibration curves against reference Beta-Attenuation Monitors (BAM-1020), expanding monitoring into rural unmonitored districts.", "4. Low-Cost IoT Sensor Mesh Calibration")
    add_bullet("Automate geofenced webhook dispatch to environmental enforcement squads when industrial corridors exceed emissions limits during stagnant meteorological conditions.", "5. Automated Regulatory Enforcement Webhooks")

    # ==========================================
    # CHAPTER 8: STRATEGIC SUMMARY MATRIX
    # ==========================================
    add_h1("8. Strategic Evaluation & Architecture Matrix")
    matrix_headers = ["Evaluation Dimension", "Current Operational State", "Target Production Enhancement"]
    matrix_widths = [Inches(1.8), Inches(2.5), Inches(2.5)]
    matrix_data = [
        ["Core System Mission", "Institutional atmospheric physics & monitoring workstation", "Predictive policy simulation & enforcement dispatch platform"],
        ["Data Streams", "7 external streams (ground, aviation, synop, model, satellite) + CSV", "Add Sentinel-5P TROPOMI satellite trace gases & IoT meshes"],
        ["Wind Reconciliation", "4-tier wind hierarchy (Station -> METAR -> ECMWF -> IDW)", "3D radiosonde vertical sounding & boundary layer height modeling"],
        ["Spatial Interpolation", "Geodesic IDW (T1) and anisotropic wind-steered IDW (T2)", "Graph Neural Network spatio-temporal machine learning"],
        ["Persistence Architecture", "PostgreSQL 16 + TimescaleDB + PostGIS + Redis Cache", "Multi-node high-availability database cluster with automated retention"],
        ["Cartographic Frontend", "React 18, Deck.gl v8, MapLibre GL v3, WCAG 2.1 AAA, 60 FPS lerp", "Automated PDF regulatory brief generator & mobile enforcement PWA"]
    ]
    matrix_tbl = doc.add_table(rows=1, cols=3)
    format_table(matrix_tbl, matrix_widths, matrix_headers, matrix_data)

    doc.save(str(output_path))
    print(f"Deep brief document successfully generated at: {output_path}")

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    out_file = repo_root / "docs" / "Punjab_Air_Quality_System_Brief.docx"
    generate_full_brief(out_file)
