#!/usr/bin/env python3
"""
Simple upload script that doesn't require unstructured.
"""

import os
import sys
from pathlib import Path
import re

# Add chatbot to path
sys.path.insert(0, str(Path(__file__).parent / "chatbot"))

from dotenv import load_dotenv
from bot.memory.openai_embedder import embed
from bot.memory.vector_database.pinecone_store import PineconeStore
from bot.memory.vector_database.id_generator import generate_deterministic_id

load_dotenv()

def chunk_text(text, chunk_size=1000, overlap=100):
    """Simple text chunker."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings near the chunk boundary
            sentence_end = max(
                text.rfind('.', start, end),
                text.rfind('!', start, end),
                text.rfind('?', start, end)
            )
            
            if sentence_end > start:
                end = sentence_end + 1
            else:
                # No sentence boundary, look for space
                space_pos = text.rfind(' ', start, end)
                if space_pos > start:
                    end = space_pos
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = max(start + 1, end - overlap)
    
    return chunks

def upload_markdown_files():
    """Upload markdown files to Pinecone."""
    docs_path = Path(__file__).parent / "docs"
    index_name = os.environ["PINECONE_INDEX_NAME"]
    
    if not docs_path.exists():
        print(f"❌ Docs directory not found: {docs_path}")
        return
    
    # Find all markdown and text files
    md_files = list(docs_path.glob("**/*.md")) + list(docs_path.glob("**/*.txt"))
    if not md_files:
        print(f"❌ No markdown files found in {docs_path}")
        return
    
    print(f"📁 Found {len(md_files)} markdown files")
    
    store = PineconeStore(index_name=index_name)
    vectors = []
    
    for md_file in md_files:
        print(f"📖 Processing {md_file.name}")
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove markdown syntax
            clean_content = re.sub(r'[#*`\[\]_~]', '', content)
            clean_content = re.sub(r'\n+', ' ', clean_content).strip()
            
            if not clean_content:
                continue
            
            # Chunk the content
            chunks = chunk_text(clean_content)
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:  # Skip very short chunks
                    continue
                
                vector_id = generate_deterministic_id(f"{md_file.name}_{i}_{chunk[:50]}")
                embedding = embed(chunk)
                
                vectors.append({
                    "id": vector_id,
                    "values": embedding,
                    "metadata": {
                        "text": chunk,
                        "source": str(md_file.relative_to(docs_path)),
                        "chunk_index": i
                    }
                })
        
        except Exception as e:
            print(f"❌ Error processing {md_file}: {e}")
    
    if not vectors:
        print("❌ No vectors to upload")
        return
    
    # Upload in batches
    batch_size = 100
    total_uploaded = 0
    
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        store.upsert(batch)
        total_uploaded += len(batch)
        print(f"📤 Uploaded batch {i//batch_size + 1}/{(len(vectors)-1)//batch_size + 1} ({len(batch)} vectors)")
    
    print(f"✅ Upload complete! {total_uploaded} vectors uploaded to {index_name}")

if __name__ == "__main__":
    try:
        upload_markdown_files()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
