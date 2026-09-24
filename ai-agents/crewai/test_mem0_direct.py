"""
Diagnóstico: chama o Mem0 diretamente (sem CrewAI no meio) usando a
MESMA config do crewai_mem0_example.py, pra ver o erro real por trás
do aviso "memory_save_failed" que o CrewAI mostrou sem detalhes.

Rode isso no mesmo venv do CrewAI (onde mem0ai já está instalado).
"""

import os
import traceback
from dotenv import load_dotenv

load_dotenv()

local_mem0_config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "collection_name": "mem0_memories",
            "embedding_model_dims": 768,
            "path": "/home/guilherme/Projects/AI/ai-agents/mem0/qdrant_data",
        },
    },
    "llm": {
        "provider": "ollama",
        "config": {"model": "qwen3:14b"},
    },
    "embedder": {
        "provider": "ollama",
        "config": {"model": "nomic-embed-text"},
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {
            "url": "bolt://localhost:7687",
            "username": "neo4j",
            "password": os.environ["NEO4J_PASSWORD"],
        },
    },
}

print("--- Tentando importar e inicializar o Mem0 ---")
try:
    from mem0 import Memory

    m = Memory.from_config(local_mem0_config)
    print("Mem0 inicializado com sucesso.")
except Exception:
    print("FALHOU na inicialização do Mem0:")
    traceback.print_exc()
    raise SystemExit(1)

print("\n--- Tentando fazer um add() de teste ---")
try:
    result = m.add(
        "Eu prefiro respostas técnicas e diretas, sem enrolação.",
        user_id="rizzo",
    )
    print("add() funcionou. Resultado:")
    print(result)
except Exception:
    print("FALHOU no add():")
    traceback.print_exc()
    raise SystemExit(1)

print("\n--- Tentando fazer um search() de teste ---")
try:
    result = m.search("Como o usuário prefere as respostas?", user_id="rizzo")
    print("search() funcionou. Resultado:")
    print(result)
except Exception:
    print("FALHOU no search():")
    traceback.print_exc()
    raise SystemExit(1)
