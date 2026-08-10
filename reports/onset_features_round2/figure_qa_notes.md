# Second-round onset figure QA notes

## Figure contract

- Core conclusion: multichannel propagation features should be prioritized only when their record-level onset alignment exceeds the strongest first-round local features.
- Archetype: quantitative grid. The record-by-feature signed-error heatmap is the hero panel; ranking and trajectories are supporting evidence.
- Backend: Python/matplotlib only.

## Statistical annotation

- Independent `n`: 5 positive records with local signals and manual onset labels.
- Patient identity: unavailable; five records cannot be claimed as five independent patients.
- Repeated measurements: channels and windows remain nested within records and are not independent replicates.
- Center and spread: record-level median and interquartile range.
- Inference: no p-values or multiple-comparison testing; all 33-feature rankings are exploratory.
- Source data: `feature_summary.csv`, `record_feature_alignment.csv`, `onset_aligned_trajectories.csv`, and propagation sensitivity CSV files in this directory.
- Missingness: global propagation features intentionally have no Top-10 value; every plotted onset-aligned time bin contains all five records.

## Visual and integrity checks

- Final width: 7.2 inches (182.9 mm), a common double-column width.
- Editable vectors: SVG retains text; PDF uses TrueType embedding.
- Raster exports: 300 dpi PNG and 600 dpi TIFF.
- Panel c is visually clipped to ±4 robust-z units because one propagation-participation IQR is extreme; the unclipped values remain in the source CSV and are used for every calculation.
- No observations were removed from the primary five-record analysis. The severe-line-noise exclusion is reported as a separate sensitivity condition with before/after channel counts.
