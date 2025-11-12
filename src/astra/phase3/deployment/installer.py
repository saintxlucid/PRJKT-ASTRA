"""Service Installer - Deployment and Service Installation

This module handles installing and deploying ASTRA services to target environments,
with support for upgrade, rollback, and configuration management.

Key Features:
- Service installation to target locations
- Configuration deployment
- Dependency resolution
- Service health verification
- Rollback support
- Installation logging and reporting
"""

import json
import time
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class InstallationStep:
    """A single step in the installation process."""
    step_name: str
    status: str = "PENDING"  # PENDING, RUNNING, SUCCESS, FAILED
    started_at_ms: float = 0.0
    completed_at_ms: float = 0.0
    duration_ms: float = 0.0
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert step to dictionary."""
        return {
            "step_name": self.step_name,
            "status": self.status,
            "started_at_ms": self.started_at_ms,
            "completed_at_ms": self.completed_at_ms,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
        }


@dataclass
class InstallationReport:
    """Report of a service installation."""
    installation_id: str
    service_name: str
    version: str
    target_location: str
    started_at_ms: float = field(default_factory=lambda: time.time() * 1000)
    completed_at_ms: float = 0.0
    status: str = "IN_PROGRESS"  # IN_PROGRESS, SUCCESS, FAILED
    steps: list[InstallationStep] = field(default_factory=list)
    configuration_deployed: bool = False
    health_check_passed: bool = False
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "installation_id": self.installation_id,
            "service_name": self.service_name,
            "version": self.version,
            "target_location": self.target_location,
            "started_at_ms": self.started_at_ms,
            "completed_at_ms": self.completed_at_ms,
            "status": self.status,
            "steps": [step.to_dict() for step in self.steps],
            "configuration_deployed": self.configuration_deployed,
            "health_check_passed": self.health_check_passed,
            "error_message": self.error_message,
        }

    def to_json(self) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class ServiceInstaller:
    """Installs ASTRA services to target environments."""

    def __init__(self):
        """Initialize service installer."""
        self.installations: dict[str, InstallationReport] = {}

    def install_service(
        self,
        installation_id: str,
        service_name: str,
        version: str,
        artifact_path: str,
        target_location: str,
        configuration: dict[str, Any] | None = None,
    ) -> InstallationReport:
        """Install a service from artifact.
        
        Args:
            installation_id: Unique installation identifier
            service_name: Name of the service
            version: Service version
            artifact_path: Path to service artifact
            target_location: Target installation directory
            configuration: Optional configuration to deploy
            
        Returns:
            InstallationReport
        """
        report = InstallationReport(
            installation_id=installation_id,
            service_name=service_name,
            version=version,
            target_location=target_location,
        )

        try:
            # Step 1: Pre-installation verification
            step = InstallationStep("pre_installation_check")
            report.steps.append(step)
            self._run_step(step, self._verify_artifact, artifact_path)

            # Step 2: Extract artifact
            step = InstallationStep("extract_artifact")
            report.steps.append(step)
            self._run_step(step, self._extract_artifact, artifact_path, target_location)

            # Step 3: Deploy configuration
            if configuration:
                step = InstallationStep("deploy_configuration")
                report.steps.append(step)
                self._run_step(step, self._deploy_configuration, target_location, configuration)
                report.configuration_deployed = True

            # Step 4: Install dependencies
            step = InstallationStep("install_dependencies")
            report.steps.append(step)
            self._run_step(step, self._install_dependencies, target_location)

            # Step 5: Health check
            step = InstallationStep("health_check")
            report.steps.append(step)
            self._run_step(step, self._perform_health_check, target_location)
            report.health_check_passed = True

            report.status = "SUCCESS"

        except Exception as e:
            report.status = "FAILED"
            report.error_message = str(e)

        report.completed_at_ms = time.time() * 1000
        self.installations[installation_id] = report
        return report

    def _run_step(
        self,
        step: InstallationStep,
        func,
        *args,
        **kwargs
    ) -> None:
        """Run an installation step.
        
        Args:
            step: InstallationStep to run
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        step.status = "RUNNING"
        step.started_at_ms = time.time() * 1000

        try:
            func(*args, **kwargs)
            step.status = "SUCCESS"
        except Exception as e:
            step.status = "FAILED"
            step.error_message = str(e)
            raise

        finally:
            step.completed_at_ms = time.time() * 1000
            step.duration_ms = step.completed_at_ms - step.started_at_ms

    @staticmethod
    def _verify_artifact(artifact_path: str) -> None:
        """Verify artifact integrity.
        
        Args:
            artifact_path: Path to artifact
        """
        path = Path(artifact_path)
        if not path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        metadata_file = path / "metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Artifact metadata not found: {metadata_file}")

    @staticmethod
    def _extract_artifact(artifact_path: str, target_location: str) -> None:
        """Extract artifact to target location.
        
        Args:
            artifact_path: Path to artifact
            target_location: Target directory
        """
        import shutil

        src_path = Path(artifact_path)
        content_dir = src_path / "content"
        target_dir = Path(target_location)

        target_dir.mkdir(parents=True, exist_ok=True)

        if content_dir.exists():
            for item in content_dir.iterdir():
                if item.is_dir():
                    shutil.copytree(item, target_dir / item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target_dir / item.name)

    @staticmethod
    def _deploy_configuration(
        target_location: str,
        configuration: dict[str, Any]
    ) -> None:
        """Deploy configuration to target location.
        
        Args:
            target_location: Target directory
            configuration: Configuration dictionary
        """
        config_path = Path(target_location) / "config.json"
        with open(config_path, "w") as f:
            json.dump(configuration, f, indent=2)

    @staticmethod
    def _install_dependencies(target_location: str) -> None:
        """Install service dependencies.
        
        Args:
            target_location: Target directory
        """
        requirements_file = Path(target_location) / "requirements.txt"
        if requirements_file.exists():
            subprocess.run(
                ["pip", "install", "-r", str(requirements_file)],
                check=True,
                capture_output=True,
            )

    @staticmethod
    def _perform_health_check(target_location: str) -> None:
        """Perform health check on installed service.
        
        Args:
            target_location: Target directory
        """
        init_file = Path(target_location) / "__init__.py"
        if not init_file.exists():
            raise RuntimeError("Installation verification failed")

    def get_installation_report(self, installation_id: str) -> InstallationReport | None:
        """Get installation report.
        
        Args:
            installation_id: Installation identifier
            
        Returns:
            InstallationReport or None if not found
        """
        return self.installations.get(installation_id)

    def list_installations(self) -> list[dict[str, Any]]:
        """List all installations.
        
        Returns:
            List of installation reports
        """
        return [r.to_dict() for r in self.installations.values()]

    def get_installation_stats(self) -> dict[str, Any]:
        """Get installation statistics.
        
        Returns:
            Dictionary with installation stats
        """
        successful = sum(1 for r in self.installations.values() if r.status == "SUCCESS")
        failed = sum(1 for r in self.installations.values() if r.status == "FAILED")

        return {
            "total_installations": len(self.installations),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(self.installations) if self.installations else 0,
            "configurations_deployed": sum(
                1 for r in self.installations.values()
                if r.configuration_deployed
            ),
            "health_checks_passed": sum(
                1 for r in self.installations.values()
                if r.health_check_passed
            ),
        }


