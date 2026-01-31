import sys
import pytest

def main():
    """
    Run performance benchmarks using pytest.
    """
    print("Running benchmarks...")
    # Run pytest on the benchmark test file
    args = ["tests/test_benchmark_preview.py"] + sys.argv[1:]
    sys.exit(pytest.main(args))

if __name__ == "__main__":
    main()
