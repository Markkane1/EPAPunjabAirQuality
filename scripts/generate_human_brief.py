"""
Script to generate publication-grade visual diagrams and assemble a
human-centric, explainable Word document for the Punjab Air Quality System.
Zero code file references, rich diagrams, and plain-English formula breakdowns.
"""

import os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

# ---------------------------------------------------------------------------
# 1. DIAGRAM GENERATION
# ---------------------------------------------------------------------------

def generate_diagrams(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ----------------------------------------------------
    # Diagram 1: System Dataflow Architecture
    # ----------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis('off')
    
    # Background card
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#FFFFFF')
    
    # Define boxes: x, y, w, h, color, title, subtitle
    stages = [
        (0.4, 1.2, 2.0, 3.8, '#EBF8FF', '#2B6CB0', '1. DATA COLLECTION\n(7 Diverse Sources)', 
         '• 79 Ground Air Monitors\n• 12 Airport Weather Feeds\n• 7 Synoptic Observatories\n• European Weather Model\n• NASA Fire Satellites\n• Indian Border Monitors\n• Continental Chemistry'),
        (2.8, 1.2, 2.0, 3.8, '#FEFCBF', '#B7791F', '2. DATA HOSPITAL\n(QC & Wind Backup)', 
         '• Zero & Negative Purge\n• 7-Hour Spike Filter\n• Frozen Sensor Detection\n• Broken Vane Blacklist\n• 4-Tier Wind Backup\n  (Sensor → Airport →\n   Forecast → Math)'),
        (5.2, 1.2, 2.0, 3.8, '#E6FFFA', '#234E52', '3. PHYSICS ENGINE\n(Math Transforms)', 
         '• Geodesic IDW (No Gaps)\n• Wind-Steered Plumes\n• Inter-District Flux\n• Transboundary Inflow\n• 16-Sector CPF Roses\n• Official PEPC AQI Scale\n• 500 Ceiling Clamp'),
        (7.6, 1.2, 2.0, 3.8, '#FAF5FF', '#6B46C1', '4. COMMAND MAP\n(Decision Screen)', 
         '• Real-Time Live Push\n• 5 Visual GPU Layers\n• 60 FPS Time Scrubber\n• Interactive Inspector\n• High-Contrast Colors\n• Air-Gapped Offline Mode\n  (Works without Internet)')
    ]
    
    for x, y, w, h, bg, border, title, desc in stages:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.15",
                                      facecolor=bg, edgecolor=border, linewidth=2.0)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.5, title, ha='center', va='center', fontsize=9, fontweight='bold', color='#1A202C')
        ax.text(x + 0.15, y + h - 1.0, desc, ha='left', va='top', fontsize=7.5, color='#2D3748', linespacing=1.4)

    # Arrows between stages
    arrows = [(2.45, 3.1, 2.75, 3.1), (4.85, 3.1, 5.15, 3.1), (7.25, 3.1, 7.55, 3.1)]
    for x1, y1, x2, y2 in arrows:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color="#4A5568", lw=2.5, mutation_scale=15))

    ax.set_title("End-to-End System Journey: From Atmospheric Sensors to Policy Decision Console", 
                 fontsize=12, fontweight='bold', color='#0F2942', pad=15)
    
    fig.tight_layout()
    path1 = output_dir / "diagram1_system_journey.png"
    fig.savefig(path1, bbox_inches='tight', dpi=300)
    plt.close(fig)

    # ----------------------------------------------------
    # Diagram 2: Atmospheric Inversion & Smog Trap
    # ----------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis('off')
    
    # Ground profile
    ground_x = np.linspace(0, 10, 100)
    ground_y = 0.5 + 0.1 * np.sin(ground_x * 1.5)
    ground_y[ground_x > 8.0] += (ground_x[ground_x > 8.0] - 8.0) * 1.2  # Himalayan foothills
    ax.fill_between(ground_x, 0, ground_y, color='#718096')
    ax.text(1.5, 0.25, "Lahore / Central Punjab Basin", color='white', fontweight='bold', fontsize=8.5)
    ax.text(8.3, 0.4, "Himalayan Foothills", color='white', fontweight='bold', fontsize=8)

    # Temperature Inversion Layer (The Thermal Lid)
    lid_y = 2.2
    rect_lid = patches.Rectangle((0, lid_y), 10, 0.35, facecolor='#ECC94B', alpha=0.85, edgecolor='#D69E2E', lw=1.5)
    ax.add_patch(rect_lid)
    ax.text(5.0, lid_y + 0.17, "TEMPERATURE INVERSION LID (WARM AIR TRAP: 150m – 300m ALTITUDE)", 
            ha='center', va='center', fontweight='bold', fontsize=8.5, color='#744210')

    # Warm free atmosphere above
    ax.fill_between([0, 10], [lid_y + 0.35, lid_y + 0.35], [5, 5], color='#EBF8FF', alpha=0.7)
    ax.text(5.0, 3.8, "Upper Atmosphere: Warmer, Buoyant Air Masses (Prevents Smoke from Rising)", 
            ha='center', va='center', fontsize=9, color='#2B6CB0', fontstyle='italic')

    # Trapped Smog Pool below lid
    ax.fill_between(ground_x, ground_y, lid_y, color='#C53030', alpha=0.35)
    ax.text(4.5, 1.4, "TRAPPED TOXIC SMOG POOL\nPM2.5 > 350 µg/m³ | Calm Winds (< 0.5 m/s)\nPollution cannot escape vertically or horizontally", 
            ha='center', va='center', fontweight='bold', fontsize=9, color='#742A2A',
            bbox=dict(boxstyle="round,pad=0.3", fc="#FFF5F5", ec="#E53E3E", lw=1))

    # Sources of pollution
    ax.annotate("Vehicular Traffic & Industrial Kilns\n(Local Primary Emissions)", xy=(2.0, 0.65), xytext=(1.5, 1.8),
                arrowprops=dict(arrowstyle="->", color="#9B2C2C", lw=1.5), fontsize=7.5, color="#742A2A", fontweight='bold')
    
    ax.annotate("Cross-Border Agricultural\nStubble Fires (Easterly Plumes)", xy=(7.2, 0.8), xytext=(6.5, 1.8),
                arrowprops=dict(arrowstyle="->", color="#C05621", lw=1.5), fontsize=7.5, color="#7B341E", fontweight='bold')

    ax.set_title("The Regional Atmospheric Trap: How Temperature Inversions Create Winter Smog", 
                 fontsize=11.5, fontweight='bold', color='#0F2942', pad=12)

    fig.tight_layout()
    path2 = output_dir / "diagram2_inversion_trap.png"
    fig.savefig(path2, bbox_inches='tight', dpi=300)
    plt.close(fig)

    # ----------------------------------------------------
    # Diagram 3: Mathematical Concept - IDW & 5km Clamp
    # ----------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), dpi=300)
    
    # Left subplot: Map intuition
    ax1.set_xlim(-10, 10)
    ax1.set_ylim(-10, 10)
    ax1.set_aspect('equal')
    ax1.axis('off')
    
    # Target unmonitored district
    ax1.plot(0, 0, marker='*', markersize=18, color='#E53E3E', label='Target District (Unmonitored)')
    ax1.text(0, -1.5, "Target District\n(No Sensors)", ha='center', fontsize=8.5, fontweight='bold', color='#9B2C2C')
    
    # Surrounding monitors
    stations = [
        (4, 5, 220, "Station A (7 km)\n220 µg/m³\nHigh Weight"),
        (-6, 3, 110, "Station B (9 km)\n110 µg/m³\nMedium Weight"),
        (2, -7, 180, "Station C (11 km)\n180 µg/m³\nLower Weight"),
        (-5, -6, 85, "Station D (14 km)\n85 µg/m³\nWeak Weight")
    ]
    for sx, sy, val, lbl in stations:
        ax1.plot(sx, sy, marker='o', markersize=12, color='#2B6CB0')
        ax1.annotate('', xy=(0, 0), xytext=(sx, sy),
                     arrowprops=dict(arrowstyle="->", linestyle="dashed", color="#4A5568", lw=1.8))
        ax1.text(sx, sy + 1.0, lbl, ha='center', fontsize=7.5, color='#1A365D')

    ax1.set_title("1. Spatial Concept: Closer Stations Exert\nExponentially Stronger Pull (1 / Distance²)", 
                  fontsize=9.5, fontweight='bold', color='#0F2942')

    # Right subplot: Weight curve & 5km clamp
    dist = np.linspace(0.1, 40, 400)
    weight_unclamped = 1.0 / (dist ** 2)
    dist_clamped = np.maximum(dist, 5.0)
    weight_clamped = 1.0 / (dist_clamped ** 2)

    ax2.plot(dist, weight_clamped, color='#2B6CB0', lw=2.5, label='Actual System Weight (5 km Clamp)')
    ax2.plot(dist[dist < 5.0], weight_unclamped[dist < 5.0], color='#E53E3E', lw=2, linestyle='dotted', label='Unclamped Flaw (Approaches Infinity)')
    ax2.axvline(5.0, color='#DD6B20', linestyle='--', lw=1.5, label='5.0 km Safety Boundary')
    ax2.scatter([5.0], [1.0/25.0], color='#DD6B20', s=60, zorder=5)
    ax2.annotate('Safe Cap: Weight = 0.04\nPrevents single station takeover', xy=(5.0, 1.0/25.0), xytext=(12, 0.06),
                 arrowprops=dict(arrowstyle="->", color="#C05621", lw=1.5), fontsize=8, color="#7B341E", fontweight='bold')

    ax2.set_xlabel("Distance to Monitoring Station (Kilometers)", fontsize=8.5, fontweight='bold')
    ax2.set_ylabel("Influence Weight (w)", fontsize=8.5, fontweight='bold')
    ax2.set_ylim(0, 0.12)
    ax2.set_xlim(0, 35)
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(fontsize=7.5, loc='upper right')
    ax2.set_title("2. Mathematical Safety: The 5 km Singularity Clamp\nEliminates Division-by-Zero", 
                  fontsize=9.5, fontweight='bold', color='#0F2942')

    fig.tight_layout()
    path3 = output_dir / "diagram3_idw_math.png"
    fig.savefig(path3, bbox_inches='tight', dpi=300)
    plt.close(fig)

    # ----------------------------------------------------
    # Diagram 4: Wind-Steered Plume & Inter-District Flux
    # ----------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), dpi=300)
    
    # Left subplot: Wind-steered anisotropic plume
    ax1.set_xlim(-8, 8)
    ax1.set_ylim(-8, 8)
    ax1.set_aspect('equal')
    ax1.axis('off')
    
    # Central Station
    ax1.scatter([0], [0], color='#0F2942', s=120, zorder=10)
    ax1.text(0, -1.2, "Reporting Station", ha='center', fontsize=8, fontweight='bold', color='#0F2942')

    # Draw wind arrow (blowing to the East-North-East)
    ax1.annotate('', xy=(5.5, 2.5), xytext=(0, 0),
                 arrowprops=dict(arrowstyle="-|>", color="#C53030", lw=3.0, mutation_scale=20))
    ax1.text(3.5, 0.8, "Prevailing Wind\nDirection (Advection)", fontsize=8, fontweight='bold', color='#C53030')

    # Plume contours
    ellipse1 = patches.Ellipse((2.2, 1.0), 7.5, 3.8, angle=24, facecolor='#FEB2B2', alpha=0.5, edgecolor='#E53E3E', lw=1.5)
    ellipse2 = patches.Ellipse((1.2, 0.5), 4.5, 2.4, angle=24, facecolor='#FC8181', alpha=0.6, edgecolor='#C53030', lw=1.5)
    ellipse3 = patches.Ellipse((0.4, 0.2), 2.2, 1.3, angle=24, facecolor='#E53E3E', alpha=0.7, edgecolor='#9B2C2C', lw=1.5)
    ax1.add_patch(ellipse1)
    ax1.add_patch(ellipse2)
    ax1.add_patch(ellipse3)

    ax1.text(5.2, 3.6, "Downwind: +70% Amplification\n(Smoke travels with wind)", fontsize=7.5, fontweight='bold', color='#9B2C2C')
    ax1.text(-5.5, -2.5, "Upwind: -70% Attenuation\n(Clean air moving in)", fontsize=7.5, fontweight='bold', color='#2B6CB0')
    ax1.set_title("1. Wind-Steered Plume (Anisotropic IDW)\nPlume Stretches Along Wind Direction", 
                  fontsize=9.5, fontweight='bold', color='#0F2942')

    # Right subplot: Inter-district transport flux cone
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')
    
    # Source district
    ax2.scatter([2], [5], color='#C53030', s=140, zorder=10)
    ax2.text(2, 4.0, "Source District\n(e.g., Lahore)\nHigh Pollution (C_A)", ha='center', fontsize=8, fontweight='bold', color='#742A2A')

    # Receptor in cone
    ax2.scatter([7.5], [6.5], color='#2B6CB0', s=120, zorder=10)
    ax2.text(7.5, 7.2, "Receptor in Cone\n(e.g., Sheikhupura)\nReceives Massive Flux!", ha='center', fontsize=8, fontweight='bold', color='#2C5282')
    
    # Receptor out of cone
    ax2.scatter([6.5], [1.5], color='#718096', s=80, zorder=10)
    ax2.text(6.5, 0.6, "District Outside Cone\n(Flux = 0.0: Wind not blowing here)", ha='center', fontsize=7.5, color='#4A5568')

    # Cone lines
    ax2.plot([2, 8.5], [5, 7.5], color='#ED8936', linestyle='--', lw=1.5)
    ax2.plot([2, 8.5], [5, 2.5], color='#ED8936', linestyle='--', lw=1.5)
    ax2.fill([2, 8.5, 8.5], [5, 7.5, 2.5], color='#FEEBC8', alpha=0.35)
    ax2.text(5.0, 5.0, "35° Transport Cone\n(Distance ≤ 180 km)", ha='center', fontsize=8, color='#C05621', fontweight='bold')

    # Transport vector
    ax2.annotate('', xy=(7.2, 6.3), xytext=(2.3, 5.1),
                 arrowprops=dict(arrowstyle="-|>", color="#9B2C2C", lw=3.0, mutation_scale=20))

    ax2.set_title("2. Inter-District Mass Flux (Eulerian Advection)\nCalculates Tons of Pollution Blown Across Districts", 
                  fontsize=9.5, fontweight='bold', color='#0F2942')

    fig.tight_layout()
    path4 = output_dir / "diagram4_plume_and_flux.png"
    fig.savefig(path4, bbox_inches='tight', dpi=300)
    plt.close(fig)

    # ----------------------------------------------------
    # Diagram 5: Official PEPC AQI Scale & 500 Ceiling Rule
    # ----------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=300)
    ax.set_xlim(0, 520)
    ax.set_ylim(0, 3)
    ax.axis('off')

    tiers = [
        (0, 50, '#00E400', 'Good\n(0–50)', 'Safe for all'),
        (50, 100, '#92D050', 'Satisfactory\n(51–100)', 'Minor irritation'),
        (100, 150, '#FFFF00', 'Moderate\n(101–150)', 'Sensitive groups'),
        (150, 200, '#FF7E00', 'Poor\n(151–200)', 'Unhealthy for all'),
        (200, 300, '#FF0000', 'Very Poor\n(201–300)', 'Severe respiratory'),
        (300, 400, '#99004C', 'Severe\n(301–400)', 'Emergency measures'),
        (400, 500, '#7E0023', 'Hazardous (Clamped)\n(401–500)', 'Health crisis')
    ]

    for start, end, color, label, desc in tiers:
        width = end - start
        rect = patches.Rectangle((start, 1.0), width, 1.0, facecolor=color, edgecolor='#2D3748', lw=1.2)
        ax.add_patch(rect)
        ax.text(start + width/2, 1.5, label, ha='center', va='center', fontsize=7.5, fontweight='bold',
                color='black' if color in ['#00E400', '#92D050', '#FFFF00'] else 'white')
        ax.text(start + width/2, 0.6, desc, ha='center', va='center', fontsize=6.5, color='#4A5568')

    # Draw 500 clamp marker
    ax.annotate("STATUTORY CEILING CLAMP AT 500\nTriggered whenever PM2.5 > 350 µg/m³\nPrevents infinite meaningless index escalation", 
                xy=(500, 2.0), xytext=(360, 2.6),
                arrowprops=dict(arrowstyle="->", color="#7E0023", lw=2), fontsize=8, fontweight='bold', color="#7E0023",
                bbox=dict(boxstyle="round,pad=0.3", fc="#FFF5F5", ec="#7E0023", lw=1.5))

    ax.set_title("Official Punjab Environmental Protection Council (PEPC) Air Quality Index Scale", 
                 fontsize=11, fontweight='bold', color='#0F2942', pad=10)

    fig.tight_layout()
    path5 = output_dir / "diagram5_pepc_aqi_scale.png"
    fig.savefig(path5, bbox_inches='tight', dpi=300)
    plt.close(fig)

    print(f"All 5 visual diagrams successfully generated in: {output_dir}")
    return path1, path2, path3, path4, path5

