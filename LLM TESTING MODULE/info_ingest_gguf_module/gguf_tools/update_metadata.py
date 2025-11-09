import argparse, json, os, sys, hashlib

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Attach/update GGUF metadata fields.")
    ap.add_argument("--in_gguf", required=True, help="Path to input .gguf")
    ap.add_argument("--out_gguf", required=True, help="Path to output .gguf (new file)")
    ap.add_argument("--set", action="append", default=[], help='Set key=value (e.g., training.dataset_name=myset)')
    ap.add_argument("--dataset_jsonl", default=None, help="Optional: reference dataset jsonl to hash and include stats")
    args = ap.parse_args()

    # lazy import 'gguf' (installed with llama.cpp python tools)
    try:
        import gguf
    except Exception as e:
        print("ERROR: This tool requires the 'gguf' python package from llama.cpp. Install it first.", file=sys.stderr)
        sys.exit(2)

    reader = gguf.GGUFReader(args.in_gguf)
    # Create writer copying tensors and kvs
    writer = gguf.GGUFWriter(args.out_gguf, reader.arch, reader.tensor_infos[0].name if reader.tensor_infos else "model")
    # copy existing kv data
    for key in reader.kv_data.keys():
        for v in reader.kv_data[key]:
            writer.add_kv(key, v)
    # copy all tensors
    for ti in reader.tensor_infos:
        data = reader.get_tensor_data(ti)
        writer.add_tensor(ti.name, data, ti.shape, ti.dtype)

    # apply sets
    for pair in args.__dict__.get("set", []):
        if "=" not in pair:
            print(f"Skip invalid --set '{pair}' (expected key=value)", file=sys.stderr)
            continue
        k, v = pair.split("=", 1)
        writer.add_kv(k, v)

    # dataset stats (hash + count)
    if args.dataset_jsonl and os.path.exists(args.dataset_jsonl):
        total = 0
        with open(args.dataset_jsonl, "r", encoding="utf-8") as f:
            for _ in f:
                total += 1
        writer.add_kv("training.dataset_path", os.path.basename(args.dataset_jsonl))
        writer.add_kv("training.dataset_sha256", sha256_file(args.dataset_jsonl))
        writer.add_kv("training.dataset_rows", str(total))

    # finalize
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()
    print(f"[gguf] wrote updated GGUF -> {args.out_gguf}")

if __name__ == "__main__":
    main()