import argparse, yaml, subprocess, sys

def run(cmd):
    print("[RUN]", " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        sys.exit(rc)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["A","B","C"], required=True)
    args = ap.parse_args()
    cfg_map = {"A":"configs/run_phaseA.yaml", "B":"configs/run_phaseB.yaml", "C":"configs/run_phaseC.yaml"}
    cfg = cfg_map[args.phase]
    # default: plain python; user can swap to accelerate/deepspeed
    run(["python", "scripts/train_gpt2_distilled.py", "--config", cfg])

if __name__ == "__main__":
    main()