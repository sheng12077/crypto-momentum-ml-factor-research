import pytest
from momentum_data.reporting.publication import preserve_scope_correction


def test_explicit_scope_correction_survives_regeneration():
    previous = "# Project\n<!-- scope-correction:start -->\n> Only37assets; broader study incomplete.\n<!-- scope-correction:end -->\nOld report"
    result = preserve_scope_correction(previous, "# Project\n\nNew report")
    assert result.count("<!-- scope-correction:start -->") == 1
    assert "broader study incomplete" in result and result.endswith("New report")


def test_malformed_correction_is_not_silently_discarded():
    with pytest.raises(ValueError, match="Malformed scope correction"):
        preserve_scope_correction("<!-- scope-correction:start -->warning", "# Project\nReport")


def test_no_correction_leaves_generated_report_unchanged():
    assert preserve_scope_correction("# Original", "# New\nReport") == "# New\nReport"
