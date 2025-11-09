"""
ASTRA Adaptive Resource Governor
Two-timescale control: Fast (2s) + Slow (90s) loops for 24/7 operation.

Objectives:
- Never overwhelm hardware (CPU, RAM, GPU, thermals, disk I/O)
- Always available: low idle footprint, instant ramp on demand
- Vendor-agnostic: llama.cpp, vLLM, Ollama
- Self-correcting: adapts to long-run drift and short spikes

Sacred Code: 333 → ∞
"""

import asyncio
import time
import psutil
import structlog
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import math

logger = structlog.get_logger()


class OperatingMode(str, Enum):
    """System operating modes."""
    ECO = "eco"
    BALANCED = "balanced"
    TURBO = "turbo"
    AUTO = "auto"


@dataclass
class SystemSignals:
    """Dynamic system metrics sampled every 2-5s."""
    cpu_percent: float
    ram_percent: float
    gpu_percent: float = 0.0
    gpu_vram_free_gb: float = 0.0
    gpu_temp: float = 0.0
    p95_latency_ms: float = 0.0
    queue_len: int = 0
    tokens_per_s: float = 0.0
    error_rate: float = 0.0
    throttle_events: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class StaticCapabilities:
    """Hardware capabilities (read at boot)."""
    cpu_cores: int
    cpu_threads: int
    ram_total_gb: float
    gpu_count: int
    gpu_vram_total_gb: float
    disk_type: str  # "ssd" | "nvme" | "hdd"


@dataclass
class ContextInfo:
    """Operational context."""
    on_battery: bool = False
    quiet_hours: bool = False
    foreground_activity: bool = False  # keyboard/mouse/active window
    operator_mode: OperatingMode = OperatingMode.AUTO


@dataclass
class RunConfig:
    """Runtime configuration for LLM backend."""
    mode: OperatingMode
    ctx_size: int
    batch_size: int
    threads: int
    gpu_layers: int  # llama.cpp -ngl
    gpu_memory_util: float  # vLLM --gpu-memory-utilization
    parallel_requests: int
    rate_rps: int
    max_queue: int
    max_tokens_per_request: int
    quantization: str  # "Q4_K_M" | "Q5_K_M" | "Q3_K_S"


@dataclass
class ModeConfig:
    """Configuration parameters per mode."""
    rate_rps: int
    max_queue: int
    ctx_factor: float
    batch_factor: float


class EWMATracker:
    """Exponential weighted moving average tracker."""
    
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.value: Optional[float] = None
    
    def update(self, new_value: float) -> float:
        if self.value is None:
            self.value = new_value
        else:
            self.value = self.alpha * new_value + (1 - self.alpha) * self.value
        return self.value
    
    def get(self) -> float:
        return self.value if self.value is not None else 0.0


