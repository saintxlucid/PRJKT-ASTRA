#!/usr/bin/env python3
"""
ASTRA Backup Verification Script
Verifies the integrity and completeness of ASTRA backups
"""

import os
import sys
import json
import sqlite3
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()

class BackupVerifier:
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir
        self.issues = []
        
    def verify_database_backup(self, db_path: Path) -> bool:
        """Verify SQLite database integrity"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()
            
            if result != "ok":
                self.issues.append(f"Database integrity check failed: {result}")
                return False
                
            logger.info("Database integrity verified", path=str(db_path))
            return True
            
        except Exception as e:
            self.issues.append(f"Failed to verify database: {e}")
            return False
    
    def verify_vector_store(self, vector_dir: Path) -> bool:
        """Verify ChromaDB vector store backup"""
        try:
            required_files = ["chroma.sqlite3", "index"]
            
            for file in required_files:
                if not (vector_dir / file).exists():
                    self.issues.append(f"Missing vector store file: {file}")
                    return False
            
            # Verify SQLite integrity
            db_path = vector_dir / "chroma.sqlite3"
            if not self.verify_database_backup(db_path):
                return False
                
            logger.info("Vector store verified", path=str(vector_dir))
            return True
            
        except Exception as e:
            self.issues.append(f"Failed to verify vector store: {e}")
            return False
    
    def verify_file_checksums(self, manifest_path: Path) -> bool:
        """Verify file checksums against manifest"""
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            for file_path, expected_hash in manifest["files"].items():
                full_path = self.backup_dir / file_path
                
                if not full_path.exists():
                    self.issues.append(f"Missing file: {file_path}")
                    return False
                
                with open(full_path, "rb") as f:
                    actual_hash = hashlib.sha256(f.read()).hexdigest()
                
                if actual_hash != expected_hash:
                    self.issues.append(f"Checksum mismatch: {file_path}")
                    return False
            
            logger.info("File checksums verified", manifest=str(manifest_path))
            return True
            
        except Exception as e:
            self.issues.append(f"Failed to verify checksums: {e}")
            return False
    
    def verify_backup_age(self, max_age_hours: int = 24) -> bool:
        """Verify backup is not too old"""
        try:
            youngest_file = max(
                Path(root) / file
                for root, _, files in os.walk(self.backup_dir)
                for file in files
            )
            
            age = datetime.now() - datetime.fromtimestamp(youngest_file.stat().st_mtime)
            
            if age > timedelta(hours=max_age_hours):
                self.issues.append(f"Backup is too old: {age.total_seconds() / 3600:.1f} hours")
                return False
            
            logger.info("Backup age verified", age_hours=age.total_seconds() / 3600)
            return True
            
        except Exception as e:
            self.issues.append(f"Failed to verify backup age: {e}")
            return False
    
    def verify_all(self) -> Tuple[bool, List[str]]:
        """Run all verification checks"""
        success = True
        
        # Verify database
        db_path = self.backup_dir / "astra.db"
        if not self.verify_database_backup(db_path):
            success = False
        
        # Verify vector store
        vector_dir = self.backup_dir / "chromadb"
        if not self.verify_vector_store(vector_dir):
            success = False
        
        # Verify file checksums
        manifest_path = self.backup_dir / "backup_manifest.json"
        if not self.verify_file_checksums(manifest_path):
            success = False
        
        # Verify backup age
        if not self.verify_backup_age(24):
            success = False
        
        return success, self.issues

def main():
    """Main entry point"""
    backup_dir = Path(os.getenv("ASTRA_BACKUP_DIR", "data/backups"))
    
    if not backup_dir.exists():
        logger.error("Backup directory not found", path=str(backup_dir))
        return 1
    
    verifier = BackupVerifier(backup_dir)
    success, issues = verifier.verify_all()
    
    if not success:
        logger.error("Backup verification failed", issues=issues)
        return 1
    
    logger.info("Backup verification successful")
    return 0

if __name__ == "__main__":
    sys.exit(main())