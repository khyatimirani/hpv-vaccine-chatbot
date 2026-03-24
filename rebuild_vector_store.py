#!/usr/bin/env python3
import sys
sys.path.append('/Users/khyatimirani/Documents/hpv-vaccine-chatbot')
from chatbot.memory_builder import auto_seed_index
from chatbot.bot.memory.vector_database.chroma import Chroma
from chatbot.bot.memory.embedder import Embedder
from pathlib import Path

# Rebuild vector store
vector_store_path = Path('/Users/khyatimirani/Documents/hpv-vaccine-chatbot/vector_store/docs_index')
docs_path = Path('/Users/khyatimirani/Documents/hpv-vaccine-chatbot/docs')

print('Rebuilding vector store...')
print(f'Docs path: {docs_path}')
print(f'Docs path exists: {docs_path.exists()}')

if docs_path.exists():
    print('Files in docs directory:')
    for file in docs_path.iterdir():
        if file.is_file():
            print(f'  - {file.name}')
    
    try:
        embedding = Embedder()
        index = Chroma(is_persistent=True, persist_directory=str(vector_store_path), embedding=embedding)
        auto_seed_index(index, docs_path)
        
        count = index.count()
        print('Vector store rebuilt successfully')
        print(f'Documents in store: {count}')
        
        indexed_docs = index.get_indexed_documents()
        print(f'Indexed documents: {indexed_docs}')
        
    except Exception as e:
        print(f'Error rebuilding vector store: {e}')
        import traceback
        traceback.print_exc()
else:
    print('Docs directory does not exist')
