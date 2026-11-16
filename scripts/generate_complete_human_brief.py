"""
Full, exhaustive, human-centric brief generator with ALL 11 FORMULAS intact,
accompanied by plain-English explanations, physical intuition, variable dictionaries,
worked numerical examples, embedded diagrams, and zero code/file references.
"""

from pathlib import Path
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

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

def add_formula_card(doc, formula_title, formula_text, variable_dict, intuition_text, example_text=None):
    """Adds a dedicated, beautifully formatted card for an exact mathematical formula."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.8)
    set_cell_background(cell, "F8FAFC")
    set_cell_margins(cell, top=140, bottom=140, left=180, right=150)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
            <w:left w:val="single" w:sz="24" w:space="0" w:color="0284C7"/>
            <w:bottom w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
            <w:right w:val="single" w:sz="6" w:space="0" w:color="CBD5E1"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    # Title
    p0 = cell.paragraphs[0]
    p0.paragraph_format.space_before = Pt(0)
    p0.paragraph_format.space_after = Pt(4)
    r_title = p0.add_run(f"FORMULA: {formula_title.upper()}\n")
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(11)
    r_title.font.color.rgb = RGBColor(0x0F, 0x29, 0x42)
    
    # Formula Box (Monospace/Clear style)
    p_form = cell.add_paragraph()
    p_form.paragraph_format.space_before = Pt(4)
    p_form.paragraph_format.space_after = Pt(6)
    p_form.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_form = p_form.add_run(formula_text)
    r_form.bold = True
    r_form.font.name = "Consolas"
    r_form.font.size = Pt(10)
    r_form.font.color.rgb = RGBColor(0x0C, 0x4A, 0x6E)
    
    # Variables breakdown
    p_vars = cell.add_paragraph()
    p_vars.paragraph_format.space_before = Pt(4)
    p_vars.paragraph_format.space_after = Pt(4)
    r_vtitle = p_vars.add_run("Variable Definitions & Physical Units:\n")
    r_vtitle.bold = True
    r_vtitle.font.name = "Calibri"
    r_vtitle.font.size = Pt(9.5)
    r_vtitle.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    
    for var, desc in variable_dict.items():
        p_item = cell.add_paragraph()
        p_item.paragraph_format.space_before = Pt(1)
        p_item.paragraph_format.space_after = Pt(1)
        r_vname = p_item.add_run(f"  • {var}: ")
        r_vname.bold = True
        r_vname.font.name = "Calibri"
        r_vname.font.size = Pt(9)
        r_vname.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
        r_vdesc = p_item.add_run(desc)
        r_vdesc.font.name = "Calibri"
        r_vdesc.font.size = Pt(9)
        r_vdesc.font.color.rgb = RGBColor(0x33, 0x41, 0x55)
        
    # Intuition / Physical Meaning
    p_int = cell.add_paragraph()
    p_int.paragraph_format.space_before = Pt(6)
    p_int.paragraph_format.space_after = Pt(3)
    r_ititle = p_int.add_run("Physical Intuition & Why It Is Built This Way:\n")
    r_ititle.bold = True
    r_ititle.font.name = "Calibri"
    r_ititle.font.size = Pt(9.5)
    r_ititle.font.color.rgb = RGBColor(0x03, 0x69, 0xA1)
    r_idesc = p_int.add_run(intuition_text)
    r_idesc.font.name = "Calibri"
    r_idesc.font.size = Pt(9)
    r_idesc.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    # Walk-through Example
    if example_text:
        p_ex = cell.add_paragraph()
        p_ex.paragraph_format.space_before = Pt(6)
        p_ex.paragraph_format.space_after = Pt(2)
        r_etitle = p_ex.add_run("Step-by-Step Numerical Example:\n")
        r_etitle.bold = True
        r_etitle.font.name = "Calibri"
        r_etitle.font.size = Pt(9.5)
        r_etitle.font.color.rgb = RGBColor(0x15, 0x80, 0x3D)
        r_edesc = p_ex.add_run(example_text)
        r_edesc.font.name = "Calibri"
        r_edesc.font.size = Pt(9)
        r_edesc.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

def format_table(tbl, col_widths, headers, data, header_bg="0F2942", alt_bg="F7FAFC"):
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
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
    run = p.add_run("Punjab Air Quality Information System | Comprehensive Operational & Mathematical Brief — Page ")
    run.font.name = "Calibri"
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x71, 0x80, 0x96)
    
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)

def add_image_figure(doc, img_path: Path, caption: str, width_in_inches=6.2):
    if not img_path.exists():
        return
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(8)
    p_img.paragraph_format.space_after = Pt(2)
    run_img = p_img.add_run()
    run_img.add_picture(str(img_path), width=Inches(width_in_inches))
    
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(0)
    p_cap.paragraph_format.space_after = Pt(10)
    run_cap = p_cap.add_run(f"Figure: {caption}")
    run_cap.font.name = "Calibri"
    run_cap.font.size = Pt(8.5)
    run_cap.font.italic = True
    run_cap.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

def generate_complete_brief(docx_path: Path, diag_dir: Path):
    doc = Document()
    
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

    # --- Document Header ---
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run("PUNJAB AIR QUALITY & ATMOSPHERIC TRANSPORT SYSTEM")
    r_title.bold = True
    r_title.font.size = Pt(21)
    r_title.font.color.rgb = RGBColor(0x0F, 0x29, 0x42)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_after = Pt(6)
    r_sub = p_sub.add_run("Comprehensive Technical & Operational Brief: Full Mathematical Formulations, Physical Intuition, Ingestion Pipelines, and Strategic Evaluation")
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

    # Document Meta Table
    meta_tbl = doc.add_table(rows=2, cols=4)
    meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_w = [Inches(1.5), Inches(1.8), Inches(1.6), Inches(2.1)]
    meta_data = [
        [("Document Type:", "Institutional Master Brief"), ("Target Airshed:", "Punjab Province (PK & IN)"), ("Date:", "November 2026"), ("Focus Areas:", "Physics, Pipelines, & Policy")],
        [("Ingestion Feeds:", "7 Multi-Source Streams"), ("Physics Engine:", "Eulerian Kinematics & IDW"), ("Formulas Included:", "All 11 Math Transforms (T1–T11)"), ("Software Reference:", "Zero Code / Zero Path Citations")]
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
    # CHAPTER 1: THE BIG PICTURE
    # ==========================================
    add_h1("1. The Big Picture: What the System Is Actually Doing")
    
    doc.add_paragraph(
        "Every winter from late October through February, the Punjab plain—home to more than 110 million people in Pakistan "
        "and tens of millions in neighboring Indian states—is smothered under a toxic, motionless dome of smog. "
        "Ambient PM2.5 concentrations routinely exceed 400 to 800 micrograms per cubic meter (µg/m³), ten to twenty times the safety threshold "
        "set by the World Health Organization. Schools close, flights divert, and hospitals see massive surges in acute respiratory distress."
    )

    doc.add_paragraph(
        "Historically, response efforts have been crippled by three critical failures: "
        "first, physical air monitoring stations were few, clustered mostly in Lahore, and frequently broken; "
        "second, official reporting portals crashed when the public needed them most; and third, policymakers engaged in circular disputes "
        "over whether smog was caused by local motor vehicles, industrial brick kilns, or cross-border smoke from Indian crop-stubble burning. "
        "The Punjab Air Quality System was built to eliminate this guesswork with rigorous, real-time, mathematically grounded atmospheric intelligence."
    )

    p2 = diag_dir / "diagram2_inversion_trap.png"
    add_image_figure(doc, p2, "The Atmospheric Trap: Nocturnal Temperature Inversion Trapping Smoke Over the Punjab Basin", 6.2)

    add_callout(
        doc,
        [
            "• The Thermal Trap: The Punjab basin is bordered to the north and east by the Himalayan mountain wall. On clear winter nights, "
            "the Earth's surface radiates heat rapidly into space, cooling the ground-level air. The air above remains warmer. "
            "This warm layer acts like a heavy lid (a nocturnal temperature inversion) trapping cold, dirty air within 150 to 300 meters of the surface. "
            "Surface winds drop below 0.5 meters per second (aerodynamic calm), so pollutants emitted from cars, kilns, and crop fires cannot rise or disperse.",
            "• What This System Does: It operates as an environmental command center. Every hour, it harvests seven independent data feeds "
            "(ground sensors, airports, weather balloons, supercomputer forecasts, and NASA thermal fire satellites), runs them through an automated "
            "data cleaning hospital to remove sensor glitches, calculates missing air quality levels in sensor-less districts using exact physics formulas, "
            "and streams a real-time, 60-frame-per-second interactive map to decision-makers."
        ],
        title="THE SMOG TRAP & SYSTEM MISSION"
    )

    p1 = diag_dir / "diagram1_system_journey.png"
    add_image_figure(doc, p1, "End-to-End System Journey: From Atmospheric Sensors to the Command Workstation", 6.3)

    # ==========================================
    # CHAPTER 2: THE 7 INGESTION PIPELINES
    # ==========================================
    add_h1("2. Detailed Pipeline Architecture: The 7 External Inflow Streams")
    
    doc.add_paragraph(
        "A foundational design principle of this platform is stream independence. If a sensor gets coated in soot, "
        "or a government server crashes, the system does not fail. It treats each data stream as an independent witness:"
    )

    stream_headers = ["Stream Name", "Primary Source", "Physical Measurement", "Collection Frequency", "Key Role in System"]
    stream_widths = [Inches(1.4), Inches(1.3), Inches(1.7), Inches(1.0), Inches(1.4)]
    stream_data = [
        ["1. Ground AQMS", "Government EPA Network", "9 pollutants (PM2.5, PM10, NO2, SO2, CO, O3, NO, NOx, wind)", "Hourly (:05, :15)", "Primary ground-truth measurements across 79 stations"],
        ["2. Airport Weather", "Commercial Aviation METAR", "Surface wind speed, direction, gusts, visibility, fog/smoke codes", "Hourly (:10)", "Calibrated meteorological truth from 12 regional airports"],
        ["3. Synoptic Towers", "WMO GTS Telegrams", "Barometric pressure, temperature, dew point, 10m wind", "Hourly (:15)", "Official meteorological observatory ground truth"],
        ["4. Weather Forecasts", "European ECMWF IFS Model", "10m surface and 925 hPa transport wind vectors (225 nodes)", "Hourly & 6-Hourly", "Fills weather gaps in rural areas and elevated plume transport"],
        ["5. Fire Satellites", "NASA VIIRS Thermal Radiometry", "375m active fire detections, Fire Radiative Power (MW)", "Twice Daily (03, 15 UTC)", "Maps agricultural stubble burning and industrial flaring"],
        ["6. Cross-Border AQMS", "Indian Regional Network", "Border PM2.5 and PM10 concentrations (Amritsar, Delhi)", "Hourly (:20)", "Monitors incoming air masses from upwind Indian airsheds"],
        ["7. Chemical Transport", "Copernicus CAMS Model", "Boundary PM2.5 mass flux along 117 border markers", "Daily Batch (04:00 UTC)", "Calculates total net tons of smoke crossing the frontier"]
    ]
    stream_tbl = doc.add_table(rows=1, cols=5)
    format_table(stream_tbl, stream_widths, stream_headers, stream_data)

    doc.add_paragraph().paragraph_format.space_before = Pt(6)

    # ==========================================
    # CHAPTER 3: ALL 11 FORMULAS EXPLAINED
    # ==========================================
    add_h1("3. The Mathematical Transformation Engine: All 11 Formulas Explained")
    
    doc.add_paragraph(
        "The platform does not rely on arbitrary visual smoothing or artificial graphic effects. "
        "Every number, color contour, transport arrow, and warning icon is derived from eleven deterministic mathematical transformations (T1 through T11). "
        "Below, each exact mathematical formula is provided in full, accompanied by a variable dictionary, physical rationale, and step-by-step numerical walk-through."
    )

    # ----------------------------------------------------
    # TRANSFORM T1
    # ----------------------------------------------------
    add_h2("3.1 Transform T1: Discrete Geodesic Inverse Distance Weighting (District Imputation)")
    doc.add_paragraph(
        "Only 15 of Punjab's 41 districts possess physical monitoring stations. Transform T1 calculates estimated pollutant "
        "concentrations for unmonitored districts by aggregating nearby active monitors using spherical Earth distance."
    )

    t1_formula = (
        "1. Haversine Distance: d = 2 * R * arcsin(sqrt(sin^2(Δφ/2) + cos(φ_t) * cos(φ_i) * sin^2(Δλ/2)))\n"
        "2. Singularity Clamping: d_clamped = max(d, d_0)    where d_0 = 5.0 km\n"
        "3. Weighting:           w_i = 1 / (d_clamped)^p      where p = 2.0\n"
        "4. Estimated Value:     V(t) = Sum(w_i * v_i) / Sum(w_i)"
    )
    t1_vars = {
        "φ_t, λ_t": "Target unmonitored district centroid coordinates (latitude and longitude in radians).",
        "φ_i, λ_i": "Reporting monitoring station coordinates (latitude and longitude in radians).",
        "R": "Radius of the Earth (standard geodetic constant: 6,371.0 kilometers).",
        "d": "True great-circle distance over Earth's spherical surface (in kilometers).",
        "d_0": "Singularity distance clamp (5.0 km). Sets the minimum mathematical distance floor.",
        "p": "Power parameter (p = 2.0). Represents the classical inverse-square law of dispersion.",
        "w_i": "Relative influence weight assigned to reporting station i.",
        "v_i": "Measured pollutant concentration at station i (e.g., PM2.5 in µg/m³)."
    }
    t1_int = (
        "Why distance is squared (p = 2): Like light or gravity, pollutants disperse outward in three dimensions; "
        "as distance doubles, atmospheric dilution drops influence to one-fourth (1/2² = 1/4). Nearby stations dominate strongly.\n"
        "Why the 5.0 km clamp is mandatory: If a sensor happens to be located 100 meters (0.1 km) from a district border, "
        "unclamped distance yields weight 1/(0.1)² = 100, which is 10,000 times larger than a station 10 km away. "
        "A single monitor would completely override all regional trends. Clamping at 5.0 km caps maximum weight at 1/25 = 0.04, "
        "eliminating division-by-zero and ensuring balanced regional estimation."
    )
    t1_ex = (
        "Suppose Kasur centroid (31.1179°N, 74.4460°E) has no sensor. Lahore (35.0 km away) reports 200 µg/m³; Okara (70.0 km away) reports 100 µg/m³.\n"
        "• d_Lahore = max(35.0, 5.0) = 35.0 km  -->  w_Lahore = 1 / (35)² = 1 / 1225 = 0.000816\n"
        "• d_Okara  = max(70.0, 5.0) = 70.0 km  -->  w_Okara  = 1 / (70)² = 1 / 4900 = 0.000204\n"
        "• Sum of weights = 0.000816 + 0.000204 = 0.001020\n"
        "• Estimated Kasur PM2.5 = ((0.000816 * 200) + (0.000204 * 100)) / 0.001020 = (0.1632 + 0.0204) / 0.001020 = 180.0 µg/m³."
    )
    add_formula_card(doc, "T1: Discrete Geodesic IDW", t1_formula, t1_vars, t1_int, t1_ex)

    p3 = diag_dir / "diagram3_idw_math.png"
    add_image_figure(doc, p3, "How Inverse Distance Weighting Operates and Why the 5.0 km Safety Clamp Prevents Singularities", 6.2)

    # ----------------------------------------------------
    # TRANSFORM T2
    # ----------------------------------------------------
    add_h2("3.2 Transform T2: Anisotropic Wind-Steered Continuous Surface IDW")
    doc.add_paragraph(
        "Standard mapping software generates symmetrical circular halos around sensors. In reality, wind carries pollution downwind, "
        "stretching plumes into elongated ovals. Transform T2 dynamically deforms the interpolation kernel along the prevailing wind vector."
    )

    t2_formula = (
        "1. Base Euclidean Weight:   w_{0, i} = 1 / (d_i^2 + ε^2)    where ε = 4.0 px (ε^2 = 16.0 px^2)\n"
        "2. Wind Alignment Cosine:   cos(α_i) = (Δx_i * u_i - Δy_i * v_i) / (d_i * s_i)\n"
        "3. Anisotropic Modulation:  ψ_i = 1.0 + 0.70 * cos(α_i) * min(1.0, s_i / 1.5 m/s)\n"
        "4. Effective Plume Weight:  w_i = w_{0, i} * max(0.30, ψ_i)\n"
        "5. Distance Opacity Decay:  α_channel(km) decays linearly from 235 (at 45 km) to 95 (at 140 km)"
    )
    t2_vars = {
        "d_i": "Screen distance in pixels from pixel (x, y) to station (x_i, y_i): d_i = sqrt(Δx² + Δy²).",
        "ε": "Kernel smoothing constant (4.0 pixels). Prevents pixel-level graininess right over station coordinates.",
        "u_i, v_i": "Orthogonal Cartesian wind components (in meters per second). u is east-west, v is north-south.",
        "s_i": "Scalar wind speed: s_i = sqrt(u_i² + v_i²).",
        "α_i": "Angle between displacement vector (Δx, Δy) and the advective wind vector (u, -v).",
        "cos(α_i)": "Directional alignment factor (+1.0 directly downwind, 0.0 crosswind, -1.0 directly upwind).",
        "ψ_i": "Dynamic wind-steering multiplier (ranges from 0.30 up to 1.70).",
        "α_channel": "Alpha transparency channel (0–255), tapering color in data-sparse rural territories."
    }
    t2_int = (
        "Why cos(α) is used: If a point is directly downwind (α = 0°), cos(0°) = +1.0, boosting weight by up to +70% (ψ = 1.70). "
        "If a point is directly upwind (α = 180°), cos(180°) = -1.0, attenuating weight down to a floor of 0.30 (-70% reduction). "
        "Why wind speed scales with min(1.0, s_i / 1.5): In calm air (0.3 m/s), wind cannot push plumes far, so elongation is minor. "
        "At 1.5 m/s (~5.4 km/h), full physical plume elongation is achieved."
    )
    t2_ex = (
        "Station reports wind blowing East at 3.0 m/s (u = 3.0, v = 0.0). Consider two points 20 pixels away:\n"
        "• Downwind Point (East, Δx = +20, Δy = 0): cos(α) = (20*3) / (20*3) = +1.0. ψ = 1.0 + 0.70(1.0)(1.0) = 1.70. Weight boosted 70%.\n"
        "• Upwind Point (West, Δx = -20, Δy = 0): cos(α) = (-20*3) / (20*3) = -1.0. ψ = 1.0 - 0.70 = 0.30. Weight cut by 70%."
    )
    add_formula_card(doc, "T2: Anisotropic Wind-Steered IDW", t2_formula, t2_vars, t2_int, t2_ex)

    p4 = diag_dir / "diagram4_plume_and_flux.png"
    add_image_figure(doc, p4, "Wind-Steered Plume Dispersion and Inter-District Advection Transport Mass Flux", 6.3)

    # ----------------------------------------------------
    # TRANSFORM T3
    # ----------------------------------------------------
    add_h2("3.3 Transform T3: Planar Screen Raster IDW (5-Pixel Grid Cells)")
    doc.add_paragraph(
        "To deliver smooth 60 FPS rendering on client browsers without GPU memory overload, the system computes a downsampled "
        "5-pixel raster grid across the provincial bounding box."
    )

    t3_formula = (
        "Raster Weight: w_k = 1.0 / (d_k + ε)^p    where p = 3.0, ε = 0.5 px\n"
        "Pixel Value:   C(x, y) = Sum(w_k * C_k) / Sum(w_k)"
    )
    t3_vars = {
        "d_k": "Screen Euclidean pixel distance from the center of cell (x, y) to monitor k.",
        "ε": "Sub-pixel singularity softening offset (0.5 pixels).",
        "p": "Cubic falloff power (p = 3.0). Sharpens localized urban gradients in dense station clusters."
    }
    t3_int = (
        "Why cubic power (p = 3) is used on screen: In dense urban clusters like Lahore (13 stations in close proximity), "
        "a power of 2 creates excessive blurring between industrial zones and green residential parks. "
        "A cubic falloff power preserves local micro-airshed boundaries without sacrificing computational speed."
    )
    add_formula_card(doc, "T3: Planar Screen Raster IDW", t3_formula, t3_vars, t3_int)

    # ----------------------------------------------------
    # TRANSFORM T4
    # ----------------------------------------------------
    add_h2("3.4 Transform T4: Vector Wind Blending & Cartesian Kinematics")
    doc.add_paragraph(
        "Weather vanes record wind in polar coordinates (speed in m/s, direction in degrees from true North). "
        "To calculate advection, these polar values must be decomposed into orthogonal Cartesian velocity vectors."
    )

    t4_formula = (
        "1. Cartesian Components: u = -w_s * sin(θ * π / 180),    v = -w_s * cos(θ * π / 180)\n"
        "2. Physical Sanity:      0.0 <= w_s <= 30.0 m/s,         0.0° <= θ <= 360.0°\n"
        "3. Surface Roughness:    u_cal = u * K_R,                v_cal = v * K_R    where K_R = 0.22686\n"
        "4. Hardware Blacklist:   Station 172 (Wazirabad) --> FORCE u = null, v = null"
    )
    t4_vars = {
        "w_s": "Scalar wind speed (in meters per second). Clamped at 30.0 m/s (severe storm limit).",
        "θ": "Meteorological wind direction (degrees from true North, 0°–360°). Represents the direction wind blows FROM.",
        "u": "Zonal velocity component (East-West flow; positive = blowing East).",
        "v": "Meridional velocity component (North-South flow; positive = blowing North).",
        "K_R": "Surface roughness scaling factor (0.22686). Reconciles unobstructed forecast winds with ground friction."
    }
    t4_int = (
        "Why the negative signs exist: In meteorology, a 'North wind' (θ = 0°) means the wind blows FROM the North TOWARD the South. "
        "Its motion vector must point negative on the y-axis (v < 0). The negative signs convert from 'direction from' to 'velocity toward'.\n"
        "The Wazirabad Rule: A mechanical survey revealed that Station 172 in Wazirabad was mounted with a 140° physical offset. "
        "Transform T4 mechanically suppresses wind rendering for Station 172 while preserving its particulate readings."
    )
    t4_ex = (
        "Wind blows FROM the East (θ = 90°) at 5.0 m/s:\n"
        "• u = -5.0 * sin(90°) = -5.0 * 1.0 = -5.0 m/s (moving Westward)\n"
        "• v = -5.0 * cos(90°) = -5.0 * 0.0 =  0.0 m/s (zero North-South motion)\n"
        "Smoke is accurately propelled toward the West."
    )
    add_formula_card(doc, "T4: Vector Wind Blending", t4_formula, t4_vars, t4_int, t4_ex)

    # ----------------------------------------------------
    # TRANSFORM T5
    # ----------------------------------------------------
    add_h2("3.5 Transform T5: 16-Sector Conditional Probability Function (CPF) Wind Rose")
    doc.add_paragraph(
        "To identify which compass direction pollution originates from, Transform T5 couples hourly pollutant peaks "
        "with directional wind vectors into a 16-sector polar wind rose."
    )

    t5_formula = (
        "1. Sector Classification: Sector k = floor((θ + 11.25°) / 22.5°) mod 16    for k in [0..15]\n"
        "2. Probability Score:     CPF_k = m_k / N_k\n"
        "3. Calm Exclusion Rule:   IF w_s < 0.50 m/s --> EXCLUDE from directional bins; add to calm_count\n"
        "4. Suppression Guard:     IF N_k < 6 valid hours --> FORCE CPF_k = null"
    )
    t5_vars = {
        "θ": "Hourly wind direction in degrees (0°–360°).",
        "k": "One of 16 compass sectors (0 = North, 4 = East, 8 = South, 12 = West).",
        "N_k": "Total count of hours where wind blew from sector k with speed w_s >= 0.50 m/s.",
        "m_k": "Count of hours in sector k where concentration exceeded the 75th percentile threshold (τ = P_75).",
        "CPF_k": "Conditional Probability (0.0 to 1.0) that wind from sector k brings severe smog."
    }
    t5_int = (
        "Why calm air is excluded: When wind speed is under 0.50 m/s, wind vanes swing randomly without true directional transport. "
        "Including calm air would create false spikes in random directions.\n"
        "Why N_k < 6 suppresses the sector: If wind blew from the East for only 2 hours during the entire week, and both hours happened to be high, "
        "raw math would yield a probability of 2/2 = 1.0 (100%), creating a massive visual spike on the rose based on statistically meaningless data. "
        "The system requires at least 6 valid hours before rendering a sector."
    )
    add_formula_card(doc, "T5: 16-Sector CPF Wind Rose", t5_formula, t5_vars, t5_int)

    # ----------------------------------------------------
    # TRANSFORM T6
    # ----------------------------------------------------
    add_h2("3.6 Transform T6: Inter-District Advection Mass Flux")
    doc.add_paragraph(
        "Transform T6 models physical mass transport between all 41 administrative districts, quantifying whether one district "
        "is actively exporting pollution into another."
    )

    t6_formula = (
        "1. Raw Flux Link:     Flux_{A->B} = C_A * w_A * cos(Δθ) * exp(-d_{AB} / 100 km)\n"
        "2. Distance Cutoff:   d_{AB} <= 180.0 km    (if distance > 180 km --> Flux = null)\n"
        "3. Directional Cone:  Δθ <= 35.0°           (if wind alignment > 35° --> Flux = null)\n"
        "4. Dimension Guard:   IF Pollutant == 'AQI' --> RETURN [] (Mass flux disabled for dimensionless index)"
    )
    t6_vars = {
        "C_A": "Upwind source district particulate concentration (in µg/m³).",
        "w_A": "Upwind source district wind speed (in m/s).",
        "d_{AB}": "Haversine distance between district centroid A and district centroid B (in km).",
        "Δθ": "Angular divergence between the compass bearing from A to B and the prevailing wind vector.",
        "cos(Δθ)": "Advective alignment factor (1.0 = direct alignment, drops to zero at 90°).",
        "exp(-d/100)": "Atmospheric dilution, settling, and deposition decay over a 100 km scale length."
    }
    t6_int = (
        "Why the 35° cone exists: If wind blows from Lahore toward Faisalabad, Kasur (which lies to the south) cannot receive the smoke. "
        "The 35° cone strictly limits transport to true downwind corridors.\n"
        "The Physical Dimension Guard: You can move physical micrograms of dust across a boundary, but you cannot physically transport "
        "a composite 'AQI number'. AQI is a non-linear statutory rating. If an operator selects 'AQI', the system automatically "
        "suppresses flux arrows to prevent displaying scientifically invalid figures."
    )
    t6_ex = (
        "Lahore Town Hall (PM2.5 = 450 µg/m³, wind = 2.5 m/s toward Sheikhupura, d = 35 km, Δθ = 5°):\n"
        "• Alignment: cos(5°) = 0.996\n"
        "• Distance Decay: exp(-35 / 100) = exp(-0.35) = 0.705\n"
        "• Mass Flux = 450 * 2.5 * 0.996 * 0.705 = 789.9 µg·m/(m³·s). Represents massive, concentrated inter-district smoke transport."
    )
    add_formula_card(doc, "T6: Inter-District Advection Mass Flux", t6_formula, t6_vars, t6_int, t6_ex)

    # ----------------------------------------------------
    # TRANSFORM T7
    # ----------------------------------------------------
    add_h2("3.7 Transform T7: Receptor CPF Pathway Coupling & Transport Balance")
    doc.add_paragraph(
        "To separate true pollution highways from random breeze links, Transform T7 weights advection flux by the receptor "
        "district's historical probability rose."
    )

    t7_formula = (
        "1. Pathway Score:    Score_{A->B} = Flux_{A->B} * Ω_B(θ_{BA})    (fallback Ω = 0.25 if unmonitored)\n"
        "2. Visual Filter:    Retain only the TOP 60 scored pathway links across the province\n"
        "3. Net Mass Balance: Net Transport_i = Sum_{j}(Flux_{i->j}) - Sum_{k}(Flux_{k->i})"
    )
    t7_vars = {
        "Ω_B": "Receptor district B's CPF polar rose probability for wind arriving from the direction of source A.",
        "θ_{BA}": "Compass bearing from receptor B looking back toward source A.",
        "Net Transport": "Net balance for district i. Positive values indicate net EXPORTERS; negative values indicate net IMPORTERS."
    }
    t7_int = (
        "Why coupling is required: If Lahore has high smoke and wind blows toward Gujranwala, but Gujranwala's historical sensor rose "
        "shows that high smog never occurs when winds blow from Lahore, the link is suppressed as an anomaly. "
        "Truncating to the top 60 links prevents the map from turning into an unreadable spiderweb of lines."
    )
    add_formula_card(doc, "T7: Receptor Pathway Coupling", t7_formula, t7_vars, t7_int)

    # ----------------------------------------------------
    # TRANSFORM T8
    # ----------------------------------------------------
    add_h2("3.8 Transform T8: Transboundary Border Belt & Normal Chevrons")
    doc.add_paragraph(
        "Transform T8 monitors the 1,100 km international border with India, evaluating whether cross-border plumes "
        "are actively crossing into Pakistan."
    )

    t8_formula = (
        "1. Border Dot Product:  Φ_j = w_j · n_j = u_j * nx_j + v_j * ny_j    for j in [1..39]\n"
        "2. Inflow Trigger:      IF Φ_j > +0.25 m/s --> ACTIVATE CRIMSON CHEVRON at node j\n"
        "3. Transboundary Flux:  Boundary Flux_j = C_{CAMS, j} * Φ_j\n"
        "4. 120km Belt Index:    D_border = (1/M) * Sum_{d in Belt} C_d"
    )
    t8_vars = {
        "w_j = (u_j, v_j)": "Surface wind vector at border checkpoint j (in meters per second).",
        "n_j = (nx_j, ny_j)": "Inward-pointing unit normal vector perpendicular to the international boundary.",
        "Φ_j": "Normal inflow velocity component across the border (positive = into Pakistan).",
        "C_{CAMS, j}": "Copernicus atmospheric model PM2.5 concentration at border coordinate node j.",
        "D_border": "Average pollution concentration across all districts within 120 km of the international boundary."
    }
    t8_int = (
        "Why the dot product is used: Winds blowing parallel to the border (North to South) carry zero smoke across the boundary. "
        "The dot product extracts only the perpendicular velocity component crossing the border line. "
        "A threshold of +0.25 m/s (~1 km/h) eliminates zero-wind noise and flags genuine transboundary transport events."
    )
    add_formula_card(doc, "T8: Transboundary Normal Chevrons", t8_formula, t8_vars, t8_int)

    # ----------------------------------------------------
    # TRANSFORM T9
    # ----------------------------------------------------
    add_h2("3.9 Transform T9: Statutory PEPC Air Quality Index Scale & Breakpoints")
    doc.add_paragraph(
        "Transform T9 converts continuous physical pollutant concentrations into statutory regulatory health categories "
        "mandated by the Punjab Environmental Protection Council (PEPC)."
    )

    t9_formula = (
        "1. Piecewise Linear Sub-index:\n"
        "   I_p = ((I_high - I_low) / (BP_high - BP_low)) * (C_p - BP_low) + I_low\n"
        "   evaluated over continuous half-open intervals: (BP_low, BP_high]\n"
        "\n"
        "2. Operational Ceiling Clamp:\n"
        "   IF PM2.5 > 350.0 µg/m³ --> FORCE AQI = 500 (Hazardous, Deep Maroon #7E0023)\n"
        "\n"
        "3. Particulate Dominance Composite:\n"
        "   Composite AQI = max(I_{PM2.5}, I_{PM10})"
    )
    t9_vars = {
        "C_p": "Measured particulate or gas concentration (in µg/m³ or mg/m³ for CO).",
        "BP_low, BP_high": "Lower and upper concentration boundaries for the matched statutory tier.",
        "I_low, I_high": "Lower and upper index boundaries for the matched statutory tier (e.g., 51 to 100).",
        "I_p": "Calculated sub-index value for pollutant p (rounded to nearest integer)."
    }
    t9_int = (
        "Why the 500 ceiling clamp exists: In winter 2024, sensationalist media headlines proclaimed 'AQI reached 1,900 in Lahore'. "
        "Under international epidemiological standards, the AQI scale has an absolute ceiling at 500 ('Hazardous'). "
        "At 350 µg/m³ of PM2.5, the air is already maximally hazardous to all humans; scaling the index up to 1,500 causes panic "
        "without providing any additional medical guidance.\n"
        "Why half-open intervals (BP_low, BP_high] matter: A concentration of exactly 15.0 µg/m³ falls into Category 0 (Good, AQI 50). "
        "A reading of 15.001 µg/m³ crosses into Category 1 (Satisfactory). Half-open intervals eliminate category ambiguity."
    )
    t9_ex = (
        "A monitor records PM2.5 = 75.0 µg/m³. The PEPC breakpoint table defines Moderate as (35.0, 75.0] µg/m³ mapping to (101, 150] AQI:\n"
        "• BP_low = 35.0, BP_high = 75.0\n"
        "• I_low = 101, I_high = 150\n"
        "• AQI = ((150 - 101) / (75.0 - 35.0)) * (75.0 - 35.0) + 101 = (49 / 40.0) * 40.0 + 101 = 49 + 101 = 150 (Moderate/Poor boundary)."
    )
    add_formula_card(doc, "T9: Statutory PEPC AQI Scale", t9_formula, t9_vars, t9_int, t9_ex)

    p5 = diag_dir / "diagram5_pepc_aqi_scale.png"
    add_image_figure(doc, p5, "Official PEPC Air Quality Index Scale and the Statutory 500 Hazardous Ceiling Clamp", 6.2)

    # ----------------------------------------------------
    # TRANSFORM T10
    # ----------------------------------------------------
    add_h2("3.10 Transform T10: Temporal Aggregation, Automated QC Cleaning & Sub-Hourly Lerp")
    doc.add_paragraph(
        "Sensor hardware is prone to electrical noise, telemetry dropouts, and computer lockups. "
        "Transform T10 acts as the automated hospital ward, cleaning raw numbers before they enter the modeling pipeline."
    )

    t10_formula = (
        "1. Zero Suppression:        IF C <= 0.0 --> C = null\n"
        "2. 7-Hour Median Spike:     IF v_i > 4 * M_i  AND  v_i > 3 * ref_p --> v_i = null\n"
        "3. 3-Hour Logger Hold:      IF i >= 2 AND v_i == v_{i-1} == v_{i-2} --> v_i = null (AQI exempt)\n"
        "4. 75% Completeness Rule:   N_valid >= max(1, round(0.75 * H))\n"
        "5. Sub-Hourly Lerp:         C(t) = (1 - α) * C_h + α * C_{h+1}    where α = t - floor(t)"
    )
    t10_vars = {
        "M_i": "Rolling 7-hour median concentration centered on hour i.",
        "ref_p": "Statutory reference threshold (e.g., 35 µg/m³ for PM2.5, 100 for AQI).",
        "i >= 2": "Array index safety guard preventing negative-index wraparound on hold checks.",
        "H": "Target rollup window in hours (e.g., H = 24 hours for daily average).",
        "α": "Fractional timeline scrub position (0.0 to 1.0) enabling smooth sub-hourly interpolation."
    }
    t10_int = (
        "Why AQI is exempt from the 3-hour hold rule: If a physical sensor reports 142.30 µg/m³ for three consecutive hours to two decimal places, "
        "its analog-to-digital converter is frozen. But an integer AQI index can legitimately sit at 500 for days during an inversion crisis. "
        "Purging identical AQI readings would create false gaps during disaster emergencies.\n"
        "The 75% Rule: To compute a valid daily average (H = 24), a station must report at least round(0.75 * 24) = 18 valid hours. "
        "If it reports 17 hours, the daily rollup returns null, preventing partial-day averages from skewing health records."
    )
    add_formula_card(doc, "T10: Temporal QC & Sub-Hourly Lerp", t10_formula, t10_vars, t10_int)

    # ----------------------------------------------------
    # TRANSFORM T11
    # ----------------------------------------------------
    add_h2("3.11 Transform T11: Geographic Projection & Greedy AABB Collision-Free Labeling")
    doc.add_paragraph(
        "Because Punjab sits at approximately 31° North latitude, standard flat computer mapping distorts distance. "
        "Transform T11 projects coordinates accurately and places text labels without overlapping neighboring cities."
    )

    t11_formula = (
        "1. Plate Carrée Projection:\n"
        "   x = (λ - λ_0) * cos(31.0° * π / 180) * S,    y = -(φ - φ_0) * S\n"
        "   where K_X = cos(31.0°) ≈ 0.85717\n"
        "\n"
        "2. Greedy AABB Collision Search:\n"
        "   Overlap Condition: |x_A - x_B| < (w_A + w_B)/2  AND  |y_A - y_B| < (h_A + h_B)/2\n"
        "   Evaluates 12 candidate radial offsets; if offset > 20 px --> RENDER LEADER LINE"
    )
    t11_vars = {
        "φ, λ": "Geographic latitude and longitude in decimal degrees.",
        "φ_0, λ_0": "Canvas center coordinates (Punjab central anchor: 31.17°N, 72.70°E).",
        "S": "Map scaling factor (pixels per degree of latitude).",
        "K_X": "Longitude compression aspect ratio (cos 31° ≈ 0.85717). Corrects east-west distance squishing.",
        "w, h": "Width and height of the text bounding box in pixels."
    }
    t11_int = (
        "Why K_X = cos(31°) matters: Lines of longitude converge as you move away from the equator. At 31° North (Punjab's latitude), "
        "one degree of longitude is only 85.7% as wide as one degree of latitude. Without K_X, Punjab would appear unnaturally stretched east-to-west.\n"
        "Greedy AABB Labeling: In dense regions like Lahore, Kasur, and Sheikhupura, city names overlap and become unreadable. "
        "The system tests 12 radial offset angles to find collision-free space. If pushed more than 20 pixels away, it draws a clean leader line "
        "connecting the text label back to the district center."
    )
    add_formula_card(doc, "T11: Projection & Collision Labeling", t11_formula, t11_vars, t11_int)

    # ==========================================
    # CHAPTER 4: INTEGRATION & ARCHITECTURE
    # ==========================================
    add_h1("4. Pipeline Integration: How the Disparate Pieces Form a Unified Whole")
    
    doc.add_paragraph(
        "Collecting seven data streams is useless if they cannot communicate. The system unifies them through two "
        "critical engineering concepts:"
    )

    add_h2("4.1 The Chronometric Staging Buffer: Synchronizing Time")
    doc.add_paragraph(
        "Different feeds arrive at different times: satellites report twice a day, airports report at 10 minutes past the hour, "
        "and ground sensors transmit on erratic schedules. "
        "The Chronometric Staging Buffer acts as a holding lounge. It gathers all incoming packets for target UTC hour T_H. "
        "Once the hour closes, it locks the dataset, runs the quality control cleaners (T10), applies the mathematical transforms (T1–T9), "
        "and writes a single, atomic, synchronized snapshot to the central database and high-speed memory cache."
    )

    add_h2("4.2 The 4-Tier Wind Backup Generator")
    doc.add_paragraph(
        "Wind is the heartbeat of pollution modeling. If wind data is missing, advection flux cannot be calculated. "
        "The system implements an automated 4-tier fallback generator:"
    )
    add_bullet("Tier 1: Ground Station Vane. Checked for physical validity and hardware blacklists. If valid, it is used.", "First Choice")
    add_bullet("Tier 2: Nearest Airport Weather Feed. If the ground sensor is broken, the system looks for an active commercial airport within 40 kilometers.", "Second Choice")
    add_bullet("Tier 3: European Supercomputer Model. If no airport is nearby, it pulls the district's ECMWF forecast vector, calibrated for ground friction.", "Third Choice")
    add_bullet("Tier 4: Mathematical Spatial Estimation. If internet forecasts fail, it interpolates wind vectors from distant reporting stations using geodesic math.", "Final Failsafe")

    # 4-tier table
    add_h2("4.3 Four-Tier Software Architecture")
    arch_headers = ["Layer", "Plain-English Role", "Key Mechanism", "User Benefit"]
    arch_widths = [Inches(1.2), Inches(1.8), Inches(2.2), Inches(1.6)]
    arch_data = [
        ["Tier 1: Collection", "Automated multi-source harvester", "Independent background workers with timeouts and retry budgets", "If one provider crashes, no other stream is affected"],
        ["Tier 2: Core Brain", "Data hospital & physics engine", "Relational time-series tables, spatial geometry engine, fast memory cache", "Stores years of hourly data with sub-5ms lookup speeds"],
        ["Tier 3: Delivery", "Real-time communication gateway", "Lightweight streaming channels pushing delta updates (<20 KB)", "Instant map updates without refreshing the browser"],
        ["Tier 4: Workstation", "Institutional decision console", "Strict 2D cartography, 5 visual overlays, 60 FPS time scrubber", "Crystal-clear policy insights with zero visual clutter"]
    ]
    arch_tbl = doc.add_table(rows=1, cols=4)
    format_table(arch_tbl, arch_widths, arch_headers, arch_data)

    doc.add_paragraph().paragraph_format.space_before = Pt(6)

    # ==========================================
    # CHAPTER 5: PROS & CONS
    # ==========================================
    add_h1("5. System Pros, Cons, and Systemic Limitations")
    
    add_h2("5.1 Pros: Key Strengths of the Platform")
    add_bullet("Unlike commercial consumer dashboards that draw generic circular heatmaps, every line and color is grounded in atmospheric physics (Eulerian advection, wind steering, and distance decay).", "1. Genuine Scientific Integrity")
    add_bullet("If the central database or external internet fails entirely, the workstation boots instantly in 'Air-Gapped Offline Mode', serving pre-indexed baseline records so disaster response teams can continue operating during blackouts.", "2. Air-Gapped Disaster Resilience")
    add_bullet("Built for government and scientific command rooms: high-contrast WCAG 2.1 AAA accessible color tokens (>=7:1 contrast ratio), clean monospaced numbers that do not jitter during playback, and zero distracting consumer emojis or tilted 3D angles.", "3. Institutional Command Ergonomics")
    add_bullet("With the 4-tier wind fallback, 7-hour spike cleaner, 3-hour freeze detector, and the 5.0 km IDW clamp, erratic sensor bugs are caught before they reach the public or leadership.", "4. Defensive Error Protection")
    add_bullet("The entire mathematical and operational suite is certified by an opaque-box test harness passing 144 out of 144 comprehensive end-to-end test scenarios.", "5. Fully Verified & Tested")

    add_h2("5.2 Cons & Honest Real-World Limitations")
    add_bullet("Punjab covers over 205,000 square kilometers, but physical monitoring stations are overwhelmingly concentrated in three cities: Lahore, Faisalabad, and Rawalpindi. Large southern districts like Rajanpur, Layyah, and Bhakkar have zero monitors. While IDW estimation is mathematically optimal, it cannot detect hyper-local rural point sources, such as illegal waste burning or isolated factory clusters.", "1. The 'Sensor Desert' Reality")
    add_bullet("The platform calculates 2D surface advection. It does not model vertical mixing heights or complex 3D photochemical reactions—such as sulfur dioxide gas converting into sulfate particles under humid winter sunlight.", "2. Absence of 3D Photochemical Modeling")
    add_bullet("Government websites change their formatting, block automated queries, or crash under heavy traffic. While the system has robust fallbacks, web-scraping public portals remains inherently fragile compared to dedicated private telemetry lines.", "3. Public Scraping Fragility")
    add_bullet("Demonstrating cross-border smoke transport is politically sensitive. While the system's border normal chevrons and wind vectors provide objective physical evidence of incoming plumes, local sources (millions of motorbikes, thousands of brick kilns) also contribute heavily. The tool must be used to foster cross-border environmental cooperation, not diplomatic deflection.", "4. Transboundary Attribution Sensitivity")
    add_bullet("The live scrubber currently operates across an indexed 216-hour horizon (9 days). Accessing multi-year historical archives requires querying backend database endpoints rather than dragging the continuous scrubber.", "5. 9-Day Scrubber Horizon")

    # ==========================================
    # CHAPTER 6: FUTURE ENHANCEMENTS
    # ==========================================
    add_h1("6. Recommended Strategic Enhancements & Future Roadmap")
    doc.add_paragraph(
        "To transition the workstation from a real-time diagnostic dashboard into a predictive, interventionist environmental "
        "command center, the following five engineering initiatives are recommended:"
    )
    add_bullet("Couple the platform with open-source 3D chemical transport models (like WRF-Chem) to simulate vertical boundary layer heights, nocturnal thermal traps, and chemical transformations in the atmosphere.", "1. 3D Atmospheric Chemistry Modeling")
    add_bullet("Train a Spatio-Temporal Graph Neural Network (ST-GNN) on historical weather, satellite fire power, and sensor readings to deliver 24h, 48h, and 72h predictive district AQI forecasts with confidence bands. This enables proactive 'green lockdowns' before hazardous peaks occur.", "2. AI-Powered Early Warning Smog Forecasts")
    add_bullet("Deploy chemical speciation monitors (measuring Black Carbon, PM2.5/PM10 ratios, and carbon monoxide ratios) combined with Positive Matrix Factorization (PMF) to dynamically compute what percentage of smog at any hour is caused by vehicular traffic vs. brick kilns vs. crop residue burning.", "3. Automated Source Apportionment")
    add_bullet("Deploy low-cost optical particle sensors across schools and clinics in unmonitored rural districts, with automatic calibration against central government reference monitors. This would expand sensing density from 79 to over 500 nodes.", "4. Low-Cost Community Sensor Mesh")
    add_bullet("Configure geofenced automated SMS and webhook alerts dispatched to environmental protection enforcement squads whenever industrial zones exceed particulate limits during calm nocturnal inversions.", "5. Automated Field Enforcement Dispatch")

    # ==========================================
    # CHAPTER 7: STRATEGIC MATRIX
    # ==========================================
    add_h1("7. Strategic Summary: Current Reality vs. Next-Gen Capability")
    
    matrix_headers = ["Strategic Dimension", "What the System Does Today", "Recommended Next Horizon"]
    matrix_widths = [Inches(1.8), Inches(2.5), Inches(2.5)]
    matrix_data = [
        ["Core Mission", "Real-time atmospheric monitoring, geostatistical interpolation, & transboundary tracking", "Predictive policy simulation, early warning health alerts, & enforcement dispatch"],
        ["Data Feeds", "7 diverse streams (ground, airport, synoptic, weather model, satellite, regional, continental)", "Integrate Sentinel-5P satellite gas sensors & 500+ rural community IoT monitors"],
        ["Meteorology", "4-tier wind fallback hierarchy (Station -> Airport -> Forecast -> Math)", "Full 3D atmospheric boundary layer height and vertical radiosonde soundings"],
        ["Mathematical Modeling", "All 11 deterministic transforms (T1–T11): IDW, anisotropic plumes, Eulerian mass flux", "Spatio-temporal Graph Neural Networks for 72-hour predictive forecasting"],
        ["System Resilience", "Air-gapped offline baseline mode + high-speed database/cache backend", "High-availability geo-distributed cloud cluster with automated retention policies"],
        ["Presentation", "Institutional 2D map console with 60 FPS sub-hourly scrubber & 5 visual layers", "Automated daily executive PDF briefing generator & mobile field inspector client"]
    ]
    matrix_tbl = doc.add_table(rows=1, cols=3)
    format_table(matrix_tbl, matrix_widths, matrix_headers, matrix_data)

    doc.save(str(docx_path))
    print(f"Master brief with ALL 11 FORMULAS and DIAGRAMS successfully saved at: {docx_path}")

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    diagrams_dir = repo_root / "docs" / "diagrams"
    out_file = repo_root / "docs" / "Punjab_Air_Quality_System_Brief.docx"
    generate_complete_brief(out_file, diagrams_dir)
