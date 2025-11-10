#!/usr/bin/env python3
"""
ASTRA TUI — Minimal, Ready-to-Run Terminal UI
Handles token issuing, health checks, chat history, and slash-commands.

Works with local endpoints:
  - SigilGate (token):  http://localhost:7701/issue
  - ASTRA API (chat):   http://localhost:8000/v1/chat

Optional env overrides:
  ASTRA_CHAT_URL, ASTRA_ISSUE_URL, ASTRA_IDENTITY
"""

import os
import json
import time
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests

try:
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import InMemoryHistory
except ImportError:
    print("❌ Missing dependencies. Install with: pip install requests prompt_toolkit")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

CHAT_URL = os.getenv("ASTRA_CHAT_URL", "http://localhost:8000/v1/chat")
ISSUE_URL = os.getenv("ASTRA_ISSUE_URL", "http://localhost:7701/issue")
IDENTITY = os.getenv("ASTRA_IDENTITY", "saint")
SCOPES = ["*"]
TTL_SECS = 3600

DEFAULT_TEMP = float(os.getenv("ASTRA_TEMP", "0.3"))
DEFAULT_MAX_TOKENS = int(os.getenv("ASTRA_MAX_TOKENS", "768"))

BANNER = """\
────────────────────────────────────────────────────────────────
🟢 ASTRA 3.0 — ASCENSION  |  Local TUI  |  Sacred Code: 333 → ∞
────────────────────────────────────────────────────────────────
Commands: /help  /health  /clear  /save  /model  /temp  /maxtok  /exit
────────────────────────────────────────────────────────────────
"""

HELP = """\
Commands:
  /help           Show this help
  /health         Ping health endpoints + token status
  /clear          Clear chat context (local only)
  /save [file]    Save transcript to JSON (default: transcript_<ts>.json)
  /model [name]   Annotate desired model for routing (metadata)
  /temp [0-2]     Set temperature for completions (default: 0.3)
  /maxtok [int]   Set max_tokens for completions (default: 768)
  /exit           Quit TUI

Examples:
  /temp 0.7       → more creative
  /maxtok 2048    → longer responses
  /save chat.json → save history
"""

COMMANDS = [
    "/help", "/health", "/clear", "/save", "/model", "/temp", "/maxtok", "/exit"
]

# ═══════════════════════════════════════════════════════════════════════════════
# CLIENT
# ═══════════════════════════════════════════════════════════════════════════════


