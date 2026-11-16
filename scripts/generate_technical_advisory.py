"""
Automated Generator for Statutory Technical Advisory and Cover Letter (.docx).
Adheres strictly to official 26 May EPA Punjab letterhead standards and Times New Roman typography.
Produces:
  1. docs/Technical_Advisory_Smog_Episode_10Nov2026.docx
  2. docs/Cover_Letter_Technical_Advisory_10Nov2026.docx
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import List, Tuple

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


def set_cell_background(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color.lstrip("#")}"/>')
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


def add_callout_box(doc, text_lines: List[str], title: str = None, border_color: str = "0F2942", bg_color: str = "F7FAFC"):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.8)
    set_cell_background(cell, bg_color)
    set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
    
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="none"/>
            <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color.lstrip("#")}"/>
            <w:bottom w:val="none"/>
            <w:right w:val="none"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    if title:
        run_title = p.add_run(title + "\n")
        run_title.bold = True
        run_title.font.name = "Times New Roman"
        run_title.font.size = Pt(11)
        run_title.font.color.rgb = RGBColor(0x0F, 0x29, 0x42)
        
    for i, line in enumerate(text_lines):
        if i > 0 or title:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
        run = p.add_run(line)
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0x2D, 0x37, 0x48)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def add_official_letterhead(doc, serial_num: str = "EPA/DIREMC/O/261110/0412"):
    """
    Renders standardized 26 May Punjab Government EPA Letterhead.
    """
    # Header
    p_gov = doc.add_paragraph()
    p_gov.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_gov = p_gov.add_run("GOVERNMENT OF THE PUNJAB\n")
    r_gov.bold = True
    r_gov.font.name = "Times New Roman"
    r_gov.font.size = Pt(14)
    r_gov.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    r_epa = p_gov.add_run("ENVIRONMENTAL PROTECTION AGENCY (EPA)\n")
    r_epa.bold = True
    r_epa.font.name = "Times New Roman"
    r_epa.font.size = Pt(12)
    r_epa.font.color.rgb = RGBColor(0x1A, 0x36, 0x5D)

    r_dir = p_gov.add_run("DIRECTORATE GENERAL OF ENVIRONMENTAL MONITORING & CONTROL\nGate No. 8, National Hockey Stadium, Qaddafi Stadium Complex, Ferozepur Road, Lahore\n")
    r_dir.font.name = "Times New Roman"
    r_dir.font.size = Pt(9.5)
    r_dir.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

    # Dividing Line
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(0)
    p_div.paragraph_format.space_after = Pt(8)
    r_div = p_div.add_run("―" * 68)
    r_div.font.name = "Times New Roman"
    r_div.font.color.rgb = RGBColor(0x00, 0x33, 0x66)

    # Serial and Date Table
    tbl = doc.add_table(rows=1, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.rows[0].cells[0].width = Inches(4.5)
    tbl.rows[0].cells[1].width = Inches(2.3)

    p_serial = tbl.rows[0].cells[0].paragraphs[0]
    r_s1 = p_serial.add_run(f"No. {serial_num}")
    r_s1.bold = True
    r_s1.font.name = "Times New Roman"
    r_s1.font.size = Pt(10)

    p_date = tbl.rows[0].cells[1].paragraphs[0]
    p_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_d1 = p_date.add_run(f"Dated Lahore, the 10th November, 2026")
    r_d1.font.name = "Times New Roman"
    r_d1.font.size = Pt(10)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)


def generate_technical_advisory(output_path: Path = None) -> Path:
    if output_path is None:
        output_path = Path("docs") / "Technical_Advisory_Smog_Episode_10Nov2026.docx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    add_official_letterhead(doc, serial_num="EPA/DIREMC/O/261110/0814")

    # Subject
    p_subj = doc.add_paragraph()
    r_subj_lbl = p_subj.add_run("SUBJECT: ")
    r_subj_lbl.bold = True
    r_subj_lbl.font.name = "Times New Roman"
    r_subj_lbl.font.size = Pt(11)
    
    r_subj = p_subj.add_run("STATUTORY TECHNICAL ADVISORY ON CRITICAL SMOG EMERGENCY EPISODE & MULTI-SECTORAL MANDATORY MITIGATION CONTROLS")
    r_subj.bold = True
    r_subj.underline = True
    r_subj.font.name = "Times New Roman"
    r_subj.font.size = Pt(11)

    p_body = doc.add_paragraph()
    r_body = p_body.add_run(
        "In exercise of statutory powers conferred under the Punjab Environmental Protection Act 1997 "
        "(amended 2012) and in response to unprecedented regional atmospheric stagnation, severe nocturnal "
        "temperature inversion, and transboundary particulate advection across the Indo-Gangetic Plains, "
        "the Environmental Protection Agency (EPA) Punjab hereby issues the following mandatory technical "
        "advisory and emergency sectoral intervention directives for immediate compliance across all 41 districts."
    )
    r_body.font.name = "Times New Roman"
    r_body.font.size = Pt(10.5)

    # Sector Directives
    sectors = [
        ("SECTOR A: TRANSPORT & TRAFFIC CONGESTION MANAGEMENT", [
            "1. Immediate ban on entry of heavy diesel vehicles (3+ axles) into urban metropolitan centers from 06:00 to 22:00 PKT.",
            "2. Mandatory deployment of smoke-meter inspection squads along Ring Roads, GT Road corridors, and Motorway interchanges.",
            "3. Enactment of odd-even vehicle movement rationing within Lahore, Faisalabad, and Gujranwala municipal boundaries.",
            "4. Anti-idling enforcement at all major educational and commercial choke points under Section 16 PEPA 1997.",
        ], "C00000"),
        ("SECTOR B: INDUSTRIAL EMISSIONS & AIR POLLUTION CONTROL SYSTEMS (APCS)", [
            "1. 100% immediate shutdown of un-scrubbed steel re-rolling mills, secondary lead smelters, and rubber/pyrolysis oil furnaces.",
            "2. Mandatory operational certification of wet scrubbers and bag-house filtration units with continuous telemetry logging.",
            "3. Nighttime surveillance by anti-smog squads with power disconnection mandates for non-compliant industrial units in Quaid-e-Azam, Sundar, and Kot Lakhpat estates.",
        ], "ED7D31"),
        ("SECTOR C: AGRICULTURAL STUBBLE BURNING & TRANSBOUNDARY INFLOW", [
            "1. Strict enforcement of Section 144 CrPC prohibiting all residue burning in paddy/rice cultivation belts.",
            "2. Utilization of satellite telemetry (NASA VIIRS 375m) for real-time FIRMS hotspot detection and geo-fenced police FIR dispatch.",
            "3. Provision of subsidized Happy Seeders and Super Straw Management Systems (SSMS) in border districts (Kasur, Narowal, Nankana, Sheikhupura).",
        ], "7030A0"),
        ("SECTOR D: BRICK KILNS CONVERSION & ZIG-ZAG COMPLIANCE", [
            "1. Total operational prohibition of traditional Bull's Trench Kilns (BTK) across Punjab territory.",
            "2. Continuous compliance monitoring of induced-draft Zig-Zag kilns; mandatory closure of any kiln emitting opacity exceeding Ringelmann Scale 2.",
            "3. Drone-based aerial thermal imaging surveillance over Sheikhupura, Kasur, and Multan kiln clusters.",
        ], "0F2942"),
        ("SECTOR E: MUNICIPAL SERVICES, EDUCATION & PUBLIC HEALTH ALERTS", [
            "1. Transition of all public and private schools to 50% hybrid/online attendance mode in red-tier districts.",
            "2. Deployment of mechanized vacuum sweepers and high-pressure anti-smog water misting cannons along arterial corridors.",
            "3. Mandatory N95 mask advisory for vulnerable demographics (children, elderly, respiratory patients) and closure of outdoor recreational venues.",
        ], "22543D"),
    ]

    for title, items, color in sectors:
        add_callout_box(doc, items, title=title, border_color=color, bg_color="FAFAFA")

    # Signoff Block
    p_sig = doc.add_paragraph()
    p_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sig.paragraph_format.space_before = Pt(12)
    
    r_sig1 = p_sig.add_run("DIRECTOR GENERAL\n")
    r_sig1.bold = True
    r_sig1.font.name = "Times New Roman"
    r_sig1.font.size = Pt(11)
    
    r_sig2 = p_sig.add_run("Environmental Protection Agency, Punjab\nGovernment of the Punjab")
    r_sig2.font.name = "Times New Roman"
    r_sig2.font.size = Pt(10)

    # CC Section
    p_cc = doc.add_paragraph()
    r_cc_lbl = p_cc.add_run("A copy is forwarded for information and necessary executive enforcement to:\n")
    r_cc_lbl.bold = True
    r_cc_lbl.font.name = "Times New Roman"
    r_cc_lbl.font.size = Pt(9.5)

    cc_recipients = [
        "1. The Chief Secretary, Government of the Punjab, Lahore.",
        "2. The Secretary, Environment Protection & Climate Change Department, Lahore.",
        "3. The Inspector General of Police (IGP), Punjab, Lahore (for Section 144 compliance).",
        "4. All Divisional Commissioners and Deputy Commissioners in Punjab.",
        "5. The Managing Director, Punjab Mass Transit Authority.",
        "6. Office Copy.",
    ]
    for c in cc_recipients:
        p_c = doc.add_paragraph()
        p_c.paragraph_format.space_before = Pt(0)
        p_c.paragraph_format.space_after = Pt(1)
        r_c = p_c.add_run(c)
        r_c.font.name = "Times New Roman"
        r_c.font.size = Pt(9)

    doc.save(str(output_path))
    return output_path


def generate_cover_letter(output_path: Path = None) -> Path:
    if output_path is None:
        output_path = Path("docs") / "Cover_Letter_Technical_Advisory_10Nov2026.docx"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    add_official_letterhead(doc, serial_num="EPA/DIREMC/O/261110/0815")

    # Addressee
    p_to = doc.add_paragraph()
    r_to = p_to.add_run(
        "To:\n"
        "    The Chief Secretary,\n"
        "    Government of the Punjab,\n"
        "    Civil Secretariat, Lahore.\n"
    )
    r_to.bold = True
    r_to.font.name = "Times New Roman"
    r_to.font.size = Pt(11)

    p_subj = doc.add_paragraph()
    r_subj_lbl = p_subj.add_run("SUBJECT: ")
    r_subj_lbl.bold = True
    r_subj_lbl.font.name = "Times New Roman"
    r_subj_lbl.font.size = Pt(11)
    
    r_subj = p_subj.add_run("SUBMISSION OF PROVINCIAL TECHNICAL ADVISORY & REAL-TIME SMOG ACTION MATRIX (10 NOVEMBER 2026)")
    r_subj.bold = True
    r_subj.underline = True
    r_subj.font.name = "Times New Roman"
    r_subj.font.size = Pt(11)

    p_body = doc.add_paragraph()
    body_text = (
        "I am directed to refer to the ongoing environmental emergency across the central plains of Punjab and "
        "to enclose herewith the comprehensive Technical Advisory on the severe smog episode of 10th November 2026, "
        "formulated on the basis of multi-sensor scientific surveillance from the Punjab Air Quality Information System.\n\n"
        "The scientific surveillance integrates continuous ground telemetry from 79 AQMS stations, NOAA aviation METAR "
        "reports from 12 commercial and military aerodromes, planetary boundary layer (PBL) mixing layer profiles, and "
        "satellite transboundary fire detections. The telemetry demonstrates critical nocturnal inversions (<150m AGL) "
        "coupled with easterly advection flux, resulting in Hazardous PEPC Tier 7 air quality in Lahore, Kasur, and Gujranwala.\n\n"
        "Immediate inter-departmental enforcement of the prescribed Sectors A through E mitigatory controls is respectfully "
        "solicited to avert severe public health hazards and atmospheric deterioration."
    )
    r_body = p_body.add_run(body_text)
    r_body.font.name = "Times New Roman"
    r_body.font.size = Pt(10.5)

    p_sig = doc.add_paragraph()
    p_sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sig.paragraph_format.space_before = Pt(18)
    
    r_sig1 = p_sig.add_run("DIRECTOR GENERAL\n")
    r_sig1.bold = True
    r_sig1.font.name = "Times New Roman"
    r_sig1.font.size = Pt(11)
    
    r_sig2 = p_sig.add_run("Environmental Protection Agency, Punjab\nGovernment of the Punjab")
    r_sig2.font.name = "Times New Roman"
    r_sig2.font.size = Pt(10)

    doc.save(str(output_path))
    return output_path


if __name__ == "__main__":
    t_out = generate_technical_advisory()
    c_out = generate_cover_letter()
    print(f"[SUCCESS] Generated Technical Advisory: {t_out}")
    print(f"[SUCCESS] Generated Cover Letter: {c_out}")
