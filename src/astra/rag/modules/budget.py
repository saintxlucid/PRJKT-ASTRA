import time

class Budget:
    """
    Tracks latency budget for a query and provides remaining time in ms.
    """
    def __init__(self, ms: int):
        self.ms = ms
        self.t0 = time.perf_counter()
    def left(self) -> int:
        return max(0, self.ms - int(1000 * (time.perf_counter() - self.t0)))
    def expired(self) -> bool:
        return self.left() <= 0
