"""
Setup script for GPT-2 Knowledge Distillation package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="gpt2-distillation",
    version="1.0.0",
    author="AI Research Team",
    author_email="research@example.com",
    description="A comprehensive toolkit for knowledge distillation from GPT-NeoX 20B to GPT-2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/gpt2-distillation",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "gpt2-distill=scripts.train_gpt2_distilled:main",
            "gpt2-generate-dataset=scripts.generate_neox_outputs:main",
            "gpt2-evaluate=scripts.evaluate_models:main",
            "gpt2-perplexity=scripts.calculate_perplexity:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
    },
)