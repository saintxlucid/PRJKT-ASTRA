# Simple smoke test for semantic search via Qdrant
param(
  [string]$IndexName = "astra_docs.jsonl",
  [string]$Query = "hello world"
)

$env:DOC_INDEX_DIR = "data/document_index"
$env:QDRANT_URL = "http://127.0.0.1:6333"
$env:USE_QDRANT = "true"
$env:EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

Write-Host "[*] Running semantic search smoke test..." -ForegroundColor Cyan

# Create a tiny sample PDF for ingestion using a temp python file
$sampleDir = Join-Path (Get-Location) "data\documents"
New-Item -ItemType Directory -Force -Path $sampleDir | Out-Null
$samplePdf = Join-Path $sampleDir "sample_test.pdf"

$pyCode = @'
import os
import fitz
pdf_path = os.environ.get('SAMPLE_PDF')
doc = fitz.open()
page = doc.new_page()
page.insert_text((72,72), "ASTRA sample document about planets and stars. Hello world.")
doc.save(pdf_path)
doc.close()
print("Saved:", pdf_path)
'@

$env:SAMPLE_PDF = $samplePdf
$tmpPy = Join-Path $env:TEMP "make_sample_pdf.py"
Set-Content -Path $tmpPy -Value $pyCode -Encoding UTF8
& python $tmpPy

# Ingest into docs (using real embeddings)
python -m astra.services.document_service ingest `
  "$samplePdf" `
  --index "$IndexName" `
  --chunk 100 `
  --overlap 10 `
  --real-embeddings

# Call semantic search (which uses Qdrant)
$pySearch = @'
import os
from astra.services import document_service as ds
index = os.environ.get('INDEX', 'astra_docs.jsonl')
query = os.environ.get('QUERY', 'planets')
res = ds.semantic_search(index, query, 5)
print('Results:', res)
'@

$env:INDEX = $IndexName
$env:QUERY = $Query
$tmpSearch = Join-Path $env:TEMP "semantic_search.py"
Set-Content -Path $tmpSearch -Value $pySearch -Encoding UTF8
& python $tmpSearch