class AstraClient:
    """ASTRA API client with auto token refresh."""

    def __init__(self):
        self.token: Optional[str] = None
        self.token_expiry: Optional[float] = None
        self.session = requests.Session()
        self.model_hint = "gpt-oss-20b"
        self.temperature = DEFAULT_TEMP
        self.max_tokens = DEFAULT_MAX_TOKENS

    def ensure_token(self):
        """Issue or refresh token if needed."""
        if not self.token or (self.token_expiry and time.time() > self.token_expiry - 30):
            self.issue_token()

    def issue_token(self):
        """Request token from SigilGate."""
        payload = {"identity": IDENTITY, "scopes": SCOPES, "ttl": TTL_SECS}
        r = self.session.post(ISSUE_URL, json=payload, timeout=10)
        if r.status_code != 200:
            raise RuntimeError(f"Token issue failed: {r.status_code} {r.text[:200]}")
        data = r.json()
        self.token = data.get("token") or data.get("jwt") or data.get("access_token")
        self.token_expiry = time.time() + TTL_SECS
        print(f"🔑 token issued for '{IDENTITY}' (ttl≈{TTL_SECS}s)")

    def health(self) -> Dict[str, Any]:
        """Probe both endpoints for health."""
        out = {"chat": None, "sigil_gate": None}
        try:
            health_url = CHAT_URL.replace("/v1/chat", "/v1/system/health")
            rc = self.session.get(health_url, timeout=5)
            out["chat"] = {
                "ok": rc.status_code == 200,
                "status": rc.status_code,
                "body": rc.text[:200],
            }
        except Exception as e:
            out["chat"] = {"ok": False, "error": str(e)}

        try:
            health_url = ISSUE_URL.replace("/issue", "/health")
            rs = self.session.get(health_url, timeout=5)
            out["sigil_gate"] = {
                "ok": rs.status_code == 200,
                "status": rs.status_code,
                "body": rs.text[:200],
            }
        except Exception as e:
            out["sigil_gate"] = {"ok": False, "error": str(e)}
        return out

    def chat(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send chat request."""
        self.ensure_token()
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "meta": {"desired_model": self.model_hint},
        }
        r = self.session.post(CHAT_URL, headers=headers, json=payload, timeout=60)

        # 401 → refresh token and retry once
        if r.status_code == 401:
            self.issue_token()
            headers["Authorization"] = f"Bearer {self.token}"
            r = self.session.post(CHAT_URL, headers=headers, json=payload, timeout=60)

        if r.status_code != 200:
            raise RuntimeError(f"Chat error {r.status_code}: {r.text[:500]}")
        return r.json()


# ═══════════════════════════════════════════════════════════════════════════════
# TUI LOOP
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Run ASTRA TUI."""
    print(BANNER)
    client = AstraClient()
    history = InMemoryHistory()
    completer = WordCompleter(COMMANDS, ignore_case=True)

    # Local conversation state
    messages: List[Dict[str, Any]] = []
    transcript: List[Dict[str, Any]] = []

    # Try token early
    try:
        client.ensure_token()
    except Exception as e:
        print(f"⚠️  Could not issue token yet: {e}")
        print("    (type /health to debug, or try again)\n")

    while True:
        try:
            user = prompt(
                HTML("<b><ansimagenta>you</ansimagenta></b> ▸ "),
                completer=completer,
                history=history,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 bye.")
            break

        if not user:
            continue

        # ═══════════════════════════════════════════════════════════════════════
        # SLASH COMMANDS
        # ═══════════════════════════════════════════════════════════════════════

        if user.startswith("/"):
            parts = user.split()
            cmd = parts[0].lower()

            if cmd == "/help":
                print(HELP)
                continue

            if cmd == "/health":
                h = client.health()
                print("🔎 Health Status:")
                print(
                    "  chat-api:   ",
                    "✅ OK" if h["chat"].get("ok") else "❌ DOWN",
                )
                if not h["chat"].get("ok"):
                    print(f"    {h['chat'].get('error') or h['chat'].get('body')}")
                print(
                    "  sigil-gate: ",
                    "✅ OK" if h["sigil_gate"].get("ok") else "❌ DOWN",
                )
                if not h["sigil_gate"].get("ok"):
                    print(
                        f"    {h['sigil_gate'].get('error') or h['sigil_gate'].get('body')}"
                    )
                if client.token_expiry:
                    exp = datetime.fromtimestamp(client.token_expiry).isoformat()
                    print(f"  token_expiry: {exp}")
                print()
                continue

            if cmd == "/clear":
                messages.clear()
                print("🧹 Context cleared (local only).\n")
                continue

            if cmd == "/save":
                fname = (
                    parts[1]
                    if len(parts) > 1
                    else f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump(transcript, f, ensure_ascii=False, indent=2)
                print(f"💾 Saved → {fname}\n")
                continue

            if cmd == "/model":
                if len(parts) == 1:
                    print(f"Model hint: {client.model_hint}\n")
                else:
                    client.model_hint = " ".join(parts[1:])
                    print(f"Model hint → {client.model_hint}\n")
                continue

            if cmd == "/temp":
                if len(parts) == 1:
                    print(f"Temperature: {client.temperature}\n")
                else:
                    try:
                        val = float(parts[1])
                        if 0.0 <= val <= 2.0:
                            client.temperature = val
                            print(f"Temperature → {client.temperature}\n")
                        else:
                            print("Enter value between 0.0 and 2.0\n")
                    except ValueError:
                        print("Usage: /temp 0.7\n")
                continue

            if cmd == "/maxtok":
                if len(parts) == 1:
                    print(f"Max tokens: {client.max_tokens}\n")
                else:
                    try:
                        val = int(parts[1])
                        if val > 0:
                            client.max_tokens = val
                            print(f"Max tokens → {client.max_tokens}\n")
                        else:
                            print("Enter a positive integer\n")
                    except ValueError:
                        print("Usage: /maxtok 1024\n")
                continue

            if cmd == "/exit":
                print("👋 bye.")
                break

            print("❓ Unknown command. Type /help\n")
            continue

        # ═══════════════════════════════════════════════════════════════════════
        # NORMAL CHAT
        # ═══════════════════════════════════════════════════════════════════════

        messages.append({"role": "user", "content": user})
        t0 = time.time()

        try:
            resp = client.chat(messages)
        except Exception as e:
            print(f"❌ Request failed: {e}\n")
            transcript.append(
                {
                    "ts": datetime.now().isoformat(),
                    "you": user,
                    "error": str(e),
                }
            )
            continue

        # Extract response (handle multiple payload formats)
        assistant_text = (
            resp.get("response")
            or resp.get("message")
            or resp.get("choices", [{}])[0].get("message", {}).get("content")
            or resp.get("content")
            or "<no content>"
        )

        usage = resp.get("usage", {})
        model = resp.get("model", client.model_hint)

        messages.append({"role": "assistant", "content": assistant_text})
        dt = time.time() - t0

        # Display response
        print("\n<b><ansicyan>astra</ansicyan></b> ▸")
        print(assistant_text.strip())
        print(f"\n⏱️  {dt:.2f}s   🧠 {model}   🔢 {usage}\n")

        # Record in transcript
        transcript.append(
            {
                "ts": datetime.now().isoformat(),
                "you": user,
                "astra": assistant_text,
                "model": model,
                "usage": usage,
                "latency_s": round(dt, 3),
                "temp": client.temperature,
                "max_tokens": client.max_tokens,
            }
        )


if __name__ == "__main__":
    main()
