"""
Unit tests for executive reporting suite docx generators.
Verifies structure, letterhead, tables, callout blocks, and statutory compliance.
"""
from pathlib import Path
import tempfile
import pytest
import docx

from scripts.generate_daily_situation_report import build_daily_situation_report
from scripts.generate_technical_advisory import generate_technical_advisory, generate_cover_letter


class TestDocxGenerators:
    """Verifies that all institutional executive Word reports generate and match specifications."""

    def test_daily_situation_report_generation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "test_situation_report.docx"
            result = build_daily_situation_report(date_str="20261110", output_path=out_path)
            assert result.exists()
            assert result.stat().st_size > 10000

            doc = docx.Document(str(result))
            # Verify 5 tables: 3 callouts + 41-district matrix + forecast matrix
            assert len(doc.tables) >= 5

            # Verify 41 districts in compliance table (row 0 is header)
            district_tbl = doc.tables[1]
            assert len(district_tbl.rows) == 42

            # Verify heading text
            all_text = "\n".join([p.text for p in doc.paragraphs])
            assert "GOVERNMENT OF THE PUNJAB" in all_text
            assert "ENVIRONMENTAL PROTECTION AGENCY (EPA) PUNJAB" in all_text
            assert "DAILY AIR QUALITY & SMOG SITUATION REPORT" in all_text

    def test_technical_advisory_generation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "test_technical_advisory.docx"
            result = generate_technical_advisory(output_path=out_path)
            assert result.exists()
            assert result.stat().st_size > 10000

            doc = docx.Document(str(result))
            all_text = "\n".join(
                [p.text for p in doc.paragraphs] +
                [p.text for t in doc.tables for row in t.rows for cell in row.cells for p in cell.paragraphs]
            )
            assert "EPA/DIREMC/O/261110/" in all_text
            assert "STATUTORY TECHNICAL ADVISORY" in all_text

            # Verify Sector callouts (Sectors A through E)
            assert len(doc.tables) >= 6

    def test_cover_letter_generation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = Path(tmp_dir) / "test_cover_letter.docx"
            result = generate_cover_letter(output_path=out_path)
            assert result.exists()
            assert result.stat().st_size > 5000

            doc = docx.Document(str(result))
            all_text = "\n".join([p.text for p in doc.paragraphs])
            assert "Chief Secretary" in all_text
            assert "SUBMISSION OF PROVINCIAL TECHNICAL ADVISORY" in all_text
