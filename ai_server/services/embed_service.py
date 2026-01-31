"""
Enhanced embedding service with optimization and batch processing
Uses sentence-transformers for semantic embeddings
"""

import os
import numpy as np
import logging
from typing import List, Union

logger = logging.getLogger(__name__)

# Set environment variables before importing transformers
os.environ.setdefault('HF_HUB_OFFLINE', '0')

try:
    from sentence_transformers import SentenceTransformer
    # Load model with optimization
    model = SentenceTransformer("all-MiniLM-L6-v2", device='cpu')
    model.max_seq_length = 512  # Optimize for longer texts
    logger.info("✅ Embedding model loaded successfully (all-MiniLM-L6-v2)")
except Exception as e:
    logger.warning(f"⚠️ Could not load embedding model: {e}")
    logger.warning("ℹ️ Vector search will be disabled, but core features will work")
    model = None


def embed(text: str) -> np.ndarray:
    """
    Generate embedding for a single text.
    
    Args:
        text: Input text to embed
        
    Returns:
        384-dimensional embedding vector
    """
    if model is None:
        # Return dummy embedding if model not loaded
        logger.warning("Embedding model not available, returning zero vector")
        return np.zeros(384, dtype=np.float32)
    
    try:
        # Normalize and truncate text
        text = text.strip()
        if not text:
            return np.zeros(384, dtype=np.float32)
        
        # Generate embedding
        embedding = model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return embedding.astype(np.float32)
    
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return np.zeros(384, dtype=np.float32)


def embed_batch(texts: List[str], batch_size: int = 32) -> np.ndarray:
    """
    Generate embeddings for multiple texts (optimized batch processing).
    
    Args:
        texts: List of texts to embed
        batch_size: Batch size for processing
        
    Returns:
        Array of embeddings (n_texts, 384)
    """
    if model is None:
        logger.warning("Embedding model not available, returning zero vectors")
        return np.zeros((len(texts), 384), dtype=np.float32)
    
    try:
        # Normalize texts
        texts = [text.strip() if text else "" for text in texts]
        
        # Generate embeddings in batches
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True  # L2 normalization for better cosine similarity
        )
        
        return embeddings.astype(np.float32)
    
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {e}")
        return np.zeros((len(texts), 384), dtype=np.float32)


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings produced by the model."""
    return 384
