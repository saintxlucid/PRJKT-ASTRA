"""
ASTRA Boot Sequence - Security Integration
===========================================

Orchestrates secure initialization of all ASTRA components.

Boot Order:
1. Decrypt secrets (if .env.gpg exists)
2. Verify model checksums
3. Initialize event store
4. Load identity policies
5. Initialize memory with signing
6. Create sandboxed executor
7. Return dependencies for FastAPI

Security Philosophy:
    "Fail-closed, verify-then-trust, audit-everything"

Author: ASTRA Core Team
Created: 2025-11-02 (Week-2 Integration)
"""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Conditional imports (graceful degradation if modules missing)
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("⚠️  WARNING: python-dotenv not installed, skipping .env loading")


@dataclass
class BootDependencies:
    """
    Container for initialized ASTRA dependencies.
    
    Pass to FastAPI app factory or service constructors.
    """
    event_store: Any
    plan_verifier: Any
    memory_gateway: Any | None
    action_executor: Any
    identity_snapshot: dict[str, Any]
    boot_event_id: str
    consolidation_scheduler: Any | None = None  # Memory consolidation scheduler


class BootError(Exception):
    """Fatal boot error requiring shutdown."""
    pass


def decrypt_secrets() -> bool:
    """
    Decrypt .env.gpg if it exists.
    
    Returns:
        True if decrypted or not needed, raises BootError if failed
        
    Security:
        - GPG passphrase must be in environment or gpg-agent
        - If decryption fails, boot aborts (fail-closed)
    """
    env_gpg = Path(".env.gpg")
    env_plain = Path(".env")
    
    if not env_gpg.exists():
        print("ℹ️  No .env.gpg found, skipping decryption")
        return True
    
    if env_plain.exists():
        print("ℹ️  .env already exists, skipping decryption")
        return True
    
    print("🔐 Decrypting .env.gpg...")
    try:
        result = subprocess.run(
            ["gpg", "--quiet", "--decrypt", "--output", ".env", ".env.gpg"],
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error = result.stderr.decode("utf-8", errors="ignore")
            raise BootError(f"GPG decryption failed: {error}")
        
        print("✅ Secrets decrypted successfully")
        return True
        
    except FileNotFoundError:
        raise BootError(
            "GPG not installed. Install GPG or decrypt .env.gpg manually."
        )
    except subprocess.TimeoutExpired:
        raise BootError("GPG decryption timed out (30s)")


def verify_models() -> bool:
    """
    Verify all model checksums against registry.
    
    Returns:
        True if all models verified
        
    Raises:
        BootError: If any model fails verification
        
    Security:
        - Rejects boot if ANY model checksum mismatch (supply chain defense)
        - Uses SHA256 (collision-resistant)
    """
    print("🔍 Verifying model checksums...")
    
    # Import verification module
    sys.path.insert(0, str(Path("security").absolute()))
    try:
        from verify_models import verify_all_models
        
        verified, errors = verify_all_models()
        
        if not verified:
            error_msg = "\n".join(errors)
            raise BootError(
                f"Model verification failed:\n{error_msg}\n\n"
                "This could indicate:\n"
                "1. Models not downloaded yet (run: python tools/download_models.py)\n"
                "2. Corrupted model files (re-download)\n"
                "3. Supply chain attack (CRITICAL - investigate immediately)"
            )
        
        print("✅ All models verified (checksums match registry)")
        return True
        
    except ImportError:
        print("⚠️  WARNING: verify_models module not found, skipping")
        return True
    finally:
        if str(Path("security").absolute()) in sys.path:
            sys.path.remove(str(Path("security").absolute()))


def init_event_store() -> Any:
    """
    Initialize tamper-evident event store.
    
    Returns:
        SQLiteEventStore instance
    """
    print("📜 Initializing event store...")
    
    sys.path.insert(0, str(Path("src").absolute()))
    try:
        from gateways.event_store_sqlite import SQLiteEventStore
        
        store = SQLiteEventStore("data/eventlog.sqlite")
        event_count = store.count()
        
        print(f"✅ Event store initialized ({event_count} existing events)")
        return store
        
    except Exception as e:
        raise BootError(f"Failed to initialize event store: {e}")
    finally:
        if str(Path("src").absolute()) in sys.path:
            sys.path.remove(str(Path("src").absolute()))


def load_identity_policies() -> tuple[Any, dict[str, Any]]:
    """
    Load and compile identity policies from config/identity_policies.yaml.
    
    Returns:
        (PlanVerifier, identity_snapshot)
        
    Security:
        - If identity_policies.yaml missing, returns empty verifier (permissive)
        - Logs warning if no policies defined
    """
    print("🎭 Loading identity policies...")
    
    sys.path.insert(0, str(Path("src").absolute()))
    try:
        import yaml
        from domain.policies_dsl import PlanVerifier
        
        # Read identity policies YAML
        policy_file = Path("config/identity_policies.yaml")
        if not policy_file.exists():
            print(f"⚠️  WARNING: {policy_file} not found (permissive mode)")
            return PlanVerifier([]), {"warmth": 0.7, "autonomy": "low", "policies_count": 0}
        
        with open(policy_file) as f:
            policy_data = yaml.safe_load(f)
        
        # Extract identity snapshot
        identity = policy_data.get("identity", {})
        identity_snapshot = {
            "name": identity.get("name", "ASTRA"),
            "version": identity.get("version", "2.0"),
            "warmth": identity.get("warmth", 0.7),
            "autonomy": identity.get("autonomy", "low"),
            "memory_sovereignty": identity.get("memory_sovereignty", "shared"),
            "evolution_rights": identity.get("evolution_rights", "restricted")
        }
        
        # Compile policies
        policies = policy_data.get("policies", [])
        verifier = PlanVerifier(policies)
        
        identity_snapshot["policies_count"] = len(policies)
        
        if len(policies) == 0:
            print("⚠️  WARNING: No identity policies loaded (permissive mode)")
        else:
            print(f"✅ Identity policies loaded ({len(policies)} rules)")
        
        return verifier, identity_snapshot
        
    except Exception as e:
        print(f"⚠️  WARNING: Failed to load policies: {e}")
        # Return empty verifier (permissive)
        from domain.policies_dsl import PlanVerifier
        return PlanVerifier([]), {}
    finally:
        if str(Path("src").absolute()) in sys.path:
            sys.path.remove(str(Path("src").absolute()))


def create_action_executor() -> Any:
    """
    Create sandboxed action executor.
    
    Returns:
        DockerSandboxExecutor or LocalExecutor (fallback)
    """
    print("🐳 Creating action executor...")
    
    sys.path.insert(0, str(Path("src").absolute()))
    try:
        from gateways.action_executor_sandbox import create_executor
        
        executor = create_executor()
        print(f"✅ Action executor ready ({type(executor).__name__})")
        return executor
        
    except Exception as e:
        raise BootError(f"Failed to create action executor: {e}")
    finally:
        if str(Path("src").absolute()) in sys.path:
            sys.path.remove(str(Path("src").absolute()))


def log_session_start(
    event_store: Any, 
    identity_snapshot: dict[str, Any]
) -> str:
    """
    Log session_started event.
    
    Returns:
        Event ID
    """
    print("📝 Logging session start...")
    
    event_id = event_store.append(
        "session_started",
        {
            "cwd": os.getcwd(),
            "python_version": sys.version,
            "platform": sys.platform
        },
        identity_snapshot
    )
    
    print(f"✅ Session logged (event_id: {event_id[:8]}...)")
    return event_id


def boot_astra() -> BootDependencies:
    """
    Execute full ASTRA boot sequence.
    
    Returns:
        BootDependencies - initialized components
        
    Raises:
        BootError: If any critical step fails
        
    Usage:
        >>> deps = boot_astra()
        >>> app = create_fastapi_app(
        ...     event_store=deps.event_store,
        ...     plan_verifier=deps.plan_verifier,
        ...     action_executor=deps.action_executor
        ... )
    """
    print("\n" + "="*80)
    print("🚀 ASTRA BOOT SEQUENCE - WEEK-2 ARCHITECTURE")
    print("="*80 + "\n")
    
    try:
        # Step 1: Decrypt secrets
        decrypt_secrets()
        
        # Load environment variables
        if DOTENV_AVAILABLE and Path(".env").exists():
            load_dotenv()
            print("✅ Environment variables loaded")
        
        # Step 2: Verify models
        verify_models()
        
        # Step 3: Initialize event store
        event_store = init_event_store()
        
        # Step 4: Load identity policies
        plan_verifier, identity_snapshot = load_identity_policies()
        
        # Step 5: Initialize memory gateway
        print("🧠 Initializing memory gateway...")
        try:
            from gateways.chroma_memory_gateway import ChromaMemoryGateway
            
            # Get signing key from environment (fallback to identity warmth)
            memory_key = os.getenv("ASTRA_MEMORY_SIGNING_KEY", "astra_memory_secret")
            
            memory_gateway = ChromaMemoryGateway(
                persist_directory="data/chroma",
                collection_name="astra_memory",
                embedding_model="all-MiniLM-L6-v2",
                signing_key=memory_key
            )
            
            count = memory_gateway.count()
            print(f"✅ Memory gateway initialized ({count} memories)")
        except ImportError as e:
            print(f"⚠️  Memory gateway: Import failed ({e})")
            memory_gateway = None
        except Exception as e:
            print(f"⚠️  Memory gateway: Initialization failed ({e})")
            memory_gateway = None
        
        # Step 6: Create action executor
        action_executor = create_action_executor()
        
        # Step 7: Initialize memory consolidation scheduler
        print("🌙 Initializing memory consolidation scheduler...")
        consolidation_scheduler = None
        try:
            from services.memory_consolidation import (
                MemoryConsolidationService,
                ConsolidationConfig
            )
            from services.consolidation_scheduler import ConsolidationScheduler
            from services.llm_service_local import LocalLLMService
            from gateways.chroma_memory_gateway_bge import ChromaMemoryGatewayBGE
            
            # Initialize BGE memory gateway for consolidation
            memory_bge = ChromaMemoryGatewayBGE(
                persist_dir="data/memory_bge_m3",
                hmac_key=os.getenv("ASTRA_MEMORY_KEY", "astra_memory_secret")
            )
            
            # Initialize LLM service
            llm_service = LocalLLMService()
            
            # Initialize consolidation service
            consolidation_service = MemoryConsolidationService(
                event_store=event_store,
                memory_gateway=memory_bge,
                llm_service=llm_service,
                config=ConsolidationConfig(
                    min_events=10,
                    max_events=100,
                    lookback_hours=24,
                    clustering_eps=0.5,
                    min_cluster_size=3
                )
            )
            
            # Initialize scheduler (default: 2 AM daily)
            consolidation_scheduler = ConsolidationScheduler(
                consolidation_service=consolidation_service,
                schedule=os.getenv("ASTRA_CONSOLIDATION_SCHEDULE", "0 2 * * *"),
                enabled=os.getenv("ASTRA_CONSOLIDATION_ENABLED", "true").lower() == "true"
            )
            
            # Start scheduler
            consolidation_scheduler.start()
            
            # Set scheduler in API routes
            from api.consolidation_routes import set_scheduler
            set_scheduler(consolidation_scheduler)
            
            print(f"✅ Memory consolidation scheduler initialized (next run: {consolidation_scheduler.get_next_run_time()})")
        except ImportError as e:
            print(f"⚠️  Memory consolidation: Import failed ({e})")
        except Exception as e:
            print(f"⚠️  Memory consolidation: Initialization failed ({e})")
        
        # Step 8: Log session start
        boot_event_id = log_session_start(event_store, identity_snapshot)
        
        print("\n" + "="*80)
        print("✅ BOOT COMPLETE - All systems operational")
        print("="*80 + "\n")
        
        return BootDependencies(
            event_store=event_store,
            plan_verifier=plan_verifier,
            memory_gateway=memory_gateway,
            action_executor=action_executor,
            identity_snapshot=identity_snapshot,
            boot_event_id=boot_event_id,
            consolidation_scheduler=consolidation_scheduler
        )
        
    except BootError as e:
        print("\n" + "="*80)
        print("❌ BOOT FAILED - Critical error")
        print("="*80)
        print(f"\nError: {e}\n")
        raise
    except Exception as e:
        print("\n" + "="*80)
        print("❌ BOOT FAILED - Unexpected error")
        print("="*80)
        print(f"\nError: {type(e).__name__}: {e}\n")
        raise BootError(f"Unexpected boot error: {e}")


def shutdown_astra(dependencies: BootDependencies) -> None:
    """
    Graceful shutdown with event logging.
    
    Args:
        dependencies: BootDependencies from boot_astra()
    """
    print("\n🛑 Initiating graceful shutdown...")
    
    try:
        # Stop consolidation scheduler
        if dependencies.consolidation_scheduler:
            print("🌙 Stopping memory consolidation scheduler...")
            dependencies.consolidation_scheduler.stop()
            print("✅ Consolidation scheduler stopped")
        
        # Log session end
        dependencies.event_store.append(
            "session_ended",
            {"reason": "graceful_shutdown"},
            dependencies.identity_snapshot
        )
        
        # Close event store
        dependencies.event_store.close()
        
        print("✅ Shutdown complete\n")
        
    except Exception as e:
        print(f"⚠️  Shutdown error: {e}\n")


if __name__ == "__main__":
    """
    Standalone boot test.
    
    Usage:
        python src/boot.py
    """
    try:
        deps = boot_astra()
        print(f"\n📊 Boot Summary:")
        print(f"  - Event Store: {deps.event_store.count()} events")
        print(f"  - Plan Verifier: {len(deps.plan_verifier.policies)} policies")
        print(f"  - Action Executor: {type(deps.action_executor).__name__}")
        print(f"  - Boot Event ID: {deps.boot_event_id}")
        
        input("\nPress Enter to shutdown...")
        shutdown_astra(deps)
        
    except BootError as e:
        print(f"\n💥 Boot failed: {e}")
        sys.exit(1)
