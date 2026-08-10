# Repository Guidelines

## Project Scope and Current Baseline

This repository contains the proposal, typesetting sources, figures, and local competition materials for the “SEEG seizure-state intelligent detection” task. It is not yet a runnable training package.

Use the V3 judge-readable proposal as the current review baseline:

- `CISCNThesis/example_v3.tex` is the main XeLaTeX entry point.
- `CISCNThesis/seeg_solution_continuation_v3.tex` contains the later chapters.
- `CISCNThesis/cumcmthesis_v3.cls` contains V3 layout rules.
- `CISCNThesis/祈祷一个好头_v3.pdf` is the Chinese rendered deliverable; `SEEG_proposal_v3.pdf` is its ASCII-named copy.
- `CISCNThesis/修改说明_v3.md` records the V3 design decisions and build procedure.

The root `SEEG癫痫发作状态智能检测算法方案_ACEHolix.md` is the comprehensive technical source. The V3 proposal deliberately shortens and reorganizes it for judges, so do not bulk-synchronize the two files or assume they must be identical. Treat the unsuffixed and V2 LaTeX/PDF files as historical references unless a task explicitly targets them.

## Repository Structure

- `README.md`: repository overview, current deliverables, and build instructions.
- `SEEG癫痫发作状态智能检测算法方案.md`: original proposal.
- `SEEG癫痫发作状态智能检测算法方案_ACEHolix.md`: expanded technical proposal.
- `CISCNThesis/`: LaTeX proposal project and rendered deliverables.
- `CISCNThesis/tmp/pdfs/seeg_figures_zh_final_v3/`: editable V3 figure sources and rendered figure assets.
- `CISCNThesis/tools/`: earlier JavaScript figure-generation utilities.
- `Dataset/`: local competition data; never commit it.
- `SecRnd/`: local competition/support packages; never commit archives or extracted contents without explicit approval.

If implementation is added, place reusable code in `src/`, tests in `tests/`, configuration in `configs/`, and durable non-code figures in `assets/`. Do not commit datasets, model checkpoints, credentials, caches, generated experiment outputs, or large third-party archives.

## Build and Validation Commands

V3 requires Python 3 for its current model-flow figure and XeLaTeX for the proposal. From `CISCNThesis/`, run:

```bash
python3 tmp/pdfs/seeg_figures_zh_final_v3/text_flow_with_placeholders_v1.py
xelatex -output-directory=tmp/pdfs/seeg_figures_zh_final_v3 tmp/pdfs/seeg_figures_zh_final_v3/onset-v3.tex
xelatex -interaction=nonstopmode -halt-on-error example_v3.tex
xelatex -interaction=nonstopmode -halt-on-error example_v3.tex
xelatex -interaction=nonstopmode -halt-on-error example_v3.tex
```

Run XeLaTeX three times so the table of contents, references, and page numbers settle. The current host may not have XeLaTeX installed; report that limitation rather than claiming a successful PDF build.

Before submitting documentation changes, run from the repository root:

```bash
git diff --check
rg -n 'TO''DO|FIX''ME|T''BD' --glob '*.md'
rg -n '^(<<<<<<<|=======|>>>>>>>)' --glob '*.md' --glob '*.tex'
git status --short
```

Use `git diff --word-diff` for prose review. For LaTeX changes, also inspect the rendered PDF for heading hierarchy, table overflow, clipped figures, missing glyphs, broken references, and unexpected blank pages.

## Source and Generated-File Rules

Edit source files rather than generated artifacts. For V3 diagrams, prefer the corresponding `.py` or `.tex` source in `CISCNThesis/tmp/pdfs/seeg_figures_zh_final_v3/`, then regenerate PDF/SVG/PNG/TIFF outputs as required. Do not manually patch a compiled PDF.

Keep version families internally consistent: `example_v3.tex`, `seeg_solution_continuation_v3.tex`, `cumcmthesis_v3.cls`, V3 figures, and V3 PDFs must not silently mix V2 or unsuffixed assets. When creating a new major proposal revision, add a new suffix and a concise `修改说明_<version>.md`; do not overwrite older deliverables.

Existing tracked `.aux`, `.log`, `.toc`, `.out`, `.synctex.gz`, page previews, and generated figures are legacy artifacts. Do not add more build intermediates unless they are explicitly needed for review. Preserve unrelated user-generated or untracked files.

## Writing and Technical Conventions

Write Chinese proposal text in concise, formal language suitable for a technical competition submission. Use ATX headings in Markdown, fenced code blocks with language tags, and blank lines around lists and tables. In LaTeX, preserve the established class and command style and keep figures, equations, and tables close to the supporting discussion.

Define acronyms such as stereoelectroencephalography (SEEG), seizure-onset zone (SOZ), and epileptogenic zone (EZ) on first use. Preserve official channel IDs. Clearly distinguish model-important Top-10 channels, candidate early-recruitment contacts, clinically confirmed SOZ, EZ, and treatment targets.

Do not invent dataset statistics, performance results, latency numbers, hardware assumptions, or competition rules. Every reported metric must identify the patient-level split, metric definition, data source, and evaluation conditions. Keep onset definitions, probability precision, Top-10 ranking semantics, and inference-time claims consistent across the Markdown proposal, LaTeX manuscript, tables, figures, and final PDF.

For future Python code, use four-space indentation, `snake_case` for functions and files, and `PascalCase` for classes. Add a reproducible environment file and document exact training, evaluation, formatting, and test commands in `README.md`.

## Testing Expectations

Documentation changes require manual verification of internal links, equations, citations, table rendering, and consistency among classification, onset, Top-10 channel, clinical-boundary, and latency claims. LaTeX changes require a clean XeLaTeX build when the toolchain is available.

Future automated tests should use `tests/test_<module>.py` and cover patient-level leakage, adjacent-window leakage, channel masking, onset bounds and delay correction, Top-10 submission formatting, missing or bad channels, and deterministic output formatting.

## Commit and Pull Request Guidelines

Use short imperative English commit subjects, such as `Update repository guidance for V3 proposal`. Keep each commit focused and stage only files belonging to the requested change. Never include `Dataset/`, `SecRnd/`, checkpoints, archives, or unrelated local drafts in a documentation commit.

Pull requests should identify the affected proposal version, summarize the technical or editorial change, explain assumptions, list validation performed, and link the relevant competition requirement or issue. Include rendered screenshots only when diagrams, tables, equations, or layout change materially.
