#!/usr/bin/env python3
"""
CLI tool for validating evolved models against gates.
"""
import argparse
from pathlib import Path
from astra_evo.validate import run_validation, gates_decision, score_ppl

def main():
    parser = argparse.ArgumentParser(description="Validate evolved model against gates")
    parser.add_argument("--base", required=True, help="Path to base model")
    parser.add_argument("--out", required=True, help="Path to evolved model")
    parser.add_argument("--eval-dir", required=True, help="Path to eval dataset directory") 
    parser.add_argument("--canary", action="store_true", help="Exit 10 if canary is forced")
    args = parser.parse_args()

    res = run_validation(args.base, args.out, args.eval_dir)
    base_ppl = score_ppl(Path(args.base), Path(args.eval_dir) / "text_tiny.txt")
    decision = gates_decision(base_ppl, res)

    print(f"PPL: {res.ppl:.3f} (Δ {decision['pplDelta']:.1%})")
    print(f"Tool Accuracy: {res.toolAcc:.1%}")
    print(f"Model Drift: {res.drift:.1%}") 
    print(f"Guardrail Score: {res.guardrail:.1%}")
    print("\nGate Results:")
    print(f"  {'BLOCKED' if decision['block'] else 'PASSED'}")
    if decision['forceCanary']:
        print("  FORCE CANARY")
        if args.canary:
            exit(10)

    exit(1 if decision['block'] else 0)

if __name__ == "__main__":
    main()