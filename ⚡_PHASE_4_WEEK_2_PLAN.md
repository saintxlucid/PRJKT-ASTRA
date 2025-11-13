⚡ PHASE 4 WEEK 2 - REPOSITORY & DATASET INGESTION PLAN

Date: November 13, 2025
Phase: Asset Ingestion - Verification & Smoke Testing
Status: READY FOR EXECUTION

═══════════════════════════════════════════════════════════════════════════════

WEEK 2 OBJECTIVES

✅ Verify all 5 cloned repositories
✅ Verify all 4 downloaded datasets  
✅ Run smoke tests on repositories
✅ Run smoke tests on datasets
✅ Update registry with verification results
✅ Prepare artifacts for Week 3 (vector store integration)

═══════════════════════════════════════════════════════════════════════════════

ASSET INVENTORY (FROM WEEK 1)

Repositories (5 total):
  1. llm-engineer-toolkit  - Tools for LLM development
  2. ragged               - RAG framework
  3. Awesome-LLMOps      - LLMOps collection
  4. awesome-llm-agents  - Agent examples
  5. llm-toolkit          - Toolkit utilities

Datasets (4 total - 45K+ records):
  1. rag-mini-wikipedia    - 3,200 records (text-corpus split)
  2. rag-mini-bioasq       - 40,221 records (text-corpus split)
  3. RAGBench              - 1,252 records (covidqa config)
  4. CXM_Arena             - 811 records (2 splits)

═══════════════════════════════════════════════════════════════════════════════

WEEK 2 TASKS

TASK 2.1: Repository Verification
──────────────────────────────────

For each repository:
  ✓ Check .git directory exists (valid repo)
  ✓ Verify HEAD points to valid commit
  ✓ Count Python files (for code analysis)
  ✓ Check for requirements.txt or setup.py
  ✓ Verify repository is not corrupted
  
Script: verify_repos.py (NEW)
Output: repo_verification_report.json

TASK 2.2: Dataset Verification
───────────────────────────────

For each dataset:
  ✓ Verify directory structure exists
  ✓ Check dataset_dict.json is valid JSON
  ✓ Count total records across all splits
  ✓ Verify arrow files are readable
  ✓ Check dataset metadata

Script: verify_datasets.py (NEW)
Output: dataset_verification_report.json

TASK 2.3: Repository Smoke Tests
─────────────────────────────────

For each repository:
  ✓ Try to import main module (if Python)
  ✓ Check for obvious syntax errors
  ✓ Verify package structure
  ✓ Count LOC and files
  ✓ Check documentation

Script: smoke_test_repos.py (NEW)
Output: repo_smoke_test_report.json

TASK 2.4: Dataset Smoke Tests
──────────────────────────────

For each dataset:
  ✓ Load dataset into memory
  ✓ Check record counts match
  ✓ Sample 10 records from each split
  ✓ Verify field structure consistency
  ✓ Check data types

Script: smoke_test_datasets.py (NEW)
Output: dataset_smoke_test_report.json

TASK 2.5: Registry Update
──────────────────────────

Update assets_registry.yml:
  ✓ Mark verified assets as "staged"
  ✓ Add timestamp of verification
  ✓ Record stats (LOC, records, files)
  ✓ Note any issues or warnings
  ✓ Prepare for Week 3 (vector integration)

TASK 2.6: Week 2 Summary Report
────────────────────────────────

Create comprehensive report:
  ✓ All verification results
  ✓ All smoke test results
  ✓ Asset statistics
  ✓ Quality metrics
  ✓ Ready/not-ready status for Week 3

═══════════════════════════════════════════════════════════════════════════════

SCRIPTS TO CREATE

1. verify_repos.py (estimated 180 LOC)
   - Git repo validation
   - Commit verification
   - File counting
   - Dependency detection

2. verify_datasets.py (estimated 160 LOC)
   - Dataset structure validation
   - Record counting
   - Arrow file verification
   - Metadata checking

3. smoke_test_repos.py (estimated 200 LOC)
   - Module import tests
   - Syntax validation
   - LOC analysis
   - Documentation checks

4. smoke_test_datasets.py (estimated 220 LOC)
   - Dataset loading
   - Record sampling
   - Field validation
   - Data type checking

TOTAL: ~760 LOC of verification/testing code

═══════════════════════════════════════════════════════════════════════════════

QUALITY GATES (Week 2 Focus)

[1/6] Code Quality
  ✓ All verification scripts: 0 lint errors
  ✓ Type hints: 95%+ coverage
  ✓ Docstrings: 100% functions

[2/6] Data Quality
  ✓ All repos verified readable
  ✓ All datasets verified loadable
  ✓ Record counts accurate
  ✓ No data corruption

[3/6] Integration (Preparation)
  ✓ All assets ready for vector indexing
  ✓ No blocking issues found
  ✓ Dependencies documented

[4/6] Performance (N/A for Week 2)

[5/6] Observability
  ✓ Verification logs created
  ✓ Smoke test results documented
  ✓ Registry updated

[6/6] Security
  ✓ No malicious code detected
  ✓ All repos from trusted sources

═══════════════════════════════════════════════════════════════════════════════

SUCCESS CRITERIA FOR WEEK 2

✅ All 5 repositories verified
✅ All 4 datasets verified  
✅ All smoke tests passing
✅ Registry updated with verification results
✅ 0 lint errors in new scripts
✅ Comprehensive report created
✅ Ready for Week 3 (vector integration)

PASS/FAIL THRESHOLD: All 5 repos + all 4 datasets must be verified and smoke tests passing

═══════════════════════════════════════════════════════════════════════════════

WEEK 2 TIMELINE

Day 1: Create verification scripts (verify_repos.py, verify_datasets.py)
Day 2: Create smoke test scripts (smoke_test_repos.py, smoke_test_datasets.py)
Day 3: Run all verification and smoke tests
Day 4: Generate reports and update registry
Day 5: Create Week 2 summary and prepare for Week 3

═══════════════════════════════════════════════════════════════════════════════

DELIVERABLES (End of Week 2)

✅ verify_repos.py               (180 LOC, verification script)
✅ verify_datasets.py            (160 LOC, verification script)
✅ smoke_test_repos.py           (200 LOC, testing script)
✅ smoke_test_datasets.py        (220 LOC, testing script)
✅ repo_verification_report.json (verification results)
✅ dataset_verification_report.json (verification results)
✅ repo_smoke_test_report.json   (test results)
✅ dataset_smoke_test_report.json (test results)
✅ assets_registry.yml (UPDATED) (with verification metadata)
✅ ⚡_PHASE_4_WEEK_2_VERIFICATION_COMPLETE.md (summary)

═══════════════════════════════════════════════════════════════════════════════

READY FOR EXECUTION
Status: ✅ GO

Phase 3 complete: 99.9%+ production ready
Phase 4 Week 1 complete: All assets acquired
Phase 4 Week 2 ready: Verification scripts pending creation

Next: Begin Week 2 verification and smoke testing
