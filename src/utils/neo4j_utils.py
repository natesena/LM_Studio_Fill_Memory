#!/usr/bin/env python3
"""
Neo4j Memory Verification Script

This script helps verify what memories are actually stored in Neo4j
and can help diagnose issues with memory storage.
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, List

class Neo4jVerifier:
    def __init__(self, neo4j_url: str = "http://localhost:7474", 
                 username: str = "neo4j", password: str = "password"):
        self.neo4j_url = neo4j_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        
    def log(self, message: str):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def test_neo4j_connection(self) -> bool:
        """Test if Neo4j is accessible"""
        self.log("=== Testing Neo4j Connection ===")
        try:
            # Try to access Neo4j browser
            response = self.session.get(f"{self.neo4j_url}/browser/", timeout=5)
            self.log(f"Neo4j browser response: {response.status_code}")
            
            # Try to access Neo4j REST API
            response = self.session.get(f"{self.neo4j_url}/db/data/", timeout=5)
            self.log(f"Neo4j REST API response: {response.status_code}")
            
            return response.status_code == 200
            
        except Exception as e:
            self.log(f"Neo4j connection failed: {e}")
            return False
            
    def query_neo4j(self, query: str) -> Dict[str, Any]:
        """Execute a Cypher query against Neo4j"""
        try:
            url = f"{self.neo4j_url}/db/data/transaction/commit"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            payload = {
                "statements": [{"statement": query}]
            }
            
            # Use basic auth if credentials provided
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
                
            response = self.session.post(url, json=payload, headers=headers, auth=auth, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"Neo4j query failed with status {response.status_code}: {response.text}")
                return {"error": f"Query failed: {response.status_code}"}
                
        except Exception as e:
            self.log(f"Neo4j query error: {e}")
            return {"error": str(e)}
            
    def get_all_nodes(self) -> Dict[str, Any]:
        """Get all nodes in the database"""
        self.log("=== Getting All Nodes ===")
        query = "MATCH (n) RETURN n LIMIT 100"
        return self.query_neo4j(query)
        
    def get_memory_nodes(self) -> Dict[str, Any]:
        """Get all memory-related nodes"""
        self.log("=== Getting Memory Nodes ===")
        query = """
        MATCH (n)
        WHERE n.name CONTAINS 'memory' OR n.name CONTAINS 'test' OR n.episode_body IS NOT NULL
        RETURN n
        LIMIT 50
        """
        return self.query_neo4j(query)
        
    def get_recent_nodes(self, hours: int = 24) -> Dict[str, Any]:
        """Get nodes created in the last N hours"""
        self.log(f"=== Getting Recent Nodes (last {hours} hours) ===")
        query = f"""
        MATCH (n)
        WHERE n.created_at IS NOT NULL
        AND datetime(n.created_at) > datetime() - duration({{hours: {hours}}})
        RETURN n
        ORDER BY n.created_at DESC
        LIMIT 50
        """
        return self.query_neo4j(query)
        
    def get_node_count(self) -> Dict[str, Any]:
        """Get total node count"""
        self.log("=== Getting Node Count ===")
        query = "MATCH (n) RETURN count(n) as total_nodes"
        return self.query_neo4j(query)
        
    def get_relationship_count(self) -> Dict[str, Any]:
        """Get total relationship count"""
        self.log("=== Getting Relationship Count ===")
        query = "MATCH ()-[r]->() RETURN count(r) as total_relationships"
        return self.query_neo4j(query)
        
    def search_for_specific_memory(self, search_term: str) -> Dict[str, Any]:
        """Search for a specific memory by name or content"""
        self.log(f"=== Searching for Memory: {search_term} ===")
        query = f"""
        MATCH (n)
        WHERE n.name CONTAINS '{search_term}' OR n.episode_body CONTAINS '{search_term}'
        RETURN n
        LIMIT 20
        """
        return self.query_neo4j(query)
        
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        self.log("=== Getting Database Info ===")
        queries = [
            "CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition",
            "CALL dbms.database.version() YIELD version RETURN version",
            "SHOW DATABASES YIELD name, current, role, address, requestedStatus, currentStatus"
        ]
        
        results = {}
        for i, query in enumerate(queries):
            try:
                result = self.query_neo4j(query)
                results[f"query_{i}"] = result
            except Exception as e:
                results[f"query_{i}"] = {"error": str(e)}
                
        return results
        
    def run_full_verification(self, search_terms: List[str] = None):
        """Run a full verification of Neo4j contents"""
        self.log("=== STARTING NEO4J VERIFICATION ===")
        
        # Test connection
        if not self.test_neo4j_connection():
            self.log("Neo4j not accessible - stopping verification")
            return
            
        # Get database info
        db_info = self.get_database_info()
        self.log(f"Database info: {json.dumps(db_info, indent=2)}")
        
        # Get counts
        node_count = self.get_node_count()
        self.log(f"Node count: {json.dumps(node_count, indent=2)}")
        
        relationship_count = self.get_relationship_count()
        self.log(f"Relationship count: {json.dumps(relationship_count, indent=2)}")
        
        # Get all nodes (limited)
        all_nodes = self.get_all_nodes()
        self.log(f"All nodes (first 100): {json.dumps(all_nodes, indent=2)}")
        
        # Get memory nodes
        memory_nodes = self.get_memory_nodes()
        self.log(f"Memory nodes: {json.dumps(memory_nodes, indent=2)}")
        
        # Get recent nodes
        recent_nodes = self.get_recent_nodes()
        self.log(f"Recent nodes: {json.dumps(recent_nodes, indent=2)}")
        
        # Search for specific terms
        if search_terms:
            for term in search_terms:
                search_result = self.search_for_specific_memory(term)
                self.log(f"Search for '{term}': {json.dumps(search_result, indent=2)}")
        
        self.log("=== NEO4J VERIFICATION COMPLETE ===")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify Neo4j memory storage")
    parser.add_argument('--neo4j-url', default="http://localhost:7474", 
                       help="Neo4j URL")
    parser.add_argument('--username', default="neo4j", 
                       help="Neo4j username")
    parser.add_argument('--password', default="password", 
                       help="Neo4j password")
    parser.add_argument('--search-terms', nargs='+', 
                       default=["test", "memory", "lifecycle"],
                       help="Terms to search for in memory nodes")
    
    args = parser.parse_args()
    
    verifier = Neo4jVerifier(
        neo4j_url=args.neo4j_url,
        username=args.username,
        password=args.password
    )
    
    verifier.run_full_verification(args.search_terms)

if __name__ == "__main__":
    main() 