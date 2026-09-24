"""
Exemplo mínimo: CrewAI + Mem0 (self-hosted) via TOOL MANUAL.

MUDANÇA IMPORTANTE: o CrewAI 1.15.22 instalado não tem, dentro do
próprio pacote, nenhum código de integração nativa com "provider":
"mem0" (confirmado via grep no site-packages inteiro). O
memory_config nativo que tentamos antes era silenciosamente
ignorado, e o CrewAI caía pro sistema de memória padrão dele
(ChromaDB), que falhava por um conflito de versão com posthog —
daí o aviso "memory_save_failed" que aparecia, sem relação nenhuma
com o Mem0 de verdade.

Por isso aqui: memory=False (desliga a memória padrão quebrada do
CrewAI) e uma Tool manual que chama o Mem0 diretamente para BUSCAR
memórias relevantes antes de responder. A GRAVAÇÃO de memória
(add()) é feita manualmente depois de cada kickoff(), fora do
CrewAI.

Pré-requisitos (no venv do CrewAI):
    pip install crewai mem0ai==2.0.14 neo4j langchain-neo4j python-dotenv
"""

import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool
from mem0 import Memory

load_dotenv()  # espera NEO4J_PASSWORD no .env

USER_ID = "rizzo"

# --- Config local do Mem0, reaproveitando o stack que você já validou ---
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

mem0_client = Memory.from_config(local_mem0_config)


# --- Tool manual: o agente chama isso explicitamente pra buscar memórias ---
class BuscarMemoriaTool(BaseTool):
    name: str = "buscar_memoria"
    description: str = (
        "Busca memórias salvas sobre o usuário que sejam relevantes para a "
        "pergunta atual. Use isso antes de responder, para personalizar a resposta."
    )

    def _run(self, query: str) -> str:
        # search() no mem0ai 2.x exige filters=, não user_id= direto
        result = mem0_client.search(query, filters={"user_id": USER_ID}, limit=5)
        memories = result.get("results", [])
        if not memories:
            return "Nenhuma memória relevante encontrada sobre o usuário."
        return "\n".join(f"- {m['memory']}" for m in memories)


def salvar_memoria(user_input: str, agent_output: str) -> None:
    """Chamado manualmente depois de cada kickoff() pra gravar a interação."""
    # add() no mem0ai ainda aceita user_id= direto (não foi afetado pela
    # mudança que quebrou o search()/get_all())
    mem0_client.add(
        [
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": agent_output},
        ],
        user_id=USER_ID,
    )


# --- LLM que o agente vai usar pra "pensar" ---
ollama_llm = LLM(
    model="ollama/qwen3:14b",
    base_url="http://localhost:11434",
)

# --- Agente e task de exemplo ---
agent = Agent(
    role="Assistente pessoal",
    goal="Responder ao usuário usando o que já sabe sobre ele",
    backstory=(
        "Você SEMPRE usa a tool buscar_memoria antes de responder, para "
        "checar o que já sabe sobre o usuário e personalizar a resposta."
    ),
    llm=ollama_llm,
    tools=[BuscarMemoriaTool()],
    verbose=True,
)

task = Task(
    description=(
        "O usuário disse: '{input}'. Primeiro use a tool buscar_memoria "
        "para checar o que você já sabe sobre ele, depois responda levando "
        "isso em conta."
    ),
    expected_output="Uma resposta curta e personalizada.",
    agent=agent,
)

# memory=False: desliga o sistema de memória padrão do CrewAI (que está
# quebrado por um conflito de dependência e não tem nada a ver com o Mem0)
crew = Crew(agents=[agent], tasks=[task], memory=False, verbose=True)

if __name__ == "__main__":
    # Rodada 1: ensina uma preferência
    entrada1 = "Eu prefiro respostas técnicas e diretas, sem enrolação."
    resultado1 = crew.kickoff(inputs={"input": entrada1})
    print("--- Rodada 1 ---")
    print(resultado1)
    salvar_memoria(entrada1, str(resultado1))

    # Rodada 2: pergunta nova — o agente deve usar buscar_memoria e
    # encontrar a preferência ensinada na Rodada 1
    entrada2 = "Como funciona um transformer?"
    resultado2 = crew.kickoff(inputs={"input": entrada2})
    print("--- Rodada 2 (deve refletir a preferência aprendida) ---")
    print(resultado2)
    salvar_memoria(entrada2, str(resultado2))
