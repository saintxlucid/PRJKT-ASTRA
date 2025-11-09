#!/usr/bin/env python3
"""
Resource Collection Script for ASTRA PRIME Development

This script helps collect and organize essential resources for mastering
the domains needed for advanced LLM reverse engineering and enhancement.
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import Dict, List

class ResourceCollector:
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.resources_dir = self.base_path / "collected_resources"
        self.resources_dir.mkdir(exist_ok=True)
        
        # Define resource categories
        self.resource_categories = {
            "gguf_internals": {
                "name": "GGUF/GGML Internals",
                "description": "Resources for understanding GGUF binary format and internals",
                "sources": [
                    "https://github.com/ggerganov/llama.cpp/blob/master/docs/gguf.md",
                    "https://github.com/ggerganov/llama.cpp/tree/master/gguf-py",
                    "https://github.com/ggerganov/llama.cpp/tree/master/examples",
                ],
                "local_files": [
                    "../astra-local/backend/bin/llama.cpp/gguf-py/gguf/gguf_reader.py",
                    "../astra-local/backend/bin/llama.cpp/gguf-py/gguf/gguf_writer.py",
                    "../astra-local/backend/bin/llama.cpp/gguf-py/gguf/constants.py"
                ]
            },
            "transformers_internals": {
                "name": "Transformers Internals",
                "description": "Resources for understanding transformer model internals",
                "sources": [
                    "https://arxiv.org/abs/1706.03762",  # Attention Is All You Need
                    "https://arxiv.org/abs/2302.13971",  # LLaMA paper
                    "https://github.com/huggingface/transformers",
                ],
                "local_files": [
                    "../astra-local/backend/bin/llama.cpp/examples/main.cpp",
                    "../astra-local/backend/bin/llama.cpp/convert_hf_to_gguf.py"
                ]
            },
            "lora_adapters": {
                "name": "LoRA and Adapters",
                "description": "Resources for understanding LoRA and adapter mechanisms",
                "sources": [
                    "https://arxiv.org/abs/2106.09685",  # LoRA paper
                    "https://github.com/huggingface/peft",
                    "https://huggingface.co/docs/peft/en/index",
                ],
                "local_files": []
            },
            "cpp_backends": {
                "name": "C++ Backends",
                "description": "Resources for understanding C++ backend internals",
                "sources": [
                    "https://github.com/ggerganov/llama.cpp",
                    "https://github.com/ggerganov/llama.cpp/tree/master/examples",
                    "https://github.com/ggerganov/llama.cpp/blob/master/README.md",
                ],
                "local_files": [
                    "../astra-local/backend/bin/llama.cpp/src/llama.cpp",
                    "../astra-local/backend/bin/llama.cpp/src/llama.h",
                    "../astra-local/backend/bin/llama.cpp/ggml/src/ggml.c",
                ]
            },
            "memory_quantization": {
                "name": "Memory Layout and Quantization",
                "description": "Resources for understanding memory and quantization",
                "sources": [
                    "https://github.com/ggerganov/llama.cpp/blob/master/ggml.md",
                    "https://github.com/ggerganov/llama.cpp/tree/master/ggml",
                ],
                "local_files": [
                    "../astra-local/backend/bin/llama.cpp/ggml/include/ggml.h",
                    "../astra-local/backend/bin/llama.cpp/ggml/src/ggml.c",
                ]
            },
            "layer_surgery": {
                "name": "Layer Surgery and Merging",
                "description": "Resources for model surgery and safe merging",
                "sources": [
                    "https://arxiv.org/abs/2305.08677",  # Model merging techniques
                    "https://github.com/huggingface/transformers",
                ],
                "local_files": []
            }
        }
    
    def create_resource_structure(self):
        """Create directory structure for organizing resources"""
        print("Creating resource directory structure...")
        
        for category_key, category_info in self.resource_categories.items():
            category_dir = self.resources_dir / category_key
            category_dir.mkdir(exist_ok=True)
            
            # Create subdirectories
            (category_dir / "papers").mkdir(exist_ok=True)
            (category_dir / "code").mkdir(exist_ok=True)
            (category_dir / "documentation").mkdir(exist_ok=True)
            (category_dir / "tutorials").mkdir(exist_ok=True)
            
            print(f"  Created structure for {category_info['name']}")
    
    def collect_local_resources(self):
        """Copy local resources to organized structure"""
        print("Collecting local resources...")
        
        for category_key, category_info in self.resource_categories.items():
            code_dir = self.resources_dir / category_key / "code"
            
            for local_file in category_info["local_files"]:
                if os.path.exists(local_file):
                    try:
                        # Copy file to resources directory
                        filename = os.path.basename(local_file)
                        destination = code_dir / filename
                        
                        with open(local_file, 'r', encoding='utf-8') as src:
                            content = src.read()
                        
                        with open(destination, 'w', encoding='utf-8') as dst:
                            dst.write(content)
                        
                        print(f"  Copied {local_file} to {destination}")
                    except Exception as e:
                        print(f"  Error copying {local_file}: {e}")
                else:
                    print(f"  Local file not found: {local_file}")
    
    def generate_resource_list(self):
        """Generate a comprehensive resource list"""
        print("Generating resource list...")
        
        resource_list = {
            "generated_at": "2025-10-10",
            "categories": {}
        }
        
        for category_key, category_info in self.resource_categories.items():
            resource_list["categories"][category_key] = {
                "name": category_info["name"],
                "description": category_info["description"],
                "online_sources": category_info["sources"],
                "local_files": category_info["local_files"],
                "collected_files": []
            }
            
            # List collected files
            category_dir = self.resources_dir / category_key
            if category_dir.exists():
                for subdir in category_dir.iterdir():
                    if subdir.is_dir():
                        for file in subdir.iterdir():
                            if file.is_file():
                                relative_path = file.relative_to(self.resources_dir)
                                resource_list["categories"][category_key]["collected_files"].append(str(relative_path))
        
        # Save resource list
        resource_list_path = self.resources_dir / "resource_list.json"
        with open(resource_list_path, 'w', encoding='utf-8') as f:
            json.dump(resource_list, f, indent=2)
        
        print(f"Resource list saved to {resource_list_path}")
        return resource_list
    
    def create_study_plan(self):
        """Create a structured study plan document"""
        print("Creating study plan...")
        
        study_plan_content = """# ASTRA PRIME RESOURCE COLLECTION STUDY PLAN

