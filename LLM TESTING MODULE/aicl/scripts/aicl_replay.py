import argparse
import json
import os

def main():
    parser = argparse.ArgumentParser(description="Replay AICL conversation logs")
    parser.add_argument("--log", required=True, help="Path to conversation log JSONL file")
    args = parser.parse_args()
    
    if not os.path.exists(args.log):
        print(f"Log file not found: {args.log}")
        return
    
    print(f"Replaying conversation from: {args.log}")
    
    with open(args.log, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                msg = json.loads(line)
                print(f"[{line_num}] {msg.get('act', 'unknown')} from {msg.get('from', 'unknown')} to {msg.get('to', 'unknown')}")
                if "payload" in msg:
                    payload = msg["payload"]
                    if "text" in payload:
                        content = payload["text"].get("content", "")[:100]
                        print(f"  Text: {content}{'...' if len(content) == 100 else ''}")
                    elif "logits" in payload:
                        print(f"  Logits: {len(payload['logits'].get('topk', []))} entries")
                    elif "tool" in payload:
                        print(f"  Tool: {payload['tool'].get('name', 'unknown')}")
            except json.JSONDecodeError:
                print(f"[{line_num}] Invalid JSON line")
            except Exception as e:
                print(f"[{line_num}] Error: {e}")

if __name__ == "__main__":
    main()