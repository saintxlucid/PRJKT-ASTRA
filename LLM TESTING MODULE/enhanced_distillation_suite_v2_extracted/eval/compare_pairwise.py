import argparse, json, random

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher_outputs", required=False, help="JSONL with {prompt, output}")
    ap.add_argument("--student_outputs", required=False, help="JSONL with {prompt, output}")
    args = ap.parse_args()
    print("[Compare] Placeholder script. Implement pairwise preference or metric comparison here.")

if __name__ == "__main__":
    main()