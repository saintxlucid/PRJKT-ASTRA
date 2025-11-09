import argparse, os, json, uuid, glob, pathlib
from typing import List
from .extract import extract_text
from .clean import normalize
from .chunk import token_chunks

def gather_files(src: str) -> List[str]:
    paths = []
    if os.path.isdir(src):
        for root, _, files in os.walk(src):
            for f in files:
                if f.lower().endswith(('.txt','.md','.markdown','.html','.htm','.pdf','.docx')):
                    paths.append(os.path.join(root, f))
    else:
        paths = glob.glob(src)
    return sorted(paths)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Directory or glob of documents")
    ap.add_argument("--out_jsonl", required=True, help="Output JSONL with {doc_id, chunk_id, source_path, prompt}")
    ap.add_argument("--student_tokenizer", default="gpt2", help="Tokenizer to size chunks")
    ap.add_argument("--max_tokens", type=int, default=512)
    ap.add_argument("--overlap", type=int, default=32)
    ap.add_argument("--prompt_template", default="You are a helpful assistant. Read the following context and answer questions.\n\n{context}\n\nQuestion: Summarize the key points.", help="Template to turn chunk into a prompt")
    args = ap.parse_args()

    files = gather_files(args.src)
    os.makedirs(os.path.dirname(args.out_jsonl), exist_ok=True)
    n_rows = 0
    with open(args.out_jsonl, "w", encoding="utf-8") as fout:
        for p in files:
            doc_id = str(uuid.uuid4())[:8]
            text = extract_text(p)
            for ch in token_chunks(text, model_name=args.student_tokenizer, max_tokens=args.max_tokens, overlap=args.overlap):
                prompt = args.prompt_template.format(context=ch["text"])
                row = {
                    "doc_id": doc_id,
                    "chunk_id": ch["chunk_id"],
                    "source_path": os.path.relpath(p),
                    "prompt": prompt,
                    # place-holder for teacher outputs; to be filled by your generator
                    "neox_output": ""
                }
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                n_rows += 1
    print(f"[ingest] wrote {n_rows} rows to {args.out_jsonl} from {len(files)} source files.")

if __name__ == "__main__":
    main()