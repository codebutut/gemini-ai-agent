import sys
import os

# Add src directory to sys.path
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

from gemini_agent.main import main

if __name__ == "__main__":
    main()
