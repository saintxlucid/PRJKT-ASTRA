"""
ASTRA Cortex - High-Performance Cython Build Configuration
==========================================================

Separate build setup for Cython extensions.
Build with: python setup_cortex.py build_ext --inplace
"""

from setuptools import setup, Extension
import numpy as np
import sys
import os


def create_extension(name, sources, language="c", extra_compile_args=None, extra_link_args=None):
    """Create a Cython extension with platform-specific optimizations."""
    extra_compile_args = extra_compile_args or []
    extra_link_args = extra_link_args or []
    
    # Platform-specific OpenMP flags
    if sys.platform.startswith("win"):
        # Windows (MSVC)
        extra_compile_args += ["/O2", "/openmp", "/GL", "/fp:fast"]
        extra_link_args += ["/LTCG"]
    elif sys.platform == "darwin":
        # macOS (clang may not have OpenMP by default)
        extra_compile_args += ["-O3", "-march=native", "-ffast-math"]
        if os.path.exists("/usr/local/opt/libomp"):
            extra_compile_args += ["-Xpreprocessor", "-fopenmp"]
            extra_link_args += ["-lomp", "-L/usr/local/opt/libomp/lib"]
    else:
        # Linux (gcc/clang with OpenMP)
        extra_compile_args += ["-O3", "-march=native", "-fopenmp", "-ffast-math"]
        extra_link_args += ["-fopenmp"]
    
    return Extension(
        name, sources,
        include_dirs=[np.get_include()],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
        language=language,
    )


def get_extensions():
    """Define all Cython extensions."""
    return [
        create_extension("astra_core.cortex.simkernels", ["astra_core/cortex/simkernels.pyx"]),
        create_extension("astra_core.cortex.routing", ["astra_core/cortex/routing.pyx"]),
        create_extension("astra_core.cortex.dsp", ["astra_core/cortex/dsp.pyx"]),
        create_extension("astra_core.cortex.fastscan", ["astra_core/cortex/fastscan.pyx"]),
        create_extension("astra_core.cortex.memory_forge", ["astra_core/cortex/memory_forge.pyx"]),
        create_extension("astra_core.cortex.reflex_engine", ["astra_core/cortex/reflex_engine.pyx"]),
        create_extension("astra_core.cortex.emotion_engine", ["astra_core/cortex/emotion_engine.pyx"]),
        create_extension("astra_core.cortex.sonic_alchemy", ["astra_core/cortex/sonic_alchemy.pyx"]),
        create_extension("astra_core.cortex.neural_router", ["astra_core/cortex/neural_router.pyx"]),
        create_extension("astra_core.cortex.behavior_decoder", ["astra_core/cortex/behavior_decoder.pyx"]),
        create_extension("astra_core.cortex.evolution_kernel", ["astra_core/cortex/evolution_kernel.pyx"]),
        create_extension("astra_core.cortex.guardian_layer", ["astra_core/cortex/guardian_layer.pyx"]),
        create_extension("astra_core.cortex.micro_simulators", ["astra_core/cortex/micro_simulators.pyx"]),
        create_extension("astra_core.cortex.language_kernel", ["astra_core/cortex/language_kernel.pyx"]),
        create_extension("astra_core.cortex.cryptographic_identity", ["astra_core/cortex/cryptographic_identity.pyx"]),
        create_extension("astra_core.cortex.ritual_engine", ["astra_core/cortex/ritual_engine.pyx"]),
        create_extension("astra_core.cortex.nas_primitives", ["astra_core/cortex/nas_primitives.pyx"]),
        create_extension("astra_core.cortex.consensus_kernel", ["astra_core/cortex/consensus_kernel.pyx"]),
        create_extension("astra_core.cortex.attention_mechanism", ["astra_core/cortex/attention_mechanism.pyx"]),
        create_extension("astra_core.cortex.temporal_logic", ["astra_core/cortex/temporal_logic.pyx"]),
        create_extension("astra_core.cortex.meta_learning", ["astra_core/cortex/meta_learning.pyx"]),
    ]


if __name__ == "__main__":
    from Cython.Build import cythonize
    
    # Compiler directives
    compiler_directives = {
        "language_level": 3,
        "boundscheck": False,
        "wraparound": False,
        "initializedcheck": False,
        "cdivision": True,
        "embedsignature": True,
    }
    
    setup(
        name="astra-cortex",
        version="0.1.0",
        ext_modules=cythonize(
            get_extensions(),
            annotate=True,  # Generate .html performance reports
            compiler_directives=compiler_directives,
            nthreads=0,  # Let Cython decide (0 = single-threaded on Windows)
        ),
        zip_safe=False,
    )
