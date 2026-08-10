# Onset feature figure QA notes

## Figure contract

- Core conclusion: onset timing alignment and official Top-10 channel concordance are complementary; no single hand-crafted feature dominates both.
- Archetype: quantitative evidence grid. Panel a is the primary onset-aligned heatmap; panel b compares descriptive timing and spatial metrics; panel c shows leading trajectories.
- Backend: Python/matplotlib only.

## Statistical annotation

- Independent `n`: 5 positive records with local signals and manual onset labels.
- Biological/record-level replicates: records; patient identity is unavailable, so these cannot yet be claimed as five independent patients.
- Technical replicates: channels and windows are repeated measurements within records and are not counted as independent `n`.
- Center: record-level median.
- Spread: interquartile range in panel c.
- Test and multiple-comparison correction: none; the analysis is descriptive and exploratory because `n=5`.
- P-value display: none.
- Baseline: onset minus 10 to 2 seconds, standardized per channel by median/MAD.
- Source data: `onset_aligned_trajectories.csv`, `feature_summary.csv`, and `record_feature_alignment.csv` in this directory.
- Missingness: all plotted aligned-time bins contain all five records; the two fractional-alignment boundary bins with `n<5` are omitted.

## Export and visual checks

- Static preflight: 14 PASS, 0 WARN, 0 FAIL with `validate_figure.py --strict`.
- Final width: 7.2 inches (182.9 mm), matching a common double-column width.
- Editable vectors: SVG text retained; PDF uses TrueType font embedding.
- Raster exports: 300 dpi PNG preview and 600 dpi TIFF.
- Visual inspection: panel labels, axes, color bars, legends, onset reference lines, and long feature labels are readable at the exported size; no clipping or overlap was observed.
