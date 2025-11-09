"""
Data Filtering Script

Implements de-duplication and semantic filtering using MinHash and cosine similarity.
"""

import argparse
import json
import numpy as np
from typing import List, Dict, Any, Tuple
import hashlib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.util import ngrams

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
except:
    pass

class MinHash:
    """MinHash implementation for near-duplicate detection."""
    
    def __init__(self, num_hashes: int = 128):
        """
        Initialize MinHash.
        
        Args:
            num_hashes: Number of hash functions to use
        """
        self.num_hashes = num_hashes
        # Generate random hash functions
        self.hash_functions = [
            lambda x, i=i: hash(str(x) + str(i)) for i in range(num_hashes)
        ]
    
    def compute_signature(self, shingles: set) -> List[int]:
        """
        Compute MinHash signature for a set of shingles.
        
        Args:
            shingles: Set of shingles
            
        Returns:
            MinHash signature
        """
        signature = []
        for hash_func in self.hash_functions:
            min_hash = float('inf')
            for shingle in shingles:
                hash_val = hash_func(shingle)
                if hash_val < min_hash:
                    min_hash = hash_val
            signature.append(min_hash)
        return signature
    
    def similarity(self, sig1: List[int], sig2: List[int]) -> float:
        """
        Estimate Jaccard similarity between two MinHash signatures.
        
        Args:
            sig1: First signature
            sig2: Second signature
            
        Returns:
            Estimated Jaccard similarity
        """
        if len(sig1) != len(sig2):
            raise ValueError("Signatures must have the same length")
        
        matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
        return matches / len(sig1)

def get_shingles(text: str, k: int = 5) -> set:
    """
    Get k-shingles from text.
    
    Args:
        text: Input text
        k: Shingle size
        
    Returns:
        Set of shingles
    """
    # Convert to lowercase and split into words
    words = text.lower().split()
    
    # Generate k-shingles
    shingles = set()
    for i in range(len(words) - k + 1):
        shingle = ' '.join(words[i:i+k])
        shingles.add(shingle)
    
    return shingles

def get_character_shingles(text: str, k: int = 5) -> set:
    """
    Get character-level k-shingles from text.
    
    Args:
        text: Input text
        k: Shingle size
        
    Returns:
        Set of character shingles
    """
    shingles = set()
    for i in range(len(text) - k + 1):
        shingle = text[i:i+k]
        shingles.add(shingle)
    
    return shingles

def filter_near_duplicates(dataset: List[Dict[str, Any]], 
                          text_key: str = "text",
                          threshold: float = 0.8,
                          minhash_num_hashes: int = 128) -> List[Dict[str, Any]]:
    """
    Filter near-duplicate examples using MinHash.
    
    Args:
        dataset: List of dataset examples
        text_key: Key for text in each example
        threshold: Jaccard similarity threshold for duplicates
        minhash_num_hashes: Number of hash functions for MinHash
        
    Returns:
        Filtered dataset
    """
    # Initialize MinHash
    minhash = MinHash(minhash_num_hashes)
    
    # Compute signatures for all examples
    signatures = []
    texts = []
    
    for example in dataset:
        if text_key in example:
            text = example[text_key]
            texts.append(text)
            
            # Get shingles
            shingles = get_character_shingles(text, k=5)
            
            # Compute signature
            signature = minhash.compute_signature(shingles)
            signatures.append(signature)
        else:
            signatures.append(None)
            texts.append("")
    
    # Find and remove duplicates
    filtered_dataset = []
    seen_signatures = []
    
    for i, (example, signature) in enumerate(zip(dataset, signatures)):
        if signature is None:
            # Keep examples without text
            filtered_dataset.append(example)
            continue
            
        # Check if this signature is similar to any previously seen signature
        is_duplicate = False
        for prev_signature in seen_signatures:
            similarity = minhash.similarity(signature, prev_signature)
            if similarity >= threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            filtered_dataset.append(example)
            seen_signatures.append(signature)
    
    return filtered_dataset

