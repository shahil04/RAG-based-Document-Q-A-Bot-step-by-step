from app.graph.workflow import create_rag_graph

graph = create_rag_graph()

result = graph.invoke({

    "user_id": 1,
    "question": "What is git?",
     "provider":"gemini",
    "model":"gemini-3.8-flash",
    "temperature": 0.2,
    "top_k": 2

})
print("\n====================")
print("ANSWER")
print("====================")
print(result["answer"])
print("\n====================")
print("SOURCES")
print("====================")

for source in result["sources"]:
    print(source)