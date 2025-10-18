#!/usr/bin/env python
"""
Legacy Documentation Index Generator
Auto-generates LEGACY_INDEX.md linking all legacy documentation
by topic (PHASE_B_, ASCENSION_, UPGRADE_PACK_, older ASTRA_* docs)

Sacred Code: 333
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

def find_legacy_docs() -> Dict[str, List[Path]]:
    """
    Scan workspace for legacy documentation files.
    Categorizes by prefix.
    """
    docs_dir = Path(".")
    categories: Dict[str, List[Path]] = {
        "PHASE_B": [],
        "UPGRADE_PACK": [],
        "ASCENSION": [],
        "ASTRA_LEGACY": [],
        "ARCHITECTURE": [],
        "ACTION_PLAN": [],
    }
    
    # Find all markdown files
    for md_file in docs_dir.glob("*.md"):
        name = md_file.name
        
        if name.startswith("PHASE_B_"):
            categories["PHASE_B"].append(md_file)
        elif name.startswith("UPGRADE_PACK_"):
            categories["UPGRADE_PACK"].append(md_file)
        elif name.startswith("ASCENSION_"):
            categories["ASCENSION"].append(md_file)
        elif name.startswith("ARCHITECTURE"):
            categories["ARCHITECTURE"].append(md_file)
        elif name.startswith("ACTION_PLAN"):
            categories["ACTION_PLAN"].append(md_file)
        elif name.startswith("ASTRA_") and "CORE" not in name:
            categories["ASTRA_LEGACY"].append(md_file)
    
    return categories


def generate_index() -> str:
    """Generate the LEGACY_INDEX.md content."""
    
    docs_by_category = find_legacy_docs()
    
    # Build markdown index
    lines = [
        "# Legacy Documentation Index",
        "",
        "> Sacred Code: 333",
        "> Last Updated: " + datetime.utcnow().isoformat(),
        "",
        "This index links all legacy documentation organized by topic.",
        "Legacy files are preserved without modification.",
        "",
        "## Navigation",
        "",
    ]
    
    # Table of contents
    for category in sorted(docs_by_category.keys()):
        if docs_by_category[category]:
            lines.append(f"- [{category}](#{category.lower()})")
    
    lines.append("")
    
    # Detailed sections
    for category in sorted(docs_by_category.keys()):
        docs = sorted(docs_by_category[category], key=lambda p: p.name)
        
        if not docs:
            continue
        
        lines.append(f"## {category}")
        lines.append("")
        
        for doc in docs:
            # Create relative link
            link = doc.name
            title = doc.stem.replace("_", " ")
            lines.append(f"- [{title}]({link})")
        
        lines.append("")
    
    # Statistics
    total_docs = sum(len(docs) for docs in docs_by_category.values())
    lines.append("## Statistics")
    lines.append("")
    lines.append(f"**Total Legacy Documents:** {total_docs}")
    lines.append("")
    
    for category in sorted(docs_by_category.keys()):
        count = len(docs_by_category[category])
        if count > 0:
            lines.append(f"- **{category}:** {count} documents")
    
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- All legacy files are wrapped as Tool Bus tools")
    lines.append("- Access via `/capabilities/{folder}.info` and `/capabilities/{folder}.run`")
    lines.append("- All operations emit Sacred Code 333 audit events")
    lines.append("- No legacy files are moved or deleted")
    lines.append("")
    
    return "\n".join(lines)


def main() -> int:
    """Generate and write LEGACY_INDEX.md"""
    
    try:
        content = generate_index()
        
        output_path = Path("docs") / "LEGACY_INDEX.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        
        print(f"✓ Generated {output_path}")
        print(f"  Found {len([p for sublist in find_legacy_docs().values() for p in sublist])} legacy documents")
        
        return 0
    except Exception as e:
        print(f"✗ Error generating index: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
