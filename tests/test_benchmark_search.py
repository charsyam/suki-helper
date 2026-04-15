from __future__ import annotations

from pathlib import Path

import fitz

from suki_helper.tools.benchmark_search import run_benchmark


def _create_sample_pdf(pdf_path: Path) -> None:
    document = fitz.open()
    for text in ("alpha beta", "beta gamma", "alpha gamma"):
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(pdf_path)
    document.close()


def test_run_benchmark_returns_zero(tmp_path: Path, capsys) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _create_sample_pdf(pdf_path)

    exit_code = run_benchmark(pdf_path, "alpha beta", root_dir=tmp_path)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Index time:" in captured.out
    assert "Search time:" in captured.out
    assert "Results:" in captured.out
