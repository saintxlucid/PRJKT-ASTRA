import argparse, os, sys, subprocess

def main():
    ap = argparse.ArgumentParser(description="Wrapper to convert HF model to GGUF via llama.cpp tooling.")
    ap.add_argument("--hf_model_path", required=True, help="Path/name of HF model (e.g., models/gpt2-distilled-merged)")
    ap.add_argument("--out_dir", required=True, help="Output dir for GGUF")
    ap.add_argument("--convert_script", default="convert-hf-to-gguf.py", help="Path to llama.cpp's convert-hf-to-gguf.py")
    ap.add_argument("--quant", default=None, choices=[None,"Q8_0","Q6_K","Q5_K_M","Q4_K_M"], help="Optional quantization type")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    cmd = [sys.executable, args.convert_script, "--outtype", "f16", "--model", args.hf_model_path, "--outfile", os.path.join(args.out_dir, "model-f16.gguf")]
    print("[to_gguf] running:", " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        sys.exit(rc)
    if args.quant:
        # example quant call; user must adjust to their llama.cpp build
        qfile = os.path.join(args.out_dir, f"model-{args.quant}.gguf")
        cmdq = ["./quantize", os.path.join(args.out_dir, "model-f16.gguf"), qfile, args.quant]
        print("[to_gguf] quantizing:", " ".join(cmdq))
        rc = subprocess.call(cmdq)
        if rc != 0:
            sys.exit(rc)
    print("[to_gguf] done.")

if __name__ == "__main__":
    main()