## Week 1-2: GGUF/GGML Internals
- [ ] Read GGUF specification documentation
- [ ] Study binary format structure
- [ ] Analyze local GGUF reader/writer code
- [ ] Practice with hex editors on sample GGUF files

## Week 3-4: Transformers Internals
- [ ] Read "Attention Is All You Need" paper
- [ ] Study LLaMA architecture paper
- [ ] Analyze HuggingFace transformer implementations
- [ ] Trace data flow through model layers

## Week 5-6: LoRA and Adapters
- [ ] Read LoRA paper
- [ ] Study HuggingFace PEFT library
- [ ] Implement basic LoRA adaptation
- [ ] Analyze gradient flow patterns

## Week 7-8: C++ Backend Mastery
- [ ] Study llama.cpp source code
- [ ] Compile and run modified versions
- [ ] Analyze kernel execution mechanisms
- [ ] Implement custom layers

## Week 9-10: Memory and Quantization
- [ ] Study GGML quantization formats
- [ ] Analyze memory layout optimization
- [ ] Implement custom quantization schemes
- [ ] Optimize tensor operations

## Week 11-12: Layer Surgery and Merging
- [ ] Study model merging techniques
- [ ] Practice layer extraction/replacement
- [ ] Implement safe merging algorithms
- [ ] Create validation frameworks

## Ongoing Activities
- [ ] Weekly code review and practice
- [ ] Monthly progress assessment
- [ ] Community engagement and learning
- [ ] Documentation and knowledge sharing
"""
        
        study_plan_path = self.resources_dir / "STUDY_PLAN.md"
        with open(study_plan_path, 'w', encoding='utf-8') as f:
            f.write(study_plan_content)
        
        print(f"Study plan saved to {study_plan_path}")
    
    def run_collection(self):
        """Run the complete resource collection process"""
        print("Starting ASTRA PRIME resource collection...")
        print("=" * 50)
        
        # Create directory structure
        self.create_resource_structure()
        
        # Collect local resources
        self.collect_local_resources()
        
        # Generate resource list
        resource_list = self.generate_resource_list()
        
        # Create study plan
        self.create_study_plan()
        
        print("=" * 50)
        print("Resource collection complete!")
        print(f"Resources organized in: {self.resources_dir}")
        print("Next steps:")
        print("1. Review the STUDY_PLAN.md")
        print("2. Examine the collected resources")
        print("3. Begin working through the study plan")
        print("4. Update resource_list.json as you collect more materials")

def main():
    collector = ResourceCollector()
    collector.run_collection()

if __name__ == "__main__":
    main()