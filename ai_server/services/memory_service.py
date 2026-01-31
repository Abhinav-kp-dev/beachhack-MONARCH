"""
Memory service with AUTHORITY SEPARATION enforced

THREE SEPARATE STORES (no mixing):
1. Evidence Store (TinyDB) - Raw conversations for audit
2. State Store (TinyDB) - Customer profiles (authoritative)
3. Search Index (FAISS) - Embeddings for agent search ONLY

CRITICAL RULES:
- Search results NEVER merged into state
- LLM NEVER reads from any store
- Semantic search is display-only
"""

import faiss
import numpy as np
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from tinydb import TinyDB, Query
from models import ConversationEvidence, CustomerProfile, SearchIndexEntry
from services.embed_service import embed
import config

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Manages three separated storage systems with clear authority boundaries.
    NO cross-contamination between stores.
    """
    
    def __init__(self):
        # Evidence store (raw conversations)
        self.evidence_db = TinyDB(config.CONVERSATIONS_DB)
        
        # State store (customer profiles) - managed primarily by CustomerService
        # This is read-only from Memory Service perspective
        self.state_db = TinyDB(config.CUSTOMERS_DB)
        
        # Search index (FAISS + metadata)
        self.dim = config.EMBEDDING_DIM
        self.index_path = config.FAISS_INDEX_PATH
        self.metadata_path = config.TEXTS_STORE_PATH
        
        # Load or create FAISS index
        try:
            self.index = faiss.read_index(self.index_path)
            logger.info(f"Loaded existing FAISS index with {self.index.ntotal} vectors")
        except:
            self.index = faiss.IndexFlatL2(self.dim)
            logger.info("Created new FAISS index")
        
        # Load index metadata (maps FAISS position to conversation details)
        try:
            with open(self.metadata_path, 'r') as f:
                self.index_metadata = json.load(f)
        except:
            self.index_metadata = []
            logger.info("Created new index metadata store")
        
        logger.info(f"Initialized MemoryService: {len(self.index_metadata)} indexed conversations")
    
    def save_index(self):
        """Persist FAISS index and metadata to disk"""
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, 'w') as f:
                json.dump(self.index_metadata, f)
            logger.debug("Saved FAISS index and metadata")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    # ============================================
    # EVIDENCE STORE (Raw Conversations)
    # ============================================
    
    def add_evidence(self, customer_id: str, text: str, channel: str) -> str:
        """
        Store raw conversation as evidence.
        Purpose: Audit trail only, never read by rules or LLM.
        
        Args:
            customer_id: Customer identifier
            text: Raw conversation text
            channel: Communication channel
            
        Returns:
            Conversation ID
        """
        evidence = ConversationEvidence(
            customer_id=customer_id,
            raw_text=text,
            channel=channel
        )
        
        # Store in evidence database
        evidence_dict = evidence.model_dump()
        evidence_dict['timestamp'] = evidence.timestamp.isoformat()
        evidence_dict['created_at'] = evidence.created_at.isoformat()
        
        self.evidence_db.insert(evidence_dict)
        logger.info(f"Stored evidence: {evidence.conversation_id} for customer {customer_id}")
        
        return evidence.conversation_id
    
    def get_customer_evidence(self, customer_id: str, limit: int = 20) -> List[ConversationEvidence]:
        """
        Retrieve raw evidence conversations for display.
        Purpose: Show conversation history to agent (never used by rules).
        
        Args:
            customer_id: Customer identifier
            limit: Maximum conversations to return
            
        Returns:
            List of ConversationEvidence objects
        """
        Query_obj = Query()
        results = self.evidence_db.search(Query_obj.customer_id == customer_id)
        
        # Sort by timestamp descending
        results = sorted(results, key=lambda x: x.get('timestamp', ''), reverse=True)
        results = results[:limit]
        
        # Convert to ConversationEvidence objects
        evidence_list = []
        for result in results:
            # Parse datetime strings
            if 'timestamp' in result and isinstance(result['timestamp'], str):
                result['timestamp'] = datetime.fromisoformat(result['timestamp'])
            if 'created_at' in result and isinstance(result['created_at'], str):
                result['created_at'] = datetime.fromisoformat(result['created_at'])
            
            try:
                evidence_list.append(ConversationEvidence(**result))
            except Exception as e:
                logger.warning(f"Failed to parse evidence record: {e}")
                continue
        
        return evidence_list
    
    # ============================================
    # SEARCH INDEX (Semantic Search - Display Only)
    # ============================================
    
    def add_to_search_index(self, conversation_id: str, customer_id: str, text: str):
        """
        Add conversation to search index.
        Purpose: Enable agent-initiated semantic search.
        Constraint: Results shown separately, NEVER merged into state.
        
        Args:
            conversation_id: Conversation identifier
            customer_id: Customer identifier
            text: Text to embed and index
        """
        try:
            # Generate embedding
            embedding = embed(text)
            embedding_np = np.array([embedding], dtype=np.float32)
            
            # Add to FAISS index
            index_position = self.index.ntotal
            self.index.add(embedding_np)
            
            # Store metadata
            metadata = {
                "conversation_id": conversation_id,
                "customer_id": customer_id,
                "embedding_index": index_position,
                "timestamp": datetime.now().isoformat()
            }
            self.index_metadata.append(metadata)
            
            # Save
            self.save_index()
            
            logger.debug(f"Added conversation {conversation_id} to search index at position {index_position}")
            
        except Exception as e:
            logger.error(f"Failed to add to search index: {e}")
    
    def search_similar(self, query_text: str, customer_id: Optional[str] = None, k: int = 5, similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Enhanced semantic search with better similarity scoring and ranking.
        
        **CRITICAL**: Results are for DISPLAY ONLY. 
        They must NEVER be merged into customer state.
        UI must show them in a separate section with clear label.
        
        IMPROVEMENTS:
        - Cosine similarity scoring (0-1 range, higher is better)
        - Similarity threshold filtering
        - Temporal recency weighting
        - Better result ranking
        
        Args:
            query_text: Search query
            customer_id: Optional filter by customer
            k: Number of results
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            Dict with results and warning about display-only usage
        """
        if self.index.ntotal == 0:
            return {
                "query": query_text,
                "results": [],
                "warning": "DISPLAY ONLY - Do not merge into state",
                "total_indexed": 0
            }
        
        try:
            # Generate query embedding
            query_embedding = embed(query_text)
            query_np = np.array([query_embedding], dtype=np.float32)
            
            # Search FAISS
            distances, indices = self.index.search(query_np, min(k * 2, self.index.ntotal))
            
            # Build results with enhanced metadata and scoring
            results = []
            for idx, dist in zip(indices[0], distances[0]):
                if idx < len(self.index_metadata):
                    metadata = self.index_metadata[idx]
                    
                    # Filter by customer if specified
                    if customer_id and metadata["customer_id"] != customer_id:
                        continue
                    
                    # Convert L2 distance to cosine similarity (normalized 0-1)
                    # For L2 distance: similarity = 1 / (1 + distance)
                    # This gives values close to 1 for similar items, close to 0 for dissimilar
                    similarity = 1.0 / (1.0 + float(dist))
                    
                    # Apply similarity threshold
                    if similarity < similarity_threshold:
                        continue
                    
                    # Get evidence text
                    Query_obj = Query()
                    evidence = self.evidence_db.search(
                        Query_obj.conversation_id == metadata["conversation_id"]
                    )
                    
                    if evidence:
                        # Calculate recency score (more recent = higher score)
                        try:
                            from datetime import datetime
                            timestamp = datetime.fromisoformat(metadata["timestamp"])
                            age_days = (datetime.now() - timestamp).days
                            recency_score = 1.0 / (1.0 + age_days / 30.0)  # Decay over 30 days
                        except:
                            recency_score = 0.5
                        
                        # Combined score: 70% similarity + 30% recency
                        combined_score = (0.7 * similarity) + (0.3 * recency_score)
                        
                        results.append({
                            "conversation_id": metadata["conversation_id"],
                            "customer_id": metadata["customer_id"],
                            "text": evidence[0]["raw_text"][:500],  # Truncate long texts
                            "similarity_score": round(similarity, 3),
                            "recency_score": round(recency_score, 3),
                            "combined_score": round(combined_score, 3),
                            "timestamp": metadata["timestamp"]
                        })
            
            # Sort by combined score (descending)
            results.sort(key=lambda x: x['combined_score'], reverse=True)
            results = results[:k]  # Take top k after sorting
            
            return {
                "query": query_text,
                "results": results,
                "total_found": len(results),
                "total_indexed": self.index.ntotal,
                "similarity_threshold": similarity_threshold,
                "warning": "⚠️ DISPLAY ONLY - These results are for reference and must NOT be merged into customer state"
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "query": query_text,
                "results": [],
                "error": str(e),
                "warning": "DISPLAY ONLY"
            }
    
    # ============================================
    # COMBINED WORKFLOW
    # ============================================
    
    def store_conversation(self, customer_id: str, text: str, channel: str) -> str:
        """
        Complete storage workflow:
        1. Store as evidence (audit)
        2. Add to search index (agent search)
        
        Note: Does NOT update customer state - that's CustomerService responsibility.
        
        Args:
            customer_id: Customer identifier
            text: Raw conversation text
            channel: Communication channel
            
        Returns:
            Conversation ID
        """
        # 1. Store evidence
        conversation_id = self.add_evidence(customer_id, text, channel)
        
        # 2. Add to search index
        self.add_to_search_index(conversation_id, customer_id, text)
        
        return conversation_id
    
    def get_customer_context(self, customer_id: str, include_search: bool = False) -> Dict[str, Any]:
        """
        Retrieve customer context with CLEAR SEPARATION.
        
        Returns:
            - state: Authoritative customer profile
            - evidence: Raw conversations
            - search_results: Optional, clearly separated
        """
        # Get authoritative state (read-only)
        Query_obj = Query()
        state_results = self.state_db.search(Query_obj.customer_id == customer_id)
        customer_state = state_results[0] if state_results else None
        
        # Get evidence
        evidence = self.get_customer_evidence(customer_id)
        
        # Optional: Get semantic search results (if agent requests)
        search_results = None
        if include_search and customer_state:
            # Search using customer's preferences as query
            query = " ".join(customer_state.get("preferences", []))
            if query:
                search_results = self.search_similar(query, customer_id=customer_id, k=5)
        
        return {
            "customer_state": customer_state,
            "evidence": evidence,
            "search_results": search_results  # Clearly separated, optional
        }


# Singleton instance
_memory_service = None

def get_memory_service() -> MemoryService:
    """Get or create singleton instance of MemoryService"""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