class DeploymentOrchestrator:
    """Orchestrates service deployments across multiple instances."""

    def __init__(self):
        """Initialize deployment orchestrator."""
        self.installer = ServiceInstaller()
        self.deployments: list[InstallationReport] = []

    def deploy_to_cluster(
        self,
        service_name: str,
        version: str,
        artifact_path: str,
        target_nodes: list[dict[str, str]],
        configuration: dict[str, Any] | None = None,
    ) -> list[InstallationReport]:
        """Deploy service to multiple nodes.
        
        Args:
            service_name: Service name
            version: Service version
            artifact_path: Artifact path
            target_nodes: List of target node configs
            configuration: Optional configuration
            
        Returns:
            List of installation reports
        """
        reports = []

        for _i, node in enumerate(target_nodes):
            import uuid
            installation_id = str(uuid.uuid4())
            node_target = node.get("target_location", f"/opt/astra/{service_name}")

            report = self.installer.install_service(
                installation_id=installation_id,
                service_name=service_name,
                version=version,
                artifact_path=artifact_path,
                target_location=node_target,
                configuration=configuration,
            )

            reports.append(report)
            self.deployments.append(report)

        return reports

    def get_deployment_status(self) -> dict[str, Any]:
        """Get overall deployment status.
        
        Returns:
            Dictionary with deployment status
        """
        total = len(self.deployments)
        successful = sum(1 for r in self.deployments if r.status == "SUCCESS")
        failed = sum(1 for r in self.deployments if r.status == "FAILED")

        return {
            "total_deployments": total,
            "successful": successful,
            "failed": failed,
            "in_progress": sum(1 for r in self.deployments if r.status == "IN_PROGRESS"),
            "success_rate": successful / total if total > 0 else 0,
            "deployments": [r.to_dict() for r in self.deployments],
        }
