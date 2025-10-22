"""
Retrieve: thin CLI wrapper over retrieval core + fusion.
"""
import argparse

from retrieval_core import retrieve_multi
from fusion import fuse
from optimizers import enforce_diversity


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--q', required=True, help='Query')
    ap.add_argument('--cats', nargs='*', default=None, help='Specific categories')
    ap.add_argument('--backend', default=None, help='Vector store backend')
    ap.add_argument('--k', type=int, default=12, help='Top-k results')
    args = ap.parse_args()
    
    per_cat = retrieve_multi(args.q, categories=args.cats, backend=args.backend)
    fused = fuse(args.q, per_cat)
    fused = enforce_diversity(fused, cap_ratio=0.6)[:args.k]
    
    print(f"Query: {args.q}\nResults: {len(fused)}\n")
    
    for i, h in enumerate(fused, 1):
        print(f"[{i}] {h.get('category', '')} score={h['score']:.3f} {h.get('uri', '')}")
        print(f"{h['text'][:300]}\n---\n")


if __name__ == '__main__':
    main()
