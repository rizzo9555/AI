from config import memory

conversation = [
    {"role": "user", "content": "Uso Ollama local com uma RTX 4080 Super de 16GB."},
    {"role": "assistant", "content": "Entendido, vou lembrar disso."}
]

memory.add(conversation, user_id="rizzo")

results = memory.search(
    "Qual GPU eu uso?",
    filters={"user_id": "rizzo"},
    limit=3
)
for hit in results["results"]:
    print(hit["memory"])
