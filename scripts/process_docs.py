#!/usr/bin/env python3
"""
Simple document processor for Uplifted Mascot ingestion.
Processes markdown files, chunks them, and creates embeddings.
"""

import os
import re
from pathlib import Path
from typing import List, Dict
import json

def read_markdown_file(file_path: str) -> str:
    """Read a markdown file and return its content."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def chunk_text(text: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into chunks with overlap.
    
    Args:
        text: The text to chunk
        max_chunk_size: Maximum characters per chunk
        overlap: Characters to overlap between chunks
    
    Returns:
        List of text chunks
    """
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Split by paragraphs first (double newlines)
    paragraphs = text.split('\n\n')
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        para_size = len(para)
        
        # If single paragraph is too large, split by sentences
        if para_size > max_chunk_size:
            # Flush current chunk if exists
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            # Split large paragraph by sentences
            sentences = re.split(r'[.!?]+\s+', para)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                if current_size + len(sentence) > max_chunk_size:
                    if current_chunk:
                        chunks.append('\n\n'.join(current_chunk))
                    current_chunk = [sentence]
                    current_size = len(sentence)
                else:
                    current_chunk.append(sentence)
                    current_size += len(sentence) + 2  # +2 for '\n\n'
        else:
            # Check if adding this paragraph would exceed limit
            if current_size + para_size > max_chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    overlap_text = '\n\n'.join(current_chunk[-1:])
                    current_chunk = [overlap_text, para]
                    current_size = len(overlap_text) + para_size + 2
                else:
                    current_chunk = [para]
                    current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size + 2
    
    # Add final chunk
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks

def extract_metadata(file_path: str, chunk_index: int, total_chunks: int) -> Dict:
    """Extract metadata for a chunk."""
    rel_path = os.path.relpath(file_path)
    filename = os.path.basename(file_path)
    
    return {
        "file_path": rel_path,
        "filename": filename,
        "chunk_index": chunk_index,
        "total_chunks": total_chunks,
        "source": "github"  # Can be expanded later
    }

def process_repository(repo_path: str, output_file: str = "chunks.json"):
    """
    Process all markdown files in a repository.
    
    Args:
        repo_path: Path to the repository root
        output_file: JSON file to write chunks to
    """
    repo_path = Path(repo_path).expanduser()
    chunks_data = []
    
    # Find all markdown files
    md_files = list(repo_path.rglob("*.md"))
    
    print(f"Found {len(md_files)} markdown files")
    
    for md_file in md_files:
        # Skip certain files
        if any(skip in str(md_file) for skip in ['.git', 'node_modules', 'CHANGELOG']):
            continue
        
        print(f"Processing: {md_file}")
        
        try:
            content = read_markdown_file(str(md_file))
            
            # Skip very small files
            if len(content) < 100:
                print(f"  Skipping (too small): {md_file}")
                continue
            
            # Chunk the content
            chunks = chunk_text(content)
            print(f"  Created {len(chunks)} chunks")
            
            # Create chunk records
            for idx, chunk_content in enumerate(chunks):
                chunk_data = {
                    "text": chunk_content,
                    "metadata": extract_metadata(str(md_file), idx, len(chunks))
                }
                chunks_data.append(chunk_data)
        
        except Exception as e:
            print(f"  Error processing {md_file}: {e}")
            continue
    
    # Save chunks to JSON file
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessed {len(chunks_data)} total chunks")
    print(f"Saved to: {output_path.absolute()}")
    
    return chunks_data

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python process_docs.py <repo_path> [output_file]")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "chunks.json"
    
    process_repository(repo_path, output_file)

