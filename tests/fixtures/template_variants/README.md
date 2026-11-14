# Generated template comparison fixtures

Tests copy `templates/ES_Template_FIG_draft_v0.1.docx` into their isolated
`tmp_path/template-fixtures/` directory, mutate those copies, and register the
resulting bytes. No owner template or real bank data is modified or introduced.
The generated copies carry `SYNTHETIC DEMO DATA` in the copied document's title
header. Both comparison sides share that label so it is not a tested change.

Cases cover font/colour, narrative guidance, renamed headers, added columns,
added/removed/duplicate headings, formulas, merged cells, styles, ancillary parts,
and mixed changes. Files are generated per test rather than checking in binaries.