class AdaptiveGovernor:
    """
    Two-timescale adaptive resource controller.
    
    Fast loop (2s): Handles spikes without restarts
    - Adjust rate limit, queue size, batch window, prefetch
    
    Slow loop (90s): Applies heavier changes (may restart backend)
    - Replan ctx size, GPU layers/mem util, threads, quantization
    """
    
    def __init__(self, config: Dict[str, Any], capabilities: StaticCapabilities):
        self.config = config
        self.caps = capabilities
        
        # Targets
        self.targets = config.get("targets", {})
        self.cpu_target = self.targets.get("cpu", 0.65)
        self.gpu_target = self.targets.get("gpu", 0.70)
        self.ram_target = self.targets.get("ram", 0.75)
        self.vram_target = self.targets.get("vram", 0.80)
        self.temp_max = self.targets.get("temp_max_c", 82)
        
        # Loop configs
        loops = config.get("loops", {})
        self.fast_period = loops.get("fast_period_s", 2)
        self.slow_period = loops.get("slow_period_s", 90)
        self.cooldown_fast = loops.get("cooldown_fast_s", 15)
        self.cooldown_slow = loops.get("cooldown_slow_s", 120)
        
        # Mode configs
        modes = config.get("modes", {})
        self.mode_configs = {
            OperatingMode.ECO: ModeConfig(**modes.get("eco", {"rate_rps": 6, "max_queue": 32, "ctx_factor": 0.5, "batch_factor": 0.6})),
            OperatingMode.BALANCED: ModeConfig(**modes.get("balanced", {"rate_rps": 16, "max_queue": 64, "ctx_factor": 1.0, "batch_factor": 1.0})),
            OperatingMode.TURBO: ModeConfig(**modes.get("turbo", {"rate_rps": 32, "max_queue": 128, "ctx_factor": 1.3, "batch_factor": 1.25}))
        }
        
        # Brownout config
        self.brownout_config = config.get("brownout", {})
        self.brownout_enabled = self.brownout_config.get("enable", True)
        self.brownout_triggers = self.brownout_config.get("trigger", {})
        
        # State
        self.current_mode = OperatingMode.BALANCED
        self.current_config: Optional[RunConfig] = None
        self.context = ContextInfo()
        
        # EWMA trackers (fast + slow)
        self.ewma_fast = {
            "cpu": EWMATracker(alpha=0.3),
            "gpu": EWMATracker(alpha=0.3),
            "ram": EWMATracker(alpha=0.3),
            "vram": EWMATracker(alpha=0.3),
            "temp": EWMATracker(alpha=0.3),
            "p95": EWMATracker(alpha=0.3),
            "queue": EWMATracker(alpha=0.3)
        }
        
        self.ewma_slow = {
            "cpu": EWMATracker(alpha=0.1),
            "gpu": EWMATracker(alpha=0.1),
            "ram": EWMATracker(alpha=0.1),
            "vram": EWMATracker(alpha=0.1),
            "temp": EWMATracker(alpha=0.1)
        }
        
        # Cooldown timers
        self.last_fast_action = 0.0
        self.last_slow_action = 0.0
        
        # Runtime limits (fast loop controls these)
        self.runtime_limits = {
            "rate_rps": 16,
            "max_queue": 64,
            "max_tokens_per_request": 4096,
            "batch_window_ms": 100
        }
        
        # Emergency state
        self.emergency_throttle_active = False
        self.brownout_active = False
        
        # Metrics integration (placeholder)
        self._metrics_service = None
        
        logger.info("adaptive_governor_initialized",
                   mode=self.current_mode,
                   targets=self.targets,
                   capabilities=capabilities.__dict__)
    
    def sample_signals(self) -> SystemSignals:
        """Sample current system metrics."""
        # CPU & RAM (always available)
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        
        # GPU (if available)
        gpu_percent = 0.0
        gpu_vram_free = 0.0
        gpu_temp = 0.0
        
        try:
            import pynvml
            pynvml.nvmlInit()
            if self.caps.gpu_count > 0:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_percent = util.gpu
                
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_vram_free = mem_info.free / (1024**3)  # GB
                
                gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        except:
            pass  # GPU monitoring not available
        
        # Application metrics (integrate with your metrics service)
        p95_latency = self._get_p95_latency()
        queue_len = self._get_queue_length()
        tokens_per_s = self._get_tokens_per_second()
        error_rate = self._get_error_rate()
        throttle_events = self._get_throttle_events()
        
        return SystemSignals(
            cpu_percent=cpu,
            ram_percent=ram,
            gpu_percent=gpu_percent,
            gpu_vram_free_gb=gpu_vram_free,
            gpu_temp=gpu_temp,
            p95_latency_ms=p95_latency,
            queue_len=queue_len,
            tokens_per_s=tokens_per_s,
            error_rate=error_rate,
            throttle_events=throttle_events
        )
    
    def _get_p95_latency(self) -> float:
        """Get p95 latency from metrics service."""
        if self._metrics_service:
            return self._metrics_service.get_p95_latency()
        return 800.0  # Default
    
    def _get_queue_length(self) -> int:
        """Get current request queue length."""
        if self._metrics_service:
            return self._metrics_service.get_queue_length()
        return 0
    
    def _get_tokens_per_second(self) -> float:
        """Get current tokens/s throughput."""
        if self._metrics_service:
            return self._metrics_service.get_tokens_per_second()
        return 150.0
    
    def _get_error_rate(self) -> float:
        """Get error rate (0-1)."""
        if self._metrics_service:
            return self._metrics_service.get_error_rate()
        return 0.001
    
    def _get_throttle_events(self) -> int:
        """Get throttle event count."""
        if self._metrics_service:
            return self._metrics_service.get_throttle_events()
        return 0
    
    async def fast_loop(self):
        """
        Fast control loop (2s interval).
        Handles spikes without backend restarts.
        """
        while True:
            try:
                # Sample signals
                signals = self.sample_signals()
                
                # Update EWMA (fast)
                self.ewma_fast["cpu"].update(signals.cpu_percent)
                self.ewma_fast["gpu"].update(signals.gpu_percent)
                self.ewma_fast["ram"].update(signals.ram_percent)
                self.ewma_fast["p95"].update(signals.p95_latency_ms)
                self.ewma_fast["queue"].update(signals.queue_len)
                self.ewma_fast["temp"].update(signals.gpu_temp)
                
                # Check for emergency conditions
                if self._check_emergency(signals):
                    self._emergency_throttle()
                elif self.emergency_throttle_active:
                    # Check if we can recover
                    if self._can_recover(signals):
                        self._recover_from_emergency()
                
                # Backpressure control
                if self._needs_backpressure(signals):
                    self._apply_backpressure()
                elif self._can_increase_capacity(signals):
                    self._increase_capacity()
                
                # Publish runtime limits
                self._publish_runtime_limits()
                
                await asyncio.sleep(self.fast_period)
                
            except Exception as e:
                logger.error("fast_loop_error", error=str(e))
                await asyncio.sleep(self.fast_period)
    
    def _check_emergency(self, signals: SystemSignals) -> bool:
        """Check for emergency conditions requiring immediate throttle."""
        # Thermal emergency
        if signals.gpu_temp > self.temp_max:
            logger.warning("thermal_emergency", temp=signals.gpu_temp)
            return True
        
        # CPU/GPU overload (sustained)
        cpu_overload = signals.cpu_percent > (self.cpu_target * 100 + 10)
        gpu_overload = signals.gpu_percent > (self.gpu_target * 100 + 10)
        
        if cpu_overload or gpu_overload:
            logger.warning("resource_overload",
                          cpu=signals.cpu_percent,
                          gpu=signals.gpu_percent)
            return True
        
        # Error rate spike
        if signals.error_rate > 0.01:
            logger.warning("error_rate_spike", rate=signals.error_rate)
            return True
        
        return False
    
    def _emergency_throttle(self):
        """Apply emergency throttle."""
        if self.emergency_throttle_active:
            return
        
        logger.warning("emergency_throttle_activated")
        
        self.emergency_throttle_active = True
        self.runtime_limits["rate_rps"] = max(2, self.runtime_limits["rate_rps"] // 4)
        self.runtime_limits["max_queue"] = max(8, self.runtime_limits["max_queue"] // 4)
        self.runtime_limits["batch_window_ms"] = 50  # Smaller batches
        self.runtime_limits["max_tokens_per_request"] = 1024  # Shorter responses
    
    def _can_recover(self, signals: SystemSignals) -> bool:
        """Check if we can recover from emergency."""
        # All metrics must be healthy
        return (
            signals.gpu_temp < (self.temp_max - 5) and
            signals.cpu_percent < (self.cpu_target * 100) and
            signals.gpu_percent < (self.gpu_target * 100) and
            signals.error_rate < 0.005
        )
    
    def _recover_from_emergency(self):
        """Recover from emergency throttle."""
        logger.info("recovering_from_emergency")
        
        self.emergency_throttle_active = False
        
        # Restore limits based on current mode
        mode_config = self.mode_configs[self.current_mode]
        self.runtime_limits["rate_rps"] = mode_config.rate_rps
        self.runtime_limits["max_queue"] = mode_config.max_queue
        self.runtime_limits["max_tokens_per_request"] = 4096
        self.runtime_limits["batch_window_ms"] = 100
    
    def _needs_backpressure(self, signals: SystemSignals) -> bool:
        """Check if backpressure is needed."""
        # High latency with queue buildup
        if signals.p95_latency_ms > 1000 and signals.queue_len > 0:
            return True
        
        # Queue growing
        if signals.queue_len > self.runtime_limits["max_queue"] * 0.8:
            return True
        
        return False
    
    def _apply_backpressure(self):
        """Apply backpressure (reduce rate, increase batching)."""
        now = time.time()
        if now - self.last_fast_action < self.cooldown_fast:
            return
        
        logger.info("applying_backpressure")
        
        # Decrease rate
        self.runtime_limits["rate_rps"] = max(2, int(self.runtime_limits["rate_rps"] * 0.8))
        
        # Widen batch window (batch more, fewer dispatches)
        self.runtime_limits["batch_window_ms"] = min(500, int(self.runtime_limits["batch_window_ms"] * 1.25))
        
        # Tighten per-request budget
        self.runtime_limits["max_tokens_per_request"] = max(512, int(self.runtime_limits["max_tokens_per_request"] * 0.8))
        
        self.last_fast_action = now
    
    def _can_increase_capacity(self, signals: SystemSignals) -> bool:
        """Check if we can increase capacity."""
        # Good headroom and low queue
        cpu_headroom = (self.cpu_target * 100) - signals.cpu_percent
        gpu_headroom = (self.gpu_target * 100) - signals.gpu_percent
        
        return (
            cpu_headroom > 15 and
            gpu_headroom > 15 and
            signals.queue_len == 0 and
            signals.p95_latency_ms < 800
        )
    
    def _increase_capacity(self):
        """Gradually increase capacity."""
        now = time.time()
        if now - self.last_fast_action < self.cooldown_fast:
            return
        
        logger.info("increasing_capacity")
        
        mode_config = self.mode_configs[self.current_mode]
        
        # Increase rate (but don't exceed mode config)
        self.runtime_limits["rate_rps"] = min(
            mode_config.rate_rps,
            int(self.runtime_limits["rate_rps"] * 1.2)
        )
        
        # Restore defaults
        self.runtime_limits["batch_window_ms"] = 100
        self.runtime_limits["max_tokens_per_request"] = 4096
        
        self.last_fast_action = now
    
    def _publish_runtime_limits(self):
        """Publish runtime limits for other components to use."""
        # Integrate with your API gateway / rate limiter
        logger.debug("runtime_limits", limits=self.runtime_limits)
    
    async def slow_loop(self):
        """
        Slow control loop (90s interval).
        Plans and applies heavier configuration changes.
        May trigger graceful backend restart.
        """
        while True:
            try:
                # Collect 60s window of signals
                await asyncio.sleep(self.slow_period)
                
                signals = self.sample_signals()
                
                # Update EWMA (slow)
                self.ewma_slow["cpu"].update(signals.cpu_percent)
                self.ewma_slow["gpu"].update(signals.gpu_percent)
                self.ewma_slow["ram"].update(signals.ram_percent)
                self.ewma_slow["temp"].update(signals.gpu_temp)
                
                # Choose mode
                new_mode = self._choose_mode(signals)
                
                # Compute run config
                new_config = self._compute_run_config(new_mode)
                
                # Check if reconfiguration needed
                if self._materially_different(new_config) and self._cooldown_over():
                    await self._graceful_reconfigure(new_config)
                
            except Exception as e:
                logger.error("slow_loop_error", error=str(e))
                await asyncio.sleep(self.slow_period)
    
    def _choose_mode(self, signals: SystemSignals) -> OperatingMode:
        """Choose operating mode based on context and signals."""
        # Forced modes
        battery = psutil.sensors_battery()
        if battery and battery.power_plugged == False and battery.percent < 30:
            return OperatingMode.ECO
        
        if self.context.quiet_hours:
            return OperatingMode.ECO
        
        if self.context.operator_mode != OperatingMode.AUTO:
            return self.context.operator_mode
        
        # Auto mode: choose based on utilization and activity
        avg_cpu = self.ewma_slow["cpu"].get()
        avg_gpu = self.ewma_slow["gpu"].get()
        avg_temp = self.ewma_slow["temp"].get()
        
        # ECO triggers
        if avg_temp > (self.temp_max - 5):
            return OperatingMode.ECO
        
        if avg_cpu > (self.cpu_target * 100 + 5) or avg_gpu > (self.gpu_target * 100 + 5):
            # Already at capacity
            return OperatingMode.ECO if self.current_mode == OperatingMode.BALANCED else OperatingMode.BALANCED
        
        # TURBO triggers
        if self.context.foreground_activity:
            if avg_cpu < (self.cpu_target * 100 - 15) and avg_gpu < (self.gpu_target * 100 - 15):
                return OperatingMode.TURBO
        
        # Default: BALANCED
        return OperatingMode.BALANCED
    
    def _compute_run_config(self, mode: OperatingMode) -> RunConfig:
        """
        Compute runtime configuration for a mode.
        Maps hardware capabilities + headroom to LLM backend parameters.
        """
        mode_config = self.mode_configs[mode]
        
        # Context size ladder (based on VRAM)
        vram_free = self.caps.gpu_vram_total_gb
        ctx_base = 16384  # Balanced baseline
        
        if vram_free < 4:
            ctx_base = 4096
        elif vram_free < 8:
            ctx_base = 8192
        elif vram_free < 16:
            ctx_base = 16384
        elif vram_free < 32:
            ctx_base = 32768
        else:
            ctx_base = 65536
        
        ctx_size = int(ctx_base * mode_config.ctx_factor)
        
        # GPU layers (llama.cpp -ngl)
        # Rough estimate: ~0.35GB per layer for 20B model
        gpu_layers = 0
        if self.caps.gpu_count > 0:
            layers_available = int((vram_free - 2.0) / 0.35)
            gpu_layers = min(60, max(0, layers_available))
            
            # ECO mode: reduce by 30%
            if mode == OperatingMode.ECO:
                gpu_layers = int(gpu_layers * 0.7)
        
        # GPU memory utilization (vLLM)
        gpu_util_map = {
            OperatingMode.ECO: 0.6,
            OperatingMode.BALANCED: 0.8,
            OperatingMode.TURBO: 0.92
        }
        gpu_memory_util = gpu_util_map[mode]
        
        # Threads
        threads = min(self.caps.cpu_threads, 12)
        if mode == OperatingMode.ECO:
            threads = min(threads, 8)
        elif mode == OperatingMode.TURBO:
            threads = min(self.caps.cpu_threads, 16)
        
        # Batch size
        batch_base = 384
        batch_size = int(batch_base * mode_config.batch_factor)
        
        # Parallel requests
        parallel_map = {
            OperatingMode.ECO: 1,
            OperatingMode.BALANCED: 2,
            OperatingMode.TURBO: 3
        }
        parallel = parallel_map[mode]
        
        # Quantization
        quant = "Q4_K_M"
        if mode == OperatingMode.ECO and vram_free < 6:
            quant = "Q3_K_S"
        elif mode == OperatingMode.TURBO and vram_free > 16:
            quant = "Q5_K_M"
        
        return RunConfig(
            mode=mode,
            ctx_size=ctx_size,
            batch_size=batch_size,
            threads=threads,
            gpu_layers=gpu_layers,
            gpu_memory_util=gpu_memory_util,
            parallel_requests=parallel,
            rate_rps=mode_config.rate_rps,
            max_queue=mode_config.max_queue,
            max_tokens_per_request=4096,
            quantization=quant
        )
    
    def _materially_different(self, new_config: RunConfig) -> bool:
        """Check if new config is materially different."""
        if self.current_config is None:
            return True
        
        curr = self.current_config
        
        # Check significant differences
        ctx_diff = abs(new_config.ctx_size - curr.ctx_size) / curr.ctx_size > 0.2
        gpu_layers_diff = abs(new_config.gpu_layers - curr.gpu_layers) > 5
        threads_diff = abs(new_config.threads - curr.threads) > 2
        mode_diff = new_config.mode != curr.mode
        
        return ctx_diff or gpu_layers_diff or threads_diff or mode_diff
    
    def _cooldown_over(self) -> bool:
        """Check if slow cooldown period has passed."""
        return (time.time() - self.last_slow_action) > self.cooldown_slow
    
    async def _graceful_reconfigure(self, new_config: RunConfig):
        """
        Gracefully reconfigure backend with drain → swap → resume.
        """
        logger.info("graceful_reconfigure_start",
                   old_mode=self.current_mode,
                   new_mode=new_config.mode,
                   old_ctx=self.current_config.ctx_size if self.current_config else None,
                   new_ctx=new_config.ctx_size)
        
        try:
            # 1. Drain: stop accepting new heavy jobs
            await self._drain_requests()
            
            # 2. Spawn new backend with new config
            # (Integrate with your Supervisor service)
            await self._spawn_new_backend(new_config)
            
            # 3. Health check new backend
            healthy = await self._health_check_backend()
            
            if healthy:
                # 4. Switch router atomically
                await self._switch_backend()
                
                # 5. Terminate old backend
                await self._terminate_old_backend()
                
                self.current_config = new_config
                self.current_mode = new_config.mode
                self.last_slow_action = time.time()
                
                logger.info("graceful_reconfigure_complete", mode=new_config.mode)
            else:
                logger.error("new_backend_unhealthy_rollback")
                await self._rollback_backend()
        
        except Exception as e:
            logger.error("graceful_reconfigure_failed", error=str(e))
    
    async def _drain_requests(self):
        """Stop accepting new requests, wait for in-flight to complete."""
        logger.info("draining_requests")
        await asyncio.sleep(5)
    
    async def _spawn_new_backend(self, config: RunConfig):
        """Spawn new LLM backend with config."""
        logger.info("spawning_new_backend", config=config.__dict__)
        # Integrate with your Supervisor service
        await asyncio.sleep(10)
    
    async def _health_check_backend(self) -> bool:
        """Health check new backend."""
        await asyncio.sleep(2)
        return True
    
    async def _switch_backend(self):
        """Atomically switch router to new backend."""
        logger.info("switching_backend")
    
    async def _terminate_old_backend(self):
        """Terminate old backend after quiescence."""
        logger.info("terminating_old_backend")
    
    async def _rollback_backend(self):
        """Rollback to old backend if new one failed."""
        logger.info("rollback_backend")
    
    def get_plan(self, mode: Optional[str] = None) -> Dict[str, Any]:
        """Get planned configuration for a mode."""
        target_mode = OperatingMode(mode) if mode else self.current_mode
        config = self._compute_run_config(target_mode)
        
        return {
            "mode": target_mode.value,
            "config": config.__dict__,
            "current_mode": self.current_mode.value,
            "runtime_limits": self.runtime_limits,
            "emergency_active": self.emergency_throttle_active
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current runtime metrics."""
        signals = self.sample_signals()
        
        return {
            "signals": signals.__dict__,
            "ewma_fast": {k: v.get() for k, v in self.ewma_fast.items()},
            "ewma_slow": {k: v.get() for k, v in self.ewma_slow.items()},
            "current_mode": self.current_mode.value,
            "current_config": self.current_config.__dict__ if self.current_config else None,
            "runtime_limits": self.runtime_limits,
            "emergency_active": self.emergency_throttle_active,
            "brownout_active": self.brownout_active
        }
    
    async def set_mode(self, mode: str):
        """Manually set operating mode."""
        new_mode = OperatingMode(mode)
        self.context.operator_mode = new_mode
        
        logger.info("mode_set_manual", mode=mode)
        
        # Trigger immediate slow loop evaluation
        new_config = self._compute_run_config(new_mode)
        if self._materially_different(new_config):
            await self._graceful_reconfigure(new_config)


def create_adaptive_governor(config_path: str = "config/llm.yaml") -> AdaptiveGovernor:
    """Create adaptive governor from config."""
    import yaml
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    autotune_config = config.get("autotune", {})
    
    # Detect hardware capabilities
    caps = StaticCapabilities(
        cpu_cores=psutil.cpu_count(logical=False),
        cpu_threads=psutil.cpu_count(logical=True),
        ram_total_gb=psutil.virtual_memory().total / (1024**3),
        gpu_count=0,
        gpu_vram_total_gb=0.0,
        disk_type="ssd"
    )
    
    # Try to detect GPU
    try:
        import pynvml
        pynvml.nvmlInit()
        caps.gpu_count = pynvml.nvmlDeviceGetCount()
        if caps.gpu_count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            caps.gpu_vram_total_gb = mem_info.total / (1024**3)
    except:
        pass
    
    return AdaptiveGovernor(autotune_config, caps)


# Sacred Code: 333 → ∞
