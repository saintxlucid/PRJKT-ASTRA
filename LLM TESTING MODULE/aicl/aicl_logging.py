import json
import os
import gzip
from datetime import datetime
from typing import Dict, Optional, List
import hashlib

class AICLLogger:
    """Advanced logger for AICL conversations with metrics tracking"""
    
    def __init__(self, log_dir: str = "artifacts/conversations", compress: bool = True):
        self.log_dir = log_dir
        self.compress = compress
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = timestamp
        
        # Create log files
        log_filename = f"conversation_{timestamp}.jsonl"
        if compress:
            log_filename += ".gz"
        self.log_file = os.path.join(log_dir, log_filename)
        
        self.last_log = os.path.join(log_dir, "last.jsonl")
        if compress:
            self.last_log += ".gz"
            
        # Metrics tracking
        self.metrics = {
            "total_messages": 0,
            "total_tokens": 0,
            "avg_latency_ms": 0,
            "message_types": {},
            "participants": set()
        }
        
    def log_message(self, msg: Dict, latency_ms: Optional[float] = None):
        """Append a message to the conversation log"""
        # Update metrics
        self.metrics["total_messages"] += 1
        self.metrics["participants"].add(msg.get("from", "unknown"))
        self.metrics["participants"].add(msg.get("to", "unknown"))
        
        # Track message types
        msg_type = msg.get("act", "unknown")
        self.metrics["message_types"][msg_type] = self.metrics["message_types"].get(msg_type, 0) + 1
        
        # Track tokens if available
        if "limits" in msg and "tokens" in msg["limits"]:
            self.metrics["total_tokens"] += msg["limits"]["tokens"]
            
        # Track latency
        if latency_ms is not None:
            current_avg = self.metrics["avg_latency_ms"]
            total = self.metrics["total_messages"]
            self.metrics["avg_latency_ms"] = ((current_avg * (total - 1)) + latency_ms) / total
        
        # Write to log file
        if self.compress:
            with gzip.open(self.log_file, "at", encoding="utf-8") as f:
                f.write(json.dumps(msg, separators=(",", ":")) + "\n")
        else:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg, separators=(",", ":")) + "\n")
                
        # Also update the "last" symlink/file
        if self.compress:
            with gzip.open(self.last_log, "at", encoding="utf-8") as f:
                f.write(json.dumps(msg, separators=(",", ":")) + "\n")
        else:
            with open(self.last_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg, separators=(",", ":")) + "\n")
            
    def get_log_path(self) -> str:
        """Get the path to the current log file"""
        return self.log_file
        
    def get_metrics(self) -> Dict:
        """Get conversation metrics"""
        metrics = self.metrics.copy()
        metrics["participants"] = list(metrics["participants"])
        return metrics
        
    def get_run_id(self) -> str:
        """Get the current run ID"""
        return self.run_id
        
    def save_metrics(self):
        """Save metrics to a file"""
        metrics_file = os.path.join(self.log_dir, f"metrics_{self.run_id}.json")
        with open(metrics_file, "w") as f:
            json.dump(self.get_metrics(), f, indent=2)
            
    def calculate_log_hash(self) -> str:
        """Calculate SHA256 hash of the log file"""
        hash_sha256 = hashlib.sha256()
        
        if self.compress:
            with gzip.open(self.log_file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
        else:
            with open(self.log_file, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
                    
        return hash_sha256.hexdigest()

class AICLReplayer:
    """Replay AICL conversation logs"""
    
    @staticmethod
    def load_log(log_path: str) -> List[Dict]:
        """Load messages from a log file"""
        messages = []
        
        if log_path.endswith(".gz"):
            with gzip.open(log_path, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON line in {log_path}")
        else:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON line in {log_path}")
                        
        return messages
        
    @staticmethod
    def print_summary(messages: List[Dict]):
        """Print a summary of the conversation"""
        if not messages:
            print("No messages in log")
            return
            
        print(f"Conversation Summary ({len(messages)} messages):")
        print("-" * 50)
        
        participants = set()
        msg_types = {}
        
        for msg in messages:
            participants.add(msg.get("from", "unknown"))
            participants.add(msg.get("to", "unknown"))
            
            msg_type = msg.get("act", "unknown")
            msg_types[msg_type] = msg_types.get(msg_type, 0) + 1
            
        print(f"Participants: {', '.join(participants)}")
        print(f"Message Types: {msg_types}")
        
        # Show first few messages
        print("\nFirst 3 messages:")
        for i, msg in enumerate(messages[:3]):
            print(f"  {i+1}. {msg.get('act', 'unknown')} from {msg.get('from', 'unknown')} to {msg.get('to', 'unknown')}")
            
        if len(messages) > 3:
            print(f"  ... and {len(messages) - 3} more messages")