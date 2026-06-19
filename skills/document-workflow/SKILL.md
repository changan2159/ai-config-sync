---
name: document-workflow
description: Use when the task involves reading, converting, creating, editing, validating, or extracting content from documents or document-like files, including PDF, Word `.docx`, Excel `.xlsx`/`.xlsm`, PowerPoint `.pptx`, CSV/TSV, Markdown, HTML exports, OCR needs, reports, memos, spreadsheets, slide decks, or deliverables that must be returned as a file. Prefer this skill when file format fidelity, formulas, layout, tables, tracked changes, comments, page structure, or conversion quality matters.
---

# Document Workflow

Use this skill for document and file deliverables. Preserve existing formatting when editing, choose tools by file type, and verify the produced artifact rather than trusting conversion code.

## File Type Routing

- PDF: extract text/tables, split/merge/rotate pages, OCR scanned pages, fill forms, watermark, or create final PDFs.
- DOCX: read or edit Word documents, tracked changes, comments, headings, tables, images, letters, memos, and polished reports.
- XLSX/XLSM/CSV/TSV: inspect sheets, clean tabular data, preserve formulas, add charts, restructure workbooks, and validate formula errors.
- PPTX: create or edit slide decks, speaker notes, images, layouts, and exported previews.
- Markdown/HTML: convert source documents for LLM analysis or produce clean intermediate text.

Use `load_workspace_dependencies` first when working with Office, spreadsheet, slide, or PDF files in the Codex desktop app so bundled runtimes and libraries are discovered before choosing tools.

## Tool Selection

Prefer deterministic tools before manual editing:

- `pypdf` or `pdfplumber` for PDF structure, text, tables, and page operations.
- OCR tooling only when extracted PDF text is missing or clearly degraded.
- `python-docx`, raw DOCX XML, or LibreOffice conversion for Word files depending on the edit.
- `openpyxl` for Excel formulas/formatting; `pandas` for data analysis; keep deliverables as spreadsheets when requested.
- `python-pptx` or LibreOffice export checks for PowerPoint.
- `markitdown`, Pandoc, or format-specific readers for conversion to Markdown.

If the task only needs analysis and not a document deliverable, convert to text/Markdown for reasoning. If the user asks for a formatted file, produce and validate the file.

## Verification Rules

- Open or inspect the generated file after writing it.
- For spreadsheets, check workbook opens, formulas are formulas rather than hardcoded computed outputs where the user expects a model, and obvious formula errors are absent.
- For PDFs, verify page count, rotation/order, text extraction quality, and whether OCR is needed.
- For DOCX/PPTX, verify package integrity and export/preview when layout matters.
- Preserve existing templates and styling unless the user asks for redesign.
- Do not overwrite source files unless the user explicitly asked for in-place modification; create a clearly named output file.

## Output Expectations

- State the source file type, output file path, and conversion/edit approach.
- Mention validation performed, including any limitations such as OCR quality or unsupported tracked changes.
- If a file cannot be faithfully edited with available tools, explain the constraint and provide the best safe alternative.
