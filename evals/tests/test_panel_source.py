"""The analysis reports a panel source like any other, as description only (UPDATE_29 section 1).

The tagged plan reports completed sessions by source and never uses the source in the
confirmatory test; a new label must neither break that nor enter the test.
"""

from __future__ import annotations

import pandas as pd

from evals import usability_analysis as ua


def test_by_source_reports_the_panel_label_per_arm():
    kept = pd.DataFrame(
        {
            "source_label": ["panel", "panel", "poster", "panel", ""],
            "arm": ["trained", "untrained", "trained", "trained", "untrained"],
        }
    )
    out = ua.by_source(kept)
    assert out["panel"] == {"trained": 2, "untrained": 1}
    assert out["poster"] == {"trained": 1, "untrained": 0}
    assert out["unknown"] == {"trained": 0, "untrained": 1}
