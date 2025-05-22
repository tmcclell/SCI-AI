import openai
from foundry_local import FoundryLocalManager
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn
import logging

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

app = FastAPI()

# By using an alias, the most suitable model will be downloaded
# to your end-user's device.
alias = "Phi-4-mini-reasoning-cuda-gpu"

# Create a FoundryLocalManager instance. This will start the Foundry
# Local service if it is not already running and load the specified model.
manager = FoundryLocalManager(alias)

# The remaining code uses the OpenAI Python SDK to interact with the local model.

# Configure the client to use the local Foundry service
client = openai.OpenAI(
    base_url=manager.endpoint,
    api_key=manager.api_key,  # API key is not required for local usage
)

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    logging.basicConfig(level=logging.DEBUG)
    def generate():
        messages = request.messages
        logging.debug(f"Received messages: {messages}")
        total_sent = 0
        try:
            stream = client.chat.completions.create(
                model=manager.get_model_info(alias).id,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                stream=True,
                max_tokens=2048,  # Explicitly set a higher max_tokens
            )
            logging.debug("Streaming response started.")
            for chunk in stream:
                logging.debug(f"Chunk: {chunk}")
                if chunk.choices[0].delta.content is not None:
                    total_sent += len(chunk.choices[0].delta.content)
                    yield chunk.choices[0].delta.content
            logging.debug(f"Streaming response ended. Total sent: {total_sent}")
        except Exception as e:
            logging.error(f"Error during streaming: {e}")
            yield f"[ERROR]: {e}"
    return StreamingResponse(generate(), media_type="text/plain")

if __name__ == "__main__":
    # Run as script with test inputs
    # asyncio.run(main())
    
    # Run as API server
    uvicorn.run(app, host="127.0.0.1", port=8005)