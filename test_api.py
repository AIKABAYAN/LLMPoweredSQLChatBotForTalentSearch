"""
Test script for the FastAPI service with candidate summaries
"""
import requests
import json

def test_api_service():
    """Test the FastAPI service endpoints"""
    base_url = "http://localhost:7777"
    
    # Test 1: Root endpoint
    print("=== Testing root endpoint ===")
    try:
        response = requests.get(f"{base_url}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print()
    except Exception as e:
        print(f"Error testing root endpoint: {e}")
        print()
    
    # Test 2: Health check
    print("=== Testing health check endpoint ===")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    except Exception as e:
        print(f"Error testing health endpoint: {e}")
        print()
    
    # Test 3: Search endpoint with "15 sdm python"
    print("=== Testing search endpoint with '15 sdm python' ===")
    try:
        search_data = {
            "query": "15 sdm python",
            "session_id": "test_api_user_python"
        }
        
        response = requests.post(
            f"{base_url}/search",
            json=search_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Query: {result['query']}")
            print(f"Total found: {result['total_found']}")
            print(f"Search time: {result['search_time_seconds']:.2f}s")
            print(f"Message: {result['message']}")
            print("\n--- Candidate Summary ---")
            print(result['summary'])
            
            # Show detailed candidate information
            print("\n--- Detailed Candidate Information ---")
            for i, candidate in enumerate(result['candidates'][:3]):  # Show first 3
                print(f"\nCandidate {i+1}:")
                print(f"  Name: {candidate['name']}")
                print(f"  Experience: {candidate['experience_years']} years")
                print(f"  Score: {candidate['score']:.2f}")
                print(f"  Primary Skills: {', '.join(candidate['primary_skills'][:10])}")
                if candidate['role']:
                    print(f"  Role: {candidate['role']}")
        else:
            print(f"Error: {response.text}")
        print()
    except Exception as e:
        print(f"Error testing search endpoint: {e}")
        print()
    
    # Test 4: Search endpoint with different query
    print("=== Testing search endpoint with '3 sdm java python' ===")
    try:
        search_data = {
            "query": "3 sdm java python",
            "session_id": "test_api_user_java_python"
        }
        
        response = requests.post(
            f"{base_url}/search",
            json=search_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Query: {result['query']}")
            print(f"Total found: {result['total_found']}")
            print(f"Search time: {result['search_time_seconds']:.2f}s")
            print(f"Message: {result['message']}")
            print("\n--- Candidate Summary ---")
            print(result['summary'])
        else:
            print(f"Error: {response.text}")
        print()
    except Exception as e:
        print(f"Error testing search endpoint: {e}")
        print()

if __name__ == "__main__":
    test_api_service()
