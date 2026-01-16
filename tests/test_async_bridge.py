import asyncio
import threading
import unittest


class TestAsyncBridge(unittest.TestCase):
    def test_thread_to_async_callback(self):
        """
        Verifies that a function running in a thread can synchronously call
        an async function running in the main loop using run_coroutine_threadsafe.
        """

        loop = asyncio.new_event_loop()

        async def async_target(val):
            await asyncio.sleep(0.01)
            return val * 2

        def sync_wrapper(val):
            future = asyncio.run_coroutine_threadsafe(async_target(val), loop)
            return future.result()

        def threaded_worker():
            # This simulates ToolExecutor.execute
            return sync_wrapper(10)

        def main_async_runner():
            asyncio.set_event_loop(loop)
            # This simulates GeminiWorker.run_async calling executor
            val = loop.run_until_complete(asyncio.to_thread(threaded_worker))
            return val

        # Run the loop in a separate thread to strictly mimic GeminiWorkerThread if needed,
        # but here we can just run the runner in this thread if we are careful.
        # However, to be safe and avoid blocking the test runner if something hangs:

        result = None

        def target():
            nonlocal result
            result = main_async_runner()

        t = threading.Thread(target=target)
        t.start()
        t.join(timeout=2)

        self.assertFalse(t.is_alive(), "Thread timed out")
        self.assertEqual(result, 20)
        loop.close()


if __name__ == "__main__":
    unittest.main()
