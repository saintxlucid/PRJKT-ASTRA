"""
Database Initialization Script

This script initializes the ASTRA database with all required tables.
Run once to set up the database schema.

Usage:
    python scripts/init_database.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, inspect
from src.astra.models.config import get_settings
from src.astra.infrastructure.persistence.models import Base

def init_database():
    """Initialize the database with all required tables."""
    
    print("=" * 60)
    print("   ASTRA Database Initialization")
    print("=" * 60)
    print()
    
    # Load settings
    print("[1/3] Loading configuration...")
    settings = get_settings()
    print(f"   ✓ Database URL: {settings.database_url}")
    
    # Create engine
    print("[2/3] Creating database engine...")
    engine = create_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True
    )
    print("   ✓ Engine created")
    
    # Create all tables
    print("[3/3] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Verify tables
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"   ✓ Created {len(tables)} tables:")
    for table in sorted(tables):
        print(f"      • {table}")
    
    print()
    print("=" * 60)
    print("   Database Initialization Complete!")
    print("=" * 60)
    print()

if __name__ == "__main__":
    try:
        init_database()
        sys.exit(0)
    except Exception as e:
        print(f"   ✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
