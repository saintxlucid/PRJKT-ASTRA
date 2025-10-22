import time
import threading
from collections import OrderedDict

class LRUCache:
    def __init__(self, maxsize=128, ttl=600):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache = OrderedDict()
        self.lock = threading.Lock()
    def _expire(self):
        now = time.time()
        keys = [k for k, (_, t) in self.cache.items() if now - t > self.ttl]
        for k in keys:
            self.cache.pop(k, None)
    def get(self, key):
        with self.lock:
            self._expire()
            if key in self.cache:
                v, t = self.cache.pop(key)
                self.cache[key] = (v, t)
                return v
            return None
    def set(self, key, value):
        with self.lock:
            self._expire()
            if key in self.cache:
                self.cache.pop(key)
            self.cache[key] = (value, time.time())
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)

# Global caches for query, ANN, rerank, embedding
query_cache = LRUCache(maxsize=256, ttl=1800)
ann_cache = LRUCache(maxsize=128, ttl=600)
rerank_cache = LRUCache(maxsize=256, ttl=3600)
embed_cache = LRUCache(maxsize=512, ttl=1800)
