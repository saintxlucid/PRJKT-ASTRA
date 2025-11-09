from core import new_msg
from transport import run_server
from time import time

def handler(msg):
    # Expect ack to our hello or student answers
    if msg.get("act")=="ack":
        # kick off a request
        ask = new_msg("model://neox","model://gpt2","ask",
                      payload={"text":{"lang":"en","fmt":"md","content":"Summarize: Transformers are..."}},
                      ctx={"turn":1}, limits={"tokens":128})
        return [ask]
    elif msg.get("act")=="answer":
        print("[teacher] student:", msg["payload"]["text"]["content"])
    return []

if __name__=="__main__":
    # Send hello via synthetic inbound trigger
    def bootstrap(_): 
        hello = new_msg("model://neox","model://gpt2","inform",
                        payload={"caps":["text","logits:topk"],"max_ctx":4096})
        return [hello]
    run_server("127.0.0.1", 5555, lambda m: handler(m) if m else bootstrap(m))