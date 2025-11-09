"""Command line interface for GGUF model surgery."""

import click
import json
from pathlib import Path
from typing import Optional

from evolution.gguf.surgeon import ModelSurgeon
from evolution.gguf.manifest import AdapterManifest

@click.group()
def cli():
    """GGUF model surgery tools."""
    pass

@cli.command()
@click.option("--base", required=True, help="Base model path")
@click.option("--manifest", required=True, help="Adapter manifest path")
@click.option("--out", required=True, help="Output path")
@click.option("--quant", default="Q5_K_M", help="Quantization target")
def merge(base: str, manifest: str, out: str, quant: str):
    """Merge LoRA adapters into base model."""
    surgeon = ModelSurgeon()
    adapter_manifest = AdapterManifest(manifest)
    
    click.echo(f"Loading base model: {base}")
    click.echo(f"Using manifest: {manifest}")
    
    # Preview merge
    ops = {
        "lora_paths": [
            cfg.path for cfg in adapter_manifest.get_merge_order().values()
        ],
        "quantize": quant
    }
    
    preview = surgeon.preview(base, ops)
    click.echo(
        f"Will modify {preview.changed_tensors} tensors "
        f"({preview.bytes_delta_mb:.1f}MB delta)"
    )
    
    if not click.confirm("Proceed with merge?"):
        return
        
    # Perform merge and sign
    surgeon.embed_provenance(out, ops)
    click.echo(f"Merged model saved to: {out}")

@cli.command()
@click.option("--base", required=True, help="Base model path")
@click.option("--out", required=True, help="Output model path") 
@click.option("--dataset", required=True, help="Evaluation dataset path")
def validate(base: str, out: str, dataset: str):
    """Validate a model against evaluation datasets."""
    surgeon = ModelSurgeon()
    
    click.echo(f"Validating: {out}")
    click.echo(f"Against base: {base}")
    click.echo(f"Using dataset: {dataset}")
    
    metrics = surgeon.validate(out, dataset)
    
    click.echo("\nValidation Results:")
    click.echo(f"Tool Accuracy: {metrics.acc:.1%}")
    click.echo(f"PPL Delta: {metrics.ppl:.2f}")
    click.echo(f"Embedding Drift: {metrics.drift:.1%}")
    click.echo(f"Safety Score: {metrics.guardrail:.1%}")
    
    if metrics.passes_gates():
        click.echo("\n✅ All validation gates passed")
    else:
        click.echo("\n❌ Failed validation gates")

@cli.command()
@click.option("--out", required=True, help="Model to commit")
@click.option("--require-gates/--no-gates", default=True,
              help="Require passing validation gates")
def commit(out: str, require_gates: bool):
    """Commit model changes to disk."""
    surgeon = ModelSurgeon()
    
    click.echo(f"Committing: {out}")
    if require_gates:
        click.echo("Validation gates will be enforced")
    
    try:
        surgeon.commit(out, require_gates)
        click.echo("✅ Changes committed successfully")
    except Exception as e:
        click.echo(f"❌ Commit failed: {e}")

if __name__ == "__main__":
    cli()