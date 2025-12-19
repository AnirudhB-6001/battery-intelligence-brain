from __future__ import annotations

from confidence import ConfidenceEngineV1, ConfidenceSignals


def test_clustered_missing_penalizes_more_than_scattered():
    eng = ConfidenceEngineV1()

    # Same missing count, same total rows
    base = dict(missing_rows=8, total_rows=1344, computed_metrics_ok=True, corroboration=0.8)

    scattered = ConfidenceSignals(
        **base,
        missing_streak_max=1,
        missing_streaks=8,
    )
    clustered = ConfidenceSignals(
        **base,
        missing_streak_max=8,
        missing_streaks=1,
    )

    s1 = eng.score(scattered).score
    s2 = eng.score(clustered).score

    # clustered should be lower score than scattered
    assert s2 < s1
