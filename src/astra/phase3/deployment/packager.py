"""Service Packager - Artifact Creation and Packaging

This module handles packaging the ASTRA system for deployment,
creating distributable artifacts with all dependencies and configurations.

Key Features:
- Service artifact creation
- Dependency bundling
- Configuration packaging
- Artifact versioning
- Integrity verification
"""

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ArtifactMetadata:
    """Metadata for a service artifact."""
    artifact_id: str
    service_name: str
    version: str
    created_at_ms: float
    created_by: str
    description: str
    size_bytes: int = 0
    file_count: int = 0
    checksum: str = ""
    dependencies: list[dict[str, str]] = field(default_factory=list)
    configuration: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "artifact_id": self.artifact_id,
            "service_name": self.service_name,
            "version": self.version,
            "created_at_ms": self.created_at_ms,
            "created_by": self.created_by,
            "description": self.description,
            "size_bytes": self.size_bytes,
            "file_count": self.file_count,
            "checksum": self.checksum,
            "dependencies": self.dependencies,
            "configuration": self.configuration,
        }

    def to_json(self) -> str:
        """Convert metadata to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class ServicePackager:
    """Packages ASTRA services for deployment."""

    def __init__(self, base_path: str = "."):
        """Initialize packager.
        
        Args:
            base_path: Base path for packaging
        """
        self.base_path = Path(base_path)
        self.artifacts: dict[str, ArtifactMetadata] = {}

    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hex checksum string
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def create_artifact(
        self,
        artifact_id: str,
        service_name: str,
        version: str,
        source_dir: str,
        include_patterns: list[str] | None = None,
        dependencies: list[dict[str, str]] | None = None,
        configuration: dict[str, Any] | None = None,
        created_by: str = "system",
        description: str = "",
    ) -> ArtifactMetadata:
        """Create a service artifact.
        
        Args:
            artifact_id: Unique artifact identifier
            service_name: Name of the service
            version: Version string
            source_dir: Source directory to package
            include_patterns: File patterns to include (default: all)
            dependencies: List of dependency dicts
            configuration: Configuration to include
            created_by: Creator identifier
            description: Artifact description
            
        Returns:
            ArtifactMetadata for the created artifact
        """
        source_path = Path(source_dir)
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")

        # Create artifact directory
        artifact_dir = self.base_path / "artifacts" / artifact_id
        artifact_dir.mkdir(parents=True, exist_ok=True)

        # Package content directory
        content_dir = artifact_dir / "content"
        content_dir.mkdir(exist_ok=True)

        # Copy files
        total_size = 0
        file_count = 0

        for item in source_path.rglob("*"):
            if item.is_file():
                # Check include patterns
                if include_patterns:
                    if not any(pattern in str(item) for pattern in include_patterns):
                        continue

                rel_path = item.relative_to(source_path)
                dest_path = content_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_path)

                total_size += item.stat().st_size
                file_count += 1

        # Create metadata
        metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            service_name=service_name,
            version=version,
            created_at_ms=time.time() * 1000,
            created_by=created_by,
            description=description,
            size_bytes=total_size,
            file_count=file_count,
            dependencies=dependencies or [],
            configuration=configuration or {},
        )

        # Write metadata
        metadata_file = artifact_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            f.write(metadata.to_json())

        # Calculate artifact checksum
        metadata.checksum = self.calculate_checksum(
            artifact_dir / "content"
            if (artifact_dir / "content").exists()
            else artifact_dir
        )

        # Update and re-write metadata
        with open(metadata_file, "w") as f:
            f.write(metadata.to_json())

        self.artifacts[artifact_id] = metadata
        return metadata

    def list_artifacts(self) -> list[dict[str, Any]]:
        """List all created artifacts.
        
        Returns:
            List of artifact metadata dictionaries
        """
        return [m.to_dict() for m in self.artifacts.values()]

    def get_artifact(self, artifact_id: str) -> ArtifactMetadata | None:
        """Get artifact metadata.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            ArtifactMetadata or None if not found
        """
        return self.artifacts.get(artifact_id)

    def verify_artifact(self, artifact_id: str) -> bool:
        """Verify artifact integrity.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            True if artifact is valid
        """
        if artifact_id not in self.artifacts:
            return False

        artifact_dir = self.base_path / "artifacts" / artifact_id
        if not artifact_dir.exists():
            return False

        metadata_file = artifact_dir / "metadata.json"
        if not metadata_file.exists():
            return False

        try:
            with open(metadata_file, "r") as f:
                data = json.load(f)
                return (
                    data.get("artifact_id") == artifact_id
                    and data.get("file_count", 0) > 0
                )
        except (json.JSONDecodeError, IOError):
            return False

    def get_artifact_stats(self) -> dict[str, Any]:
        """Get packaging statistics.
        
        Returns:
            Dictionary with packaging stats
        """
        total_artifacts = len(self.artifacts)
        total_size = sum(m.size_bytes for m in self.artifacts.values())
        total_files = sum(m.file_count for m in self.artifacts.values())

        return {
            "total_artifacts": total_artifacts,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "total_files": total_files,
            "artifacts": [m.to_dict() for m in self.artifacts.values()],
        }


class ArtifactRegistry:
    """Registry for managing artifact metadata and versions."""

    def __init__(self, registry_path: str = "artifact_registry.json"):
        """Initialize registry.
        
        Args:
            registry_path: Path to registry file
        """
        self.registry_path = Path(registry_path)
        self.entries: dict[str, dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        """Load registry from file."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r") as f:
                    data = json.load(f)
                    self.entries = data.get("entries", {})
            except (json.JSONDecodeError, IOError):
                self.entries = {}

    def save(self) -> None:
        """Save registry to file."""
        with open(self.registry_path, "w") as f:
            json.dump(
                {
                    "entries": self.entries,
                    "saved_at_ms": time.time() * 1000,
                },
                f,
                indent=2,
            )

    def register_artifact(self, metadata: ArtifactMetadata) -> None:
        """Register an artifact.
        
        Args:
            metadata: ArtifactMetadata to register
        """
        key = f"{metadata.service_name}:{metadata.version}"
        self.entries[key] = metadata.to_dict()
        self.save()

    def get_latest_version(self, service_name: str) -> dict[str, Any] | None:
        """Get latest version of a service.
        
        Args:
            service_name: Service name
            
        Returns:
            Latest artifact metadata or None
        """
        candidates = [
            entry
            for key, entry in self.entries.items()
            if entry.get("service_name") == service_name
        ]

        if not candidates:
            return None

        # Sort by created_at_ms descending
        return sorted(candidates, key=lambda x: x.get("created_at_ms", 0), reverse=True)[0]

    def list_versions(self, service_name: str) -> list[dict[str, Any]]:
        """List all versions of a service.
        
        Args:
            service_name: Service name
            
        Returns:
            List of artifact metadata for all versions
        """
        candidates = [
            entry
            for key, entry in self.entries.items()
            if entry.get("service_name") == service_name
        ]
        return sorted(candidates, key=lambda x: x.get("created_at_ms", 0), reverse=True)

    def get_registry_stats(self) -> dict[str, Any]:
        """Get registry statistics.
        
        Returns:
            Dictionary with registry stats
        """
        services = {}
        for entry in self.entries.values():
            service = entry.get("service_name", "unknown")
            if service not in services:
                services[service] = []
            services[service].append(entry)

        return {
            "total_entries": len(self.entries),
            "services": {
                name: {
                    "versions": len(versions),
                    "latest": max(
                        v.get("created_at_ms", 0) for v in versions
                    ),
                }
                for name, versions in services.items()
            },
        }