def filter_semantic_duplicates(dataset: List[Dict[str, Any]], 
                             text_key: str = "text",
                             threshold: float = 0.9,
                             sample_size: int = 1000) -> List[Dict[str, Any]]:
    """
    Filter semantically similar examples using TF-IDF and cosine similarity.
    
    Args:
        dataset: List of dataset examples
        text_key: Key for text in each example
        threshold: Cosine similarity threshold for duplicates
        sample_size: Number of examples to use for TF-IDF fitting (for efficiency)
        
    Returns:
        Filtered dataset
    """
    # Extract texts
    texts = [example[text_key] for example in dataset if text_key in example]
    
    if len(texts) <= 1:
        return dataset
    
    # Sample texts for TF-IDF fitting if dataset is large
    if len(texts) > sample_size:
        indices = np.random.choice(len(texts), sample_size, replace=False)
        sample_texts = [texts[i] for i in indices]
    else:
        sample_texts = texts
    
    # Fit TF-IDF vectorizer
    vectorizer = TfidfVectorizer(max_features=10000, stop_words='english')
    vectorizer.fit(sample_texts)
    
    # Transform all texts
    tfidf_matrix = vectorizer.transform(texts)
    
    # Calculate cosine similarities
    similarities = cosine_similarity(tfidf_matrix)
    
    # Find and remove semantically similar examples
    filtered_dataset = []
    seen_indices = set()
    
    for i in range(len(dataset)):
        if i in seen_indices:
            continue
            
        # Add current example to filtered dataset
        filtered_dataset.append(dataset[i])
        
        # Mark similar examples as seen
        for j in range(i+1, len(dataset)):
            if j not in seen_indices and similarities[i, j] >= threshold:
                seen_indices.add(j)
    
    return filtered_dataset

def load_dataset(dataset_path: str) -> List[Dict[str, Any]]:
    """
    Load dataset from JSON/JSONL file.
    
    Args:
        dataset_path: Path to dataset file
        
    Returns:
        Loaded dataset
    """
    with open(dataset_path, 'r') as f:
        if dataset_path.endswith('.json'):
            return json.load(f)
        elif dataset_path.endswith('.jsonl'):
            dataset = []
            for line in f:
                dataset.append(json.loads(line.strip()))
            return dataset

def save_dataset(dataset: List[Dict[str, Any]], output_path: str):
    """
    Save dataset to JSON/JSONL file.
    
    Args:
        dataset: Dataset to save
        output_path: Path to save dataset
    """
    with open(output_path, 'w') as f:
        if output_path.endswith('.json'):
            json.dump(dataset, f, indent=2)
        elif output_path.endswith('.jsonl'):
            for example in dataset:
                f.write(json.dumps(example) + '\n')

def main():
    parser = argparse.ArgumentParser(description="Filter dataset for duplicates")
    parser.add_argument("--input_dataset", type=str, required=True,
                        help="Path to input dataset")
    parser.add_argument("--output_dataset", type=str, required=True,
                        help="Path to output filtered dataset")
    parser.add_argument("--text_key", type=str, default="text",
                        help="Key for text in dataset examples")
    parser.add_argument("--near_dup_threshold", type=float, default=0.8,
                        help="MinHash similarity threshold for near-duplicates")
    parser.add_argument("--semantic_threshold", type=float, default=0.9,
                        help="Cosine similarity threshold for semantic duplicates")
    parser.add_argument("--minhash_hashes", type=int, default=128,
                        help="Number of hash functions for MinHash")
    
    args = parser.parse_args()
    
    # Load dataset
    print("Loading dataset...")
    dataset = load_dataset(args.input_dataset)
    print(f"Loaded {len(dataset)} examples")
    
    # Filter near-duplicates
    print("Filtering near-duplicates with MinHash...")
    filtered_dataset = filter_near_duplicates(
        dataset,
        args.text_key,
        args.near_dup_threshold,
        args.minhash_hashes
    )
    print(f"Near-duplicate filtering reduced dataset to {len(filtered_dataset)} examples")
    
    # Filter semantic duplicates
    print("Filtering semantic duplicates with TF-IDF...")
    final_dataset = filter_semantic_duplicates(
        filtered_dataset,
        args.text_key,
        args.semantic_threshold
    )
    print(f"Semantic filtering reduced dataset to {len(final_dataset)} examples")
    
    # Save filtered dataset
    print("Saving filtered dataset...")
    save_dataset(final_dataset, args.output_dataset)
    print(f"Saved {len(final_dataset)} filtered examples to {args.output_dataset}")

if __name__ == "__main__":
    main()