# ---------------------------------------------------------------------------
# 2. WORD DOCUMENT ASSEMBLY
# ---------------------------------------------------------------------------

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
    run = p.add_run("Punjab Air Quality Information System | Human-Centric Explainable Brief — Page ")
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

def build_human_centric_document(docx_path: Path, diag_paths: tuple):
    p1, p2, p3, p4, p5 = diag_paths
    
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

    # --- Title Banner ---
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run("PUNJAB AIR QUALITY & ATMOSPHERIC TRANSPORT SYSTEM")
    r_title.bold = True
    r_title.font.size = Pt(21)
    r_title.font.color.rgb = RGBColor(0x0F, 0x29, 0x42)

    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_after = Pt(6)
    r_sub = p_sub.add_run("Plain-English Operational Brief: Understanding What the System Does, How the Physics Works, and Strategic Next Steps")
    r_sub.font.size = Pt(11)
    r_sub.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)

    # Document Meta Table
    meta_tbl = doc.add_table(rows=2, cols=4)
    meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_w = [Inches(1.5), Inches(1.8), Inches(1.6), Inches(2.1)]
    meta_data = [
        [("Document Purpose:", "Human-Centric System Brief"), ("Target Audience:", "Leadership, Policy, & Science"), ("Date:", "November 2026"), ("Scope:", "Punjab Province (PK & IN)")],
        [("Core Capability:", "Real-Time Smog Intelligence"), ("Data Sources:", "7 Multi-Source Streams"), ("Physics Grounding:", "Eulerian Kinematics & IDW"), ("Operation Mode:", "Live & Air-Gapped Offline")]
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
    # CHAPTER 1: WHAT THE SYSTEM ACTUALLY DOES
    # ==========================================
    add_h1("1. The Big Picture: What the System Is Actually Doing")
    
    doc.add_paragraph(
        "Every winter between October and February, a catastrophic blanket of toxic smog descends upon the Punjab plains, "
        "home to more than 110 million people in Pakistan and tens of millions in neighboring Indian states. "
        "Air quality monitors frequently report PM2.5 levels exceeding 400 to 800 micrograms per cubic meter—ten to twenty times "
        "the safe limits established by the World Health Organization. Schools are forced to close, hospitals overflow with "
        "respiratory emergencies, and daily life grinds to a halt."
    )

    doc.add_paragraph(
        "Before this system was built, authorities and citizens faced an information crisis: "
        "official government monitoring stations were few and frequently broke down, public websites crashed under heavy traffic, "
        "and disputes raged over whether the smog was caused by local traffic, brick kilns, or cross-border crop burning. "
        "The Punjab Air Quality System was built to replace rumor and lagging charts with undeniable, mathematically grounded, "
        "real-time atmospheric intelligence."
    )

    add_image_figure(doc, p2, "The Atmospheric Trap: Nocturnal Temperature Inversion Trapping Smoke Over the Punjab Basin", 6.2)

    add_callout(
        doc,
        [
            "• Why Winter Smog Happens: The Punjab basin is surrounded by the Himalayas to the north and east. During clear winter nights, "
            "the ground cools rapidly, chilling the air right at the surface. Meanwhile, higher air stays warm. This warm air acts like a heavy lid "
            "(a 'temperature inversion') trapping cold, dirty air within 150 to 300 meters of the ground. Because winds drop to almost zero (<0.5 m/s), "
            "pollutants emitted from traffic, factories, and burning fields cannot rise or blow away—they stew in place.",
            "• What This System Does: It acts as an environmental air traffic control center. Every single hour, it pulls data from the skies, "
            "airports, weather models, and satellites; filters out sensor lies and frozen equipment; fills in gaps for districts with zero sensors "
            "using physics formulas; and projects a live, interactive map that reveals where pollution is coming from, where it is blowing, "
            "and who is responsible."
        ],
        title="UNDERSTANDING THE CRISIS & THE SYSTEM'S MISSION"
    )

    add_image_figure(doc, p1, "The 4-Stage Data Journey: From Satellite and Surface Feeds to the Command Screen", 6.3)

    # ==========================================
    # CHAPTER 2: THE 7 DATA PIPELINES (PLAIN ENGLISH)
    # ==========================================
    add_h1("2. The Data Inflow: Explaining Each Pipeline in Plain Terms")
    
    doc.add_paragraph(
        "To build an accurate picture of air pollution, you cannot rely on a single source. If a sensor gets coated in soot, "
        "or a website goes down, or a cloud blocks a satellite, your system must not go blind. The platform continuously ingests "
        "and cross-verifies seven independent data streams, treating them like witnesses in an investigation:"
    )

    add_h2("2.1 Ground Air Monitoring Stations (EPA Punjab Network)")
    doc.add_paragraph(
        "This stream connects to 79 physical air quality monitoring stations (74 permanently installed across major cities like Lahore, "
        "Faisalabad, and Rawalpindi, and 5 mobile laboratory vans). Every hour, these machines measure nine distinct pollutants: "
        "fine particles (PM2.5), coarse dust (PM10), nitrogen dioxide (NO2), sulfur dioxide (SO2), carbon monoxide (CO), ozone (O3), "
        "nitric oxide (NO), total nitrogen oxides (NOx), and wind speed/direction. "
        "Because this government website frequently crashes during smog crises, the system uses an automated backup query: "
        "if the main summary page fails, it quietly queries individual district endpoints in parallel, bounding total wait time to under 15 seconds."
    )

    add_h2("2.2 Commercial Airport Weather Stations (Aviation METAR Feeds)")
    doc.add_paragraph(
        "Airports are home to the most rigorously calibrated, reliable weather sensors in the world because pilot lives depend on them. "
        "The system taps directly into international aviation weather reports from 12 regional airports, including Lahore International (OPLA), "
        "Multan, Faisalabad, Sialkot, Islamabad, and Amritsar International in India (VIAR). "
        "These stations provide pristine ground-truth wind speed, wind direction, visibility, and present weather codes "
        "(identifying whether reduced visibility is caused by fog, smoke, or dry dust)."
    )

    add_h2("2.3 Official Meteorological Observatories (WMO Synoptic Bulletins)")
    doc.add_paragraph(
        "Under international treaties, government weather bureaus broadcast global telegraphic telegrams every hour via the World "
        "Meteorological Organization (WMO). The system intercepts and decodes these telegraphic messages from seven primary observatories "
        "(such as Lahore PBO, Multan, and Sialkot). They provide barometric surface pressure, air temperature, and high-precision 10-meter "
        "anemometer winds, serving as a secondary truth check against commercial airport feeds."
    )

    add_h2("2.4 European Supercomputer Weather Forecasts (ECMWF IFS Model)")
    doc.add_paragraph(
        "Even with airports and ground stations, vast rural areas have no physical weather towers. To see the wind everywhere, the system "
        "queries the European Centre for Medium-Range Weather Forecasts (ECMWF)—widely considered the world's most accurate numerical weather model. "
        "It pulls 10-meter surface winds for all 41 district centers, as well as high-altitude winds at 925 hPa (~750 meters above the ground). "
        "High-altitude winds show where smoke plumes travel once they rise above local trees and buildings."
    )

    add_h2("2.5 NASA Satellite Active Fire Detection (VIIRS Thermal Sensors)")
    doc.add_paragraph(
        "Twice daily, NASA satellites (NOAA-20 and Suomi-NPP) sweep over South Asia. Equipped with thermal infrared cameras (VIIRS), "
        "they detect heat anomalies on the ground at a 375-meter resolution. The system scans a geographic box covering Punjab, Haryana, "
        "and Rajasthan, counting crop stubble fires, measuring their Fire Radiative Power (in Megawatts), and filtering out industrial gas flares "
        "so that agricultural fires are accurately mapped."
    )

    add_h2("2.6 Cross-Border Regional Sensors (Indian Airshed Network)")
    doc.add_paragraph(
        "Air recognizes no political borders. Smog in Lahore is heavily influenced by conditions in Amritsar, Jalandhar, Bathinda, and New Delhi. "
        "The system ingests hourly sensor readings from Indian monitoring stations along the border. To prevent 'apples-to-oranges' comparisons, "
        "it recalculates Indian raw particle measurements using the official Punjab PEPC scale so officials can view regional pollution "
        "under a single, uniform standard."
    )

    add_h2("2.7 Continental Chemical Transport Reanalysis (Copernicus CAMS)")
    doc.add_paragraph(
        "Operated by the European Union, the Copernicus Atmosphere Monitoring Service (CAMS) models atmospheric chemistry on a continental scale. "
        "The system reads particulate concentrations along 117 coordinate markers spaced along the 1,100-kilometer international border. "
        "By combining CAMS smoke density with local wind vectors, it calculates the net tons of particulate matter entering or leaving the country."
    )

    # ==========================================
    # CHAPTER 3: FORMULAS EXPLAINED FOR HUMANS
    # ==========================================
    add_h1("3. The Mathematics Explained: How the Formulas Work in Real Life")
    
    doc.add_paragraph(
        "Mathematical equations often look intimidating, but each formula in this system represents a common-sense physical reality. "
        "Below, each core equation is translated into plain English, showing why it was chosen, how its variables behave, "
        "and how it prevents false conclusions."
    )

    # --- Formula 1 ---
    add_h2("3.1 Estimating Unmonitored Districts: Inverse Distance Weighting (IDW)")
    doc.add_paragraph(
        "Only about 15 of Punjab's 41 districts have operational government air sensors. What about the other 26 districts? "
        "We cannot leave them blank. The system estimates them using Inverse Distance Weighting (IDW)."
    )
    
    add_callout(
        doc,
        [
            "THE EQUATION:",
            "  w_i = 1 / (max(Distance_i, 5.0 km))^2",
            "  Estimated Concentration = Sum(w_i * Concentration_i) / Sum(w_i)",
            "",
            "PLAIN-ENGLISH BREAKDOWN:",
            "• Distance_i: The great-circle distance (using Haversine geometry over Earth's curvature) from the unmonitored district center to active sensor station 'i'.",
            "• Why Distance is Squared (^2): If Station A is 10 km away and Station B is 20 km away, Station B is twice as far, but its influence drops by a factor of FOUR (2^2). Proximity dominates heavily.",
            "• Why the 5.0 km Clamp Exists: If a sensor happened to sit 0.01 km away, dividing by 0.01^2 would create an artificial multiplier of 10,000, completely drowning out all other stations. By setting a minimum distance floor of 5.0 km, the maximum weight any single station can have is 1/25 = 0.04. This prevents a single erratic monitor from taking over the map.",
            "",
            "WALK-THROUGH EXAMPLE:",
            "Suppose Kasur has no active monitor. Lahore (35 km away) reports 200 µg/m³; Okara (70 km away) reports 100 µg/m³.",
            "• Weight for Lahore = 1 / (35)^2 = 1 / 1225 = 0.000816",
            "• Weight for Okara  = 1 / (70)^2 = 1 / 4900 = 0.000204",
            "• Total Weight = 0.00102",
            "• Estimated Kasur PM2.5 = (0.000816 * 200 + 0.000204 * 100) / 0.00102 = (0.1632 + 0.0204) / 0.00102 = 180 µg/m³.",
            "Kasur's estimate is heavily influenced by nearby Lahore, with a gentle moderating pull from Okara. On the map, Kasur is marked with diagonal stripe cross-hatching so everyone knows it is an educated estimate, not a physical reading."
        ],
        title="FORMULA 1: INVERSE DISTANCE WEIGHTING & THE 5 KM CLAMP"
    )

    add_image_figure(doc, p3, "How Inverse Distance Weighting Works and Why the 5.0 km Minimum Clamp Is Essential", 6.2)

    # --- Formula 2 ---
    add_h2("3.2 Spreading the Plume: Wind-Steered Anisotropic Surface")
    doc.add_paragraph(
        "Standard mapping tools draw smooth circular halos around pollution sensors. In the real world, pollution never spreads in a circle—it "
        "is blown downwind into an elongated oval plume. The system uses wind-steering (anisotropic IDW) to create realistic concentration fields."
    )

    add_callout(
        doc,
        [
            "THE EQUATION:",
            "  Steering Multiplier (psi) = 1.0 + 0.70 * cos(alpha) * min(1.0, Wind_Speed / 1.5 m/s)",
            "  Final Weight = Base_Weight * max(0.30, psi)",
            "",
            "PLAIN-ENGLISH BREAKDOWN:",
            "• alpha (Wind Angle Alignment): The angle between the wind blowing from the station and the spot on the map we are drawing.",
            "  - Directly Downwind (alpha = 0°): cos(0°) = +1.0. The steering multiplier becomes 1.0 + 0.70 = 1.70 (+70% boost).",
            "  - Crosswind (alpha = 90°): cos(90°) = 0.0. The steering multiplier is 1.0 (no change).",
            "  - Directly Upwind (alpha = 180°): cos(180°) = -1.0. The steering multiplier drops to 1.0 - 0.70 = 0.30 (-70% reduction).",
            "• Wind_Speed / 1.5 m/s: If the air is stagnant (0.2 m/s), wind cannot push smoke very far, so directional elongation is tiny. Once wind reaches 1.5 m/s (~5.4 km/h), the plume stretches out to its full directional oval shape.",
            "• Distance-Dependent Opacity Taper: If an area is within 45 km of a monitor, the map renders with 100% solid color. Between 45 km and 140 km, the plume becomes semi-transparent. This visually tells decision-makers: 'We are confident near the city, but further out into the desert, uncertainty increases.'"
        ],
        title="FORMULA 2: ANISOTROPIC WIND STEERING"
    )

    add_image_figure(doc, p4, "Wind-Steered Plumes and Inter-District Advection Transport Mass Flux", 6.3)

    # --- Formula 3 ---
    add_h2("3.3 Pollution Highways: Inter-District Advection Mass Flux")
    doc.add_paragraph(
        "When Lahore suffers 400 µg/m³ of smog, neighboring Sheikhupura or Kasur often asks: 'Is Lahore blowing its pollution into our city?' "
        "The system answers this with an advection mass flux calculation."
    )

    add_callout(
        doc,
        [
            "THE EQUATION:",
            "  Mass Flux (A -> B) = Concentration_A * Wind_Speed_A * cos(Delta_Theta) * exp(-Distance / 100 km)",
            "",
            "PLAIN-ENGLISH BREAKDOWN:",
            "• Concentration_A * Wind_Speed_A: The physical volume of pollution moving per second. Higher smoke density and faster winds equal more tons of particulate matter transported per hour.",
            "• cos(Delta_Theta): The wind alignment cone. Delta_Theta is the difference between the compass bearing from City A to City B and the direction the wind is blowing. If wind is blowing directly from A toward B (Delta_Theta = 0°), cos = 1.0. The system strictly shuts off flux if the angle exceeds 35° (wind is missing the target).",
            "• exp(-Distance / 100 km): Atmospheric dilution and settling. Dust falls to the ground, and clean air mixes in over distance. At 100 km, flux naturally drops to 37% (e^-1). At distances beyond 180 km, the link is severed completely.",
            "• THE PHYSICAL DIMENSION GUARD: You can transport physical micrograms of dust through air, but you CANNOT transport an 'AQI number'. AQI is an arbitrary, non-linear index. If a user selects 'AQI' on the dashboard, the system's physics guard immediately turns off transport flux arrows to prevent displaying nonsensical, unscientific figures."
        ],
        title="FORMULA 3: INTER-DISTRICT MASS FLUX & THE DIMENSION GUARD"
    )

    # --- Formula 4 ---
    add_h2("3.4 Transboundary Inflow: 39 Border Normal Chevrons")
    doc.add_paragraph(
        "To determine whether cross-border smoke from Indian Punjab is entering Pakistani Punjab, the platform places 39 mathematical "
        "sensors along the international frontier. Each point has an inward-pointing vector perpendicular to the border line (the normal vector n)."
    )

    add_callout(
        doc,
        [
            "THE EQUATION:",
            "  Inflow Velocity (Phi_j) = Wind_Vector_j · Inward_Normal_Vector_j",
            "  Trigger Chevron IF: Phi_j > +0.25 m/s",
            "",
            "PLAIN-ENGLISH BREAKDOWN:",
            "• Dot Product (·): Measures how much of the wind is blowing directly across the border into Pakistan.",
            "• If winds blow parallel to the border (North to South), Phi = 0.0 (no cross-border entry).",
            "• If winds blow from the West into India, Phi is negative (Pakistan is exporting air).",
            "• If winds blow from the East into Pakistan at greater than 0.25 m/s (~1 km/h), Phi is positive. The system immediately renders bright crimson chevron arrows along the border, alerting officials to incoming transboundary smoke plumes."
        ],
        title="FORMULA 4: TRANSBOUNDARY INFLOW VELOCITY"
    )

    # --- Formula 5 ---
    add_h2("3.5 The Official Health Scale: PEPC Air Quality Index & The 500 Clamp")
    doc.add_paragraph(
        "Public health guidelines do not report raw micrograms—they report an Air Quality Index (AQI) from 0 to 500. "
        "The system uses the statutory Punjab Environmental Protection Council (PEPC) linear piecewise breakpoints."
    )

    add_callout(
        doc,
        [
            "THE EQUATION:",
            "  AQI = ((I_high - I_low) / (BP_high - BP_low)) * (Concentration - BP_low) + I_low",
            "  Composite AQI = max(AQI_PM2.5, AQI_PM10)",
            "",
            "THE 500 CEILING CLAMP RULE:",
            "In commercial apps, you sometimes see sensationalist headlines shouting 'AQI reached 1,800 in Lahore!' This is mathematically invalid. "
            "Under international and PEPC standards, the AQI scale officially ends at 500 ('Hazardous'). "
            "Whenever PM2.5 exceeds 350 µg/m³, the formula locks at 500 (Deep Maroon color). "
            "Why? Because at 350 µg/m³, the air is already maximally hazardous to all human life. Escalating the index to 1,200 or 2,000 creates panic "
            "without providing any additional medical guidance."
        ],
        title="FORMULA 5: PEPC AIR QUALITY INDEX & THE 500 CEILING CLAMP"
    )

    add_image_figure(doc, p5, "Official PEPC Air Quality Index Scale and the Statutory 500 Hazardous Ceiling Clamp", 6.2)

    # --- Formula 6 ---
    add_h2("3.6 Automated Data Hospital: The 7-Hour Spike and 3-Hour Hold Filters")
    doc.add_paragraph(
        "Low-cost sensors and electronic monitors often glitch. A spider might crawl into an optical chamber, causing a single reading to spike "
        "to 1,000 µg/m³, or a computer logger might freeze and report the exact same number for 10 hours. The system runs an automated data cleaning hospital:"
    )
    add_bullet("7-Hour Rolling Median Spike Filter: If a sensor reports a value that is both more than 4 times higher than its 7-hour median AND more than 3 times higher than the legal standard, it is flagged as a spurious electrical spike and removed.", "Spike Filter")
    add_bullet("3-Hour Logger Freeze Purge: If a physical sensor reports the exact same floating-point number (e.g., 142.30) for three consecutive hours, it is declared frozen and nulled out. (Composite AQI is exempt from this rule because an integer index can legitimately sit at 500 for days during severe inversions).", "Freeze Purge")
    add_bullet("Hardware Blacklist (Station 172 Wazirabad): Environmental engineers discovered that the physical weather vane at Station 172 in Wazirabad was installed with a permanent 140° mechanical offset. The system automatically blacklists wind readings from this station, protecting the entire regional model from corruption.", "Hardware Blacklist")

    # ==========================================
    # CHAPTER 4: PIPELINE INTEGRATION
    # ==========================================
    add_h1("4. Pipeline Integration: How the Disparate Pieces Form a Unified Whole")
    
    doc.add_paragraph(
        "Collecting seven different data streams is useless if they cannot communicate. The system bridges them through two "
        "critical engineering concepts:"
    )

    add_h2("4.1 The Chronometric Staging Buffer: Synchronizing Time")
    doc.add_paragraph(
        "Different feeds arrive at different times: satellite data arrives twice a day, airport weather arrives at 10 minutes past the hour, "
        "and ground monitors report between 5 and 20 minutes past the hour. "
        "The Chronometric Staging Buffer acts as a holding lounge. It gathers all incoming packets for a specific UTC hour. "
        "Once the hour closes, it locks the door, runs the quality control cleaners, applies the physics formulas, and writes a single, "
        "synchronized snapshot to the central database and high-speed memory cache."
    )

    add_h2("4.2 The 4-Tier Wind Backup Generator")
    doc.add_paragraph(
        "Wind is the heartbeat of pollution modeling. If wind data is missing, advection flux cannot be calculated. "
        "The system implements an automated 4-tier fallback generator:"
    )
    add_bullet("Tier 1: Ground Station Vane. Checked for physical validity and hardware blacklists. If good, it is used.", "First Choice")
    add_bullet("Tier 2: Nearest Airport Weather Feed. If the ground sensor is broken, the system looks for an active commercial airport within 40 kilometers.", "Second Choice")
    add_bullet("Tier 3: European Supercomputer Model. If no airport is nearby, it pulls the district's ECMWF forecast vector, calibrated for ground friction.", "Third Choice")
    add_bullet("Tier 4: Mathematical Spatial Estimation. If internet forecasts fail, it interpolates wind vectors from distant reporting stations using geodesic math.", "Final Failsafe")

    # ==========================================
    # CHAPTER 5: OVERALL SYSTEM ARCHITECTURE
    # ==========================================
    add_h1("5. Overall System Architecture & The Command Workstation")
    
    doc.add_paragraph(
        "The system is structured into four functional tiers that guarantee high reliability, sub-second query response times, "
        "and resilient operation even during national power or internet outages:"
    )

    # 4-tier table
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

    add_h2("5.1 The 5 Visual Overlays on the Map Screen")
    add_bullet("Layer 0 (Continuous Plume Heatmap): Renders the smooth, wind-steered smoke surface with transparency reflecting distance from sensors.")
    add_bullet("Layer 1 (District Health Boundaries): Colors all 41 district polygons by official PEPC severity grades, applying stripe hatching to estimated zones.")
    add_bullet("Layer 2 (Wind Flow Vectors): Displays real-time wind arrows showing exactly which way surface air is moving.")
    add_bullet("Layer 3 (Pollution Highways & Border Chevrons): Draws dynamic inter-district mass transport arrows and bright crimson border influx chevrons.")
    add_bullet("Layer 4 (Active Stations & Airports): Plots all 79 air monitors and 12 airports with interactive click-to-inspect telemetry cards.")

    add_h2("5.2 The 60 FPS Time Scrubber (Smooth Historic Playback)")
    doc.add_paragraph(
        "Decision-makers need to see how smog evolved over the past week. In standard software, dragging a timeline causes the screen "
        "to stutter and freeze as thousands of numbers recalculate. The workstation decouples the visual animation loop from the data updates: "
        "the map smoothly animates wind arrows and plumes at a fluid 60 frames per second, while heavy text statistics update at a relaxed 15 times "
        "per second. Operators can scrub backward and forward through 9 days of hourly history like a movie."
    )

    # ==========================================
    # CHAPTER 6: PROS OF THE SYSTEM
    # ==========================================
    add_h1("6. Pros: Key Strengths of the Platform")
    add_bullet("Unlike commercial consumer dashboards that draw generic circular heatmaps, every line and color is grounded in atmospheric physics (Eulerian advection, wind steering, and distance decay).", "1. Genuine Scientific Integrity")
    add_bullet("If the central database or external internet fails entirely, the workstation boots instantly in 'Air-Gapped Offline Mode', serving pre-indexed baseline records so disaster response teams can continue operating during blackouts.", "2. Air-Gapped Disaster Resilience")
    add_bullet("Built for government and scientific command rooms: high-contrast WCAG 2.1 AAA accessible color tokens (>=7:1 contrast ratio), clean monospaced numbers that do not jitter during playback, and zero distracting consumer emojis or tilted 3D angles.", "3. Institutional Command Ergonomics")
    add_bullet("With the 4-tier wind fallback, 7-hour spike cleaner, 3-hour freeze detector, and the 5.0 km IDW clamp, erratic sensor bugs are caught before they reach the public or leadership.", "4. Defensive Error Protection")
    add_bullet("The entire mathematical and operational suite is certified by an opaque-box test harness passing 144 out of 144 comprehensive end-to-end test scenarios.", "5. Fully Verified & Tested")

    # ==========================================
    # CHAPTER 7: CONS & SYSTEMIC LIMITATIONS
    # ==========================================
    add_h1("7. Cons, Systemic Vulnerabilities & Limitations")
    doc.add_paragraph(
        "To use this system responsibly, decision-makers must understand its genuine real-world limitations. "
        "No software can completely overcome physical hardware gaps on the ground:"
    )
    add_bullet("Punjab covers over 205,000 square kilometers, but physical monitoring stations are overwhelmingly concentrated in three cities: Lahore, Faisalabad, and Rawalpindi. Large southern districts like Rajanpur, Layyah, and Bhakkar have zero monitors. While IDW estimation is mathematically optimal, it cannot detect hyper-local rural point sources, such as illegal waste burning or isolated factory clusters.", "1. The 'Sensor Desert' Reality")
    add_bullet("The platform calculates 2D surface advection. It does not model vertical mixing heights or complex 3D photochemical reactions—such as sulfur dioxide gas converting into sulfate particles under humid winter sunlight.", "2. Absence of 3D Photochemical Modeling")
    add_bullet("Government websites change their formatting, block automated queries, or crash under heavy traffic. While the system has robust fallbacks, web-scraping public portals remains inherently fragile compared to dedicated private telemetry lines.", "3. Public Scraping Fragility")
    add_bullet("Demonstrating cross-border smoke transport is politically sensitive. While the system's border normal chevrons and wind vectors provide objective physical evidence of incoming plumes, local sources (millions of motorbikes, thousands of brick kilns) also contribute heavily. The tool must be used to foster cross-border environmental cooperation, not diplomatic deflection.", "4. Transboundary Attribution Sensitivity")
    add_bullet("The live scrubber currently operates across an indexed 216-hour horizon (9 days). Accessing multi-year historical archives requires querying backend database endpoints rather than continuous slider dragging.", "5. 9-Day Scrubber Horizon")

    # ==========================================
    # CHAPTER 8: STRATEGIC ENHANCEMENTS
    # ==========================================
    add_h1("8. Recommended Strategic Enhancements & Future Roadmap")
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
    # CHAPTER 9: SUMMARY MATRIX
    # ==========================================
    add_h1("9. Strategic Summary: Current Reality vs. Next-Gen Capability")
    
    matrix_headers = ["Strategic Dimension", "What the System Does Today", "Recommended Next Horizon"]
    matrix_widths = [Inches(1.8), Inches(2.5), Inches(2.5)]
    matrix_data = [
        ["Core Mission", "Real-time atmospheric monitoring, geostatistical interpolation, & transboundary tracking", "Predictive policy simulation, early warning health alerts, & enforcement dispatch"],
        ["Data Feeds", "7 diverse streams (ground, airport, synoptic, weather model, satellite, regional, continental)", "Integrate Sentinel-5P satellite gas sensors & 500+ rural community IoT monitors"],
        ["Meteorology", "4-tier wind fallback hierarchy (Station -> Airport -> Forecast -> Math)", "Full 3D atmospheric boundary layer height and vertical radiosonde soundings"],
        ["Mathematical Modeling", "Deterministic geodesic IDW, wind-steered plumes, and Eulerian mass flux", "Spatio-temporal Graph Neural Networks for 72-hour predictive forecasting"],
        ["System Resilience", "Air-gapped offline baseline mode + high-speed TimescaleDB/Redis backend", "High-availability geo-distributed cloud cluster with automated retention policies"],
        ["Presentation", "Institutional 2D MapLibre/Deck.gl console with 60 FPS sub-hourly scrubber", "Automated daily executive PDF briefing generator & mobile field inspector client"]
    ]
    matrix_tbl = doc.add_table(rows=1, cols=3)
    format_table(matrix_tbl, matrix_widths, matrix_headers, matrix_data)

    doc.save(str(docx_path))
    print(f"Human-centric Word brief successfully generated at: {docx_path}")

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    diagrams_folder = repo_root / "docs" / "diagrams"
    diag_files = generate_diagrams(diagrams_folder)
    out_docx = repo_root / "docs" / "Punjab_Air_Quality_System_Brief.docx"
    build_human_centric_document(out_docx, diag_files)
