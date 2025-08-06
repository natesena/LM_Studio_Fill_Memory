#!/usr/bin/env python3
"""
Neo4j Memory Verification Script using Bolt Protocol

This script helps verify what memories are actually stored in Neo4j
using the same Bolt protocol that Graphiti uses.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from neo4j import AsyncGraphDatabase

class Neo4jBoltVerifier:
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 username: str = "neo4j", password: str = "demodemo"):
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = None
        
    def log(self, message: str):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    async def connect(self):
        """Connect to Neo4j using Bolt protocol"""
        if self.driver is None:
            self.driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
        
    async def close(self):
        """Close the Neo4j connection"""
        if self.driver:
            await self.driver.close()
            self.driver = None
            
    async def execute_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute a Cypher query against Neo4j"""
        await self.connect()
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query, **kwargs)
                records = await result.data()
                return {"success": True, "data": records}
        except Exception as e:
            self.log(f"Neo4j query error: {e}")
            return {"success": False, "error": str(e)}
            
    async def test_neo4j_connection(self) -> bool:
        """Test if Neo4j is accessible"""
        self.log("=== Testing Neo4j Bolt Connection ===")
        try:
            await self.connect()
            result = await self.execute_query("RETURN 1 as test")
            if result["success"]:
                self.log("✅ Neo4j Bolt connection successful")
                return True
            else:
                self.log(f"❌ Neo4j Bolt connection failed: {result['error']}")
                return False
        except Exception as e:
            self.log(f"Neo4j connection failed: {e}")
            return False
            
    async def get_all_nodes(self) -> Dict[str, Any]:
        """Get all nodes in the database"""
        self.log("=== Getting All Nodes ===")
        query = "MATCH (n) RETURN n LIMIT 100"
        return await self.execute_query(query)
        
    async def get_memory_nodes(self) -> Dict[str, Any]:
        """Get all memory-related nodes"""
        self.log("=== Getting Memory Nodes ===")
        query = """
        MATCH (n)
        WHERE n.name IS NOT NULL OR n.episode_body IS NOT NULL
        RETURN n
        LIMIT 50
        """
        return await self.execute_query(query)
        
    async def get_recent_nodes(self, hours: int = 24) -> Dict[str, Any]:
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
        return await self.execute_query(query)
        
    async def get_node_count(self) -> Dict[str, Any]:
        """Get total node count"""
        self.log("=== Getting Node Count ===")
        query = "MATCH (n) RETURN count(n) as total_nodes"
        return await self.execute_query(query)
        
    async def search_for_specific_memory(self, search_term: str) -> Dict[str, Any]:
        """Search for a specific memory by name"""
        self.log(f"=== Searching for Memory: {search_term} ===")
        query = """
        MATCH (n)
        WHERE n.name CONTAINS $search_term
        RETURN n
        LIMIT 20
        """
        return await self.execute_query(query, search_term=search_term)
        
    async def search_by_filename(self, filename: str) -> Dict[str, Any]:
        """Search for memories by filename (more specific search)"""
        self.log(f"=== Searching for Memory by filename: {filename} ===")
        query = """
        MATCH (n)
        WHERE n.name CONTAINS $filename
        RETURN n
        LIMIT 20
        """
        return await self.execute_query(query, filename=filename)
        
    async def run_full_verification(self, search_terms: List[str] = None):
        """Run a full verification of Neo4j contents"""
        self.log("=== STARTING NEO4J BOLT VERIFICATION ===")
        
        # Test connection
        if not await self.test_neo4j_connection():
            return
            
        # Get node count
        count_result = await self.get_node_count()
        if count_result["success"]:
            total_nodes = count_result["data"][0]["total_nodes"] if count_result["data"] else 0
            self.log(f"Total nodes in database: {total_nodes}")
        else:
            self.log(f"Failed to get node count: {count_result['error']}")
            
        # Get memory nodes
        memory_result = await self.get_memory_nodes()
        if memory_result["success"]:
            memory_count = len(memory_result["data"])
            self.log(f"Memory nodes found: {memory_count}")
            
            if memory_count > 0:
                self.log("Sample memory nodes:")
                for i, record in enumerate(memory_result["data"][:5]):
                    node = record["n"]
                    name = node.get("name", "NO_NAME")
                    self.log(f"  {i+1}. {name}")
        else:
            self.log(f"Failed to get memory nodes: {memory_result['error']}")
            
        # Get recent nodes
        recent_result = await self.get_recent_nodes(hours=24)
        if recent_result["success"]:
            recent_count = len(recent_result["data"])
            self.log(f"Recent nodes (last 24h): {recent_count}")
            
            if recent_count > 0:
                self.log("Recent memory nodes:")
                for i, record in enumerate(recent_result["data"][:5]):
                    node = record["n"]
                    name = node.get("name", "NO_NAME")
                    created_at = node.get("created_at", "NO_DATE")
                    self.log(f"  {i+1}. {name} (created: {created_at})")
        else:
            self.log(f"Failed to get recent nodes: {recent_result['error']}")
            
        # Search for specific terms if provided
        if search_terms:
            self.log("=== Searching for specific terms ===")
            for term in search_terms:
                search_result = await self.search_for_specific_memory(term)
                if search_result["success"]:
                    found_count = len(search_result["data"])
                    self.log(f"Found {found_count} nodes containing '{term}'")
                else:
                    self.log(f"Search failed for '{term}': {search_result['error']}")

async def main():
    """Main function to test the Bolt verifier"""
    verifier = Neo4jBoltVerifier()
    try:
        await verifier.run_full_verification()
    finally:
        await verifier.close()

if __name__ == "__main__":
    asyncio.run(main()) 