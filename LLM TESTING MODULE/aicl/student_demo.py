from core import new_msg
from transport import run_server

def handler(msg):
    act = msg.get("act")
    if act=="inform":  # capabilities from teacher
        return [new_msg("model://gpt2","model://neox","ack", payload={"ok":True})]
    if act=="ask":
        text = msg["payload"]["text"]["content"]
        summary = "Key points: " + text[:120] + "..."
        return [new_msg("model://gpt2","model://neox","answer",
                        payload={"text":{"lang":"en","fmt":"md","content":summary}},
                        ctx={"turn": msg.get("ctx",{}).get("turn",0)})]
    return []

if __name__=="__main__":
    run_server("127.0.0.1", 5556, handler)  # student listens