import os
from dotenv import load_dotenv
from mem0 import Memory

load_dotenv()  # carrega as variáveis do .env pro ambiente

config = {
    "llm": {
        "provider": "ollama",
        "config": {
            "model": "qwen3:14b",
            "ollama_base_url": "http://localhost:11434"
        }
    },
    "embedder": {
        "provider": "ollama",
        "config": {
            "model": "nomic-embed-text",
            "ollama_base_url": "http://localhost:11434"
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0_memories",
            "embedding_model_dims": 768,
            "path": "/home/guilherme/Projects/AI/ai-agents/mem0/qdrant_data"
        }
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": "bolt://localhost:7687",
            "username": "neo4j",
            "password": os.getenv("NEO4J_PASSWORD"),
            "database": "neo4j"
        }
    },
    "version": "v1.1"
}

memory = Memory.from_config(config_dict=config)
