import time
import threading
import sys
import os

# Add src to PYTHONPATH
sys.path.append(os.path.abspath("src"))

from gemini_agent.utils.helpers import RateLimiter

def test_rate_limiter_threads():
    # max 10 requests per 1 second -> refill every 0.1s
    rl = RateLimiter(max_requests=10, period=1.0, auto_refill=True)
    
    initial_threads = threading.active_count()
    print(f"Initial threads: {initial_threads}")
    
    # Wait for some refills
    time.sleep(0.5)
    
    current_threads = threading.active_count()
    print(f"Threads after 0.5s: {current_threads}")
    
    # If it creates a new thread for every refill, we should see many threads
    # But wait, threading.Timer starts a thread that finishes.
    # However, if they overlap or if we check at the right time...
    
    # Let's check if the number of threads grows over time if we don't stop it.
    # Actually, Timer threads finish. But it's still a lot of overhead.
    
    rl.acquire()
    print("Acquired 1")
    
    time.sleep(1.1)
    print(f"Final threads: {threading.active_count()}")

if __name__ == "__main__":
    test_rate_limiter_threads()
