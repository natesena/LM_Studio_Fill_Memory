#!/usr/bin/env python3
"""
Test Neo4j connection with different credentials
"""

import requests
import json

def test_neo4j_connection():
    """Test Neo4j connection with different credentials"""
    
    neo4j_url = "http://localhost:7474"
    
    # Test different credential combinations
    credentials_to_test = [
        ("neo4j", "demodemo"),
        ("neo4j", "password"),
        ("neo4j", "neo4j"),
        (None, None),  # No credentials
    ]
    
    for username, password in credentials_to_test:
        print(f"\n🔍 Testing credentials: username='{username}', password='{password}'")
        
        try:
            # Test basic connection
            response = requests.get(f"{neo4j_url}/browser/", timeout=5)
            print(f"  Browser response: {response.status_code}")
            
            # Test REST API
            auth = None
            if username and password:
                auth = (username, password)
            
            response = requests.get(f"{neo4j_url}/db/data/", auth=auth, timeout=5)
            print(f"  REST API response: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✅ SUCCESS with credentials: {username}/{password}")
                return username, password
            else:
                print(f"  ❌ Failed with credentials: {username}/{password}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n❌ No working credentials found")
    return None, None

if __name__ == "__main__":
    test_neo4j_connection() 