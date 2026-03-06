import sys
import os
# Append the current directory to sys.path to import analyze
sys.path.append(os.getcwd())

import analyze
import time

def test_inference():
    print("Starting inference test...")
    tweets = [
        "The train was very clean and the staff was polite.",
        "The washroom was dirty and the train was late.",
        "The security was good but the delay was frustrating.",
        "TC was rude but the train arrived on time.",
    ]
    
    start_time = time.time()
    try:
        results = analyze.run_protege_inference("Test Dataset", tweets)
        end_time = time.time()
        
        print(f"Results: {results}")
        print(f"Time taken: {end_time - start_time:.2f} seconds")
        
        # Basic validation
        assert "dataset" in results
        assert "analysis" in results
        print("✅ Test passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_inference()
