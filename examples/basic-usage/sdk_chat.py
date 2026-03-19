"""Chat with OpenAI + memwire-sdk for persistent memory."""

import os
from openai import OpenAI
from memwire_sdk import MemWireClient

openai_client = OpenAI()
memory = MemWireClient(
    os.getenv("MEMWIRE_URL", "http://localhost:8000"),
    api_key=os.getenv("MEMWIRE_API_KEY"),
)

USER_ID = "chat_user"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
SYSTEM = "You are a helpful assistant. Use memory context to personalize responses."

history: list[dict] = []


def chat(user_input: str) -> str:
    # recall relevant memories
    recall = memory.recall(user_input, USER_ID)

    messages = [{"role": "system", "content": SYSTEM}]
    if recall.formatted:
        messages.append({"role": "system", "content": f"Memory:\n{recall.formatted}"})
    messages.extend(history[-20:])
    messages.append({"role": "user", "content": user_input})

    # stream response
    print("Assistant: ", end="", flush=True)
    stream = openai_client.chat.completions.create(model=MODEL, messages=messages, stream=True)
    chunks = []
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
            chunks.append(delta)
    print()

    response = "".join(chunks)

    # update history
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response})

    # store to memory and reinforce
    memory.add(user_id=USER_ID, messages=[
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": response},
    ])
    memory.feedback(assistant_response=response, user_id=USER_ID)  # pass LLM output to reinforce paths

    return response


if __name__ == "__main__":
    print("Chat with Memory (type 'quit' to exit)\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() == "quit":
            break
        chat(user_input)

    memory.close()
