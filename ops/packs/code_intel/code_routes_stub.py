"""
ASTRA Code Intelligence Routes
FastAPI routes for /api/code/* endpoints.
"""
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from pathlib import Path
import sqlite3
import subprocess
import sys

router = APIRouter(prefix="/api/code", tags=["code"])
DB = Path("backend/data/memory.db")


class DiffRequest(BaseModel):
    """Request to propose a code change."""
    instruction: str = Field(..., description="Natural language instruction for change")
    files: list[str] = Field(default_factory=list, description="Files to consider")


class ApplyRequest(BaseModel):
    """Request to apply a code patch."""
    path: str = Field(..., description="Target file path")
    original: str = Field(..., description="Original content for verification")
    patched: str = Field(..., description="Patched content to apply")


@router.get("/search")
def search_symbols(q: str, limit: int = 50):
    """Search code symbols by name or signature."""
    try:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        
        cur.execute("""
            SELECT cs.name, cs.kind, cs.line_start, cf.path, cs.signature
            FROM code_symbols cs
            JOIN code_files cf ON cs.file_id = cf.id
            WHERE cs.name LIKE ? OR cs.signature LIKE ?
            LIMIT ?
        """, (f"%{q}%", f"%{q}%", limit))
        
        results = []
        for row in cur.fetchall():
            results.append({
                "name": row[0],
                "kind": row[1],
                "line": row[2],
                "path": row[3],
                "signature": row[4]
            })
        
        con.close()
        return {"results": results, "query": q}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file")
def read_file(path: str, start: int = 1, end: int = 200):
    """Read file content with line range."""
    try:
        p = Path(path)
        if not p.exists():
            raise HTTPException(status_code=404, detail="file not found")
        
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        selected = lines[max(0, start - 1):end]
        
        return {
            "path": path,
            "lines": selected,
            "start": start,
            "end": min(end, len(lines)),
            "total": len(lines)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diff")
def propose_diff(req: DiffRequest):
    """Propose a patch plan (dry-run)."""
    # Stub: in production, this would use LLM to generate proposed changes
    return {
        "instruction": req.instruction,
        "files": req.files,
        "plan": "TODO: generate patch plan with LLM",
        "diff": "TODO: generate unified diff"
    }


@router.post("/apply")
def apply_patch(req: ApplyRequest):
    """Apply a guarded patch."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from patch_apply import apply_unified_patch
        
        target = Path(req.path)
        apply_unified_patch(target, req.original, req.patched)
        
        return {"status": "applied", "path": req.path}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/index")
def reindex_repo():
    """Reindex repository code."""
    try:
        indexer = Path(__file__).parent / "code_indexer.py"
        subprocess.run([sys.executable, str(indexer)], check=True, capture_output=True)
        return {"status": "reindexed"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
