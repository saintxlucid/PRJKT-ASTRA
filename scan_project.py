#!/usr/bin/env python3
"""
ASTRA Project Scanner - Complete codebase analysis tool
"""
import os
import sys
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime
import re
from typing import Dict, List, Optional
import ast

class ProjectScanner:
    def __init__(self, root_path: str, output_path: str = "scan_report.json"):
        self.root = Path(root_path).resolve()
        self.output_path = Path(output_path)
        self.ignore_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'build', 'dist'}
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'root_path': str(self.root),
            'files': [],
            'summary': {
                'total_files': 0,
                'total_code_files': 0,
                'total_lines': 0,
                'languages': {},
                'file_types': {}
            }
        }

    def scan_python_file(self, content: str) -> Dict:
        """Extract Python code structure using AST"""
        info = {
            'functions': [],
            'classes': [],
            'imports': [],
            'todos': [],
            'docstring': None
        }
        try:
            tree = ast.parse(content)
            info['docstring'] = ast.get_docstring(tree)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'lineno': node.lineno,
                        'docstring': ast.get_docstring(node),
                        'args': [a.arg for a in node.args.args if hasattr(a, 'arg')]
                    }
                    info['functions'].append(func_info)
                elif isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'lineno': node.lineno,
                        'docstring': ast.get_docstring(node),
                        'methods': []
                    }
                    for subnode in node.body:
                        if isinstance(subnode, ast.FunctionDef):
                            method_info = {
                                'name': subnode.name,
                                'lineno': subnode.lineno,
                                'docstring': ast.get_docstring(subnode),
                                'args': [a.arg for a in subnode.args.args if hasattr(a, 'arg')]
                            }
                            class_info['methods'].append(method_info)
                    info['classes'].append(class_info)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            info['imports'].append(name.name)
                    else:
                        module = node.module or ''
                        for name in node.names:
                            info['imports'].append(f"{module}.{name.name}")
        except SyntaxError as e:
            info['error'] = f"Syntax error: {str(e)}"
        except Exception as e:
            info['error'] = f"Error parsing Python file: {str(e)}"
        
        # Find TODOs
        todos = re.findall(r'#\s*TODO\s*:?\s*(.*)', content)
        info['todos'].extend(todos)
        
        return info

    def scan_text_file(self, content: str) -> Dict:
        """Analyze text/markdown files"""
        info = {
            'line_count': content.count('\n') + 1,
            'todos': re.findall(r'(?:^|\n)\s*[-*]\s*\[ \]\s*(.*)', content),  # Markdown task items
            'headers': re.findall(r'^#+\s+(.+)$', content, re.MULTILINE),
            'has_code_blocks': bool(re.search(r'```\w*\n.*?```', content, re.DOTALL))
        }
        return info

    def compute_file_hash(self, path: Path) -> str:
        """Compute SHA-256 hash of file contents"""
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def is_binary(self, path: Path) -> bool:
        """Check if file is binary"""
        try:
            with open(path, 'tr') as check:
                check.read()
                return False
        except:
            return True

    def scan_file(self, path: Path) -> Dict:
        """Scan individual file and extract information"""
        rel_path = path.relative_to(self.root).as_posix()
        info = {
            'path': rel_path,
            'size': path.stat().st_size,
            'last_modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            'extension': path.suffix.lower(),
            'hash': self.compute_file_hash(path)
        }
        
        # Skip binary files
        if self.is_binary(path):
            info['type'] = 'binary'
            return info
            
        # Read file content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            info['error'] = f"Error reading file: {str(e)}"
            return info
            
        info['line_count'] = content.count('\n') + 1
        
        # Analyze based on file type
        if path.suffix == '.py':
            info['type'] = 'python'
            info['analysis'] = self.scan_python_file(content)
        elif path.suffix in {'.md', '.txt'}:
            info['type'] = 'text'
            info['analysis'] = self.scan_text_file(content)
        else:
            info['type'] = 'other'
            info['analysis'] = {
                'line_count': info['line_count'],
                'todos': re.findall(r'(?://|#)\s*TODO\s*:?\s*(.*)', content)
            }
            
        return info

    def scan_directory(self):
        """Scan entire project directory"""
        for path in self.root.rglob('*'):
            if not path.is_file():
                continue
            
            # Skip ignored directories
            if any(ignore in path.parts for ignore in self.ignore_dirs):
                continue
                
            try:
                file_info = self.scan_file(path)
                self.results['files'].append(file_info)
                
                # Update summary
                self.results['summary']['total_files'] += 1
                ext = file_info.get('extension', '')
                self.results['summary']['file_types'][ext] = self.results['summary']['file_types'].get(ext, 0) + 1
                
                if file_info.get('type') in {'python', 'text', 'other'}:
                    self.results['summary']['total_code_files'] += 1
                    self.results['summary']['total_lines'] += file_info.get('line_count', 0)
                    
                if file_info.get('type') == 'python':
                    self.results['summary']['languages']['python'] = self.results['summary']['languages'].get('python', 0) + 1
                    
            except Exception as e:
                print(f"Error scanning {path}: {str(e)}", file=sys.stderr)

    def generate_report(self):
        """Generate comprehensive JSON report"""
        self.scan_directory()
        
        # Sort files by path for consistency
        self.results['files'].sort(key=lambda x: x['path'])
        
        # Write report
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)
        
        # Also generate markdown summary
        md_path = self.output_path.with_suffix('.md')
        self.generate_markdown_summary(md_path)
        
        return self.results
        
    def generate_markdown_summary(self, output_path: Path):
        """Generate human-readable markdown summary"""
        md_lines = [
            f"# ASTRA Project Scan Report\n",
            f"Generated: {self.results['timestamp']}\n",
            f"## Summary\n",
            f"- Total Files: {self.results['summary']['total_files']}",
            f"- Code Files: {self.results['summary']['total_code_files']}",
            f"- Total Lines: {self.results['summary']['total_lines']}\n",
            "## File Types\n"
        ]
        
        # File types table
        md_lines.extend([
            "| Extension | Count |",
            "|-----------|-------|"
        ])
        for ext, count in sorted(self.results['summary']['file_types'].items()):
            md_lines.append(f"| {ext or '(no extension)'} | {count} |")
            
        # Python specific stats
        python_files = [f for f in self.results['files'] if f.get('type') == 'python']
        if python_files:
            md_lines.extend([
                "\n## Python Analysis\n",
                f"Total Python Files: {len(python_files)}\n",
                "### Classes\n"
            ])
            
            for file in python_files:
                classes = file.get('analysis', {}).get('classes', [])
                if classes:
                    md_lines.append(f"\n**File: {file['path']}**\n")
                    for cls in classes:
                        md_lines.append(f"- {cls['name']}")
                        if cls['methods']:
                            for method in cls['methods']:
                                md_lines.append(f"  - {method['name']}")
                                
        # Write markdown
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md_lines))

def main():
    """CLI entry point"""
    import argparse
    parser = argparse.ArgumentParser(description='ASTRA Project Scanner')
    parser.add_argument('--path', '-p', default='.', help='Project root path')
    parser.add_argument('--output', '-o', default='scan_report.json', help='Output report path')
    args = parser.parse_args()
    
    scanner = ProjectScanner(args.path, args.output)
    scanner.generate_report()
    print(f"Scan complete. Reports written to:")
    print(f"- JSON: {args.output}")
    print(f"- Markdown: {Path(args.output).with_suffix('.md')}")

if __name__ == '__main__':
    main()