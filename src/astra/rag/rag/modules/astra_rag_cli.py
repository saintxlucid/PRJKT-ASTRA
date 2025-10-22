"""
ASTRA RAG CLI: unified interface for planner, citations, and tracing.
"""
import argparse
import json

from planner import answer


def main():
    ap = argparse.ArgumentParser(description='ASTRA Multi-RAG v2.0 CLI')
    ap.add_argument('--q', required=True, help='Query')
    ap.add_argument('--k', type=int, default=12, help='Top-k results')
    ap.add_argument('--policy', default='hrm', help='Planner policy (hrm|fast_only|slow_only)')
    ap.add_argument('--json', action='store_true', help='JSON output')
    args = ap.parse_args()
    
    res = answer(args.q, k=args.k, policy=args.policy)
    
    if args.json:
        print(json.dumps(res, indent=2, default=str))
    else:
        print(f"Avg Score: {res['avg_score']:.3f}")
        print(f"Policy: {res['policy']}")
        print(f"Confidence: {res['reflection'].get('confidence', 0):.3f}\n")
        
        print("CONTEXTS:")
        for i, c in enumerate(res['contexts'], 1):
            print(f"\n[{i}] {c.get('category', '')} score={c['score']:.3f}")
            print(f"    {c.get('uri', '')} → chunk {c.get('chunk_id', '')}")
            print(f"    {c['text'][:200]}...\n")
        
        print("\nCITATIONS:")
        for cite in res['citations']:
            print(f"  - {cite['uri']}#{cite['chunk_id']} ({cite['category']})")


if __name__ == '__main__':
    main()
