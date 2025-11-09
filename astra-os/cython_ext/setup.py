import sys

from setuptools import Extension, setup

try:
    from Cython.Build import cythonize
except ImportError as e:
    raise RuntimeError("Cython is required to build extensions: pip install cython") from e

try:
    import numpy as np
except ImportError as e:
    raise RuntimeError("numpy is required to build extensions: pip install numpy") from e


def _openmp_flags() -> dict[str, list[str]]:
    if sys.platform.startswith("win"):
        # MSVC
        return {"extra_compile_args": ["/O2", "/openmp"], "extra_link_args": []}
    # GCC/Clang
    return {"extra_compile_args": ["-O3", "-march=native", "-fopenmp"], "extra_link_args": ["-fopenmp"]}


omp = _openmp_flags()

extensions = [
    Extension(
        name="astra_cykernels.kernels",
        sources=["astra_cykernels/kernels.pyx"],
        include_dirs=[np.get_include()],
        language="c",
        extra_compile_args=omp["extra_compile_args"],
        extra_link_args=omp["extra_link_args"],
    ),
]

setup(
    name="astra_cykernels",
    version="0.0.1",
    description="ASTRA optional Cython kernels",
    packages=["astra_cykernels"],
    ext_modules=cythonize(extensions, compiler_directives={
        "language_level": 3,
        "boundscheck": False,
        "wraparound": False,
        "cdivision": True,
        "nonecheck": False,
        "initializedcheck": False,
    }),
    zip_safe=False,
)
