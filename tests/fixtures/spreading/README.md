# B09 saved public regression fixtures

Copied/adapted on **2026-11-10**, task 0012. These are public report fixtures, not synthetic bank/client records.

- `dbs-annual-report-2025.pdf`: unchanged bytes copied read-only from `../financial-spreading-tool/FS/dbs-annual-report-2025.pdf`. Public DBS Group Holdings annual report, 107 physical dual-spread pages. SHA-256 `062223b76be563833610f1f14232c6f754e8ec9931c9e2ad1650d1218180665f`. The regression uses physical page 59, printed pages 114–115: Group total assets 897,488, liabilities 828,572 and equity 68,916 in reported millions. Original download URL/retrieval date were not supplied with the Phase 1 copy; do not invent them or describe this as newly retrieved public evidence. Tests treat it as a supplied public PDF, not a public-search result.
- `esr-core-response.json`: offline transcription of 17 configured core rows from the existing `demo/public_pack/esr-reit/annual-report-2025.pdf`, physical pages 127/128/155/156, with currency declaration on page 162. Source URL, retrieval date and hash remain in that pack's `manifest.yaml`; PDF bytes are not duplicated here. `page:N` references are fixture placeholders bound to real B08 evidence IDs by tests. Group/Trust and FY2025/FY2024 columns remain intact. No live model produced this fixture; source values are validated by Python.

Synthetic statement text used by tests is generated in `test_spreading.py`; every normalized page begins `SYNTHETIC DEMO DATA`. No Phase 1 runtime databases, client files or model credentials were copied.
