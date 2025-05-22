import os
from dotenv import load_dotenv

from azure.identity.aio import DefaultAzureCredential

from semantic_kernel.agents import AgentGroupChat, AzureAIAgent, AzureAIAgentSettings, AzureAssistantAgent
from semantic_kernel.agents.strategies import TerminationStrategy
from semantic_kernel.contents import AuthorRole

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import uvicorn
import httpx
import logging
import openai
from foundry_local import FoundryLocalManager

# Load environment variables from the .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize FoundryLocalManager with the alias for phi-3.5-mini
alias = "Phi-3.5-mini-instruct-cuda-gpu"
manager = FoundryLocalManager(alias)

# Configure the OpenAI client to use the local Foundry endpoint
openai_client = openai.OpenAI(
    base_url=manager.endpoint,
    api_key=manager.api_key  # Not required for local usage, but included for compatibility
)

class ApprovalTerminationStrategy(TerminationStrategy):
    """A strategy for determining when an agent should terminate."""

    async def should_agent_terminate(self, agents, history):
        logger.debug(f"Checking termination: agents={agents}, last_message={history[-1].content if history else None}")
        return "approved" in history[-1].content.lower()

class ChatRequest(BaseModel):
    messages: List[str]

async def call_foundry_local(messages):
    logger.debug(f"Calling Foundry Local via OpenAI SDK with messages: {messages}")
    chat_messages = [{"role": "user", "content": m} for m in messages]
    logger.debug(f"Prepared chat messages for OpenAI SDK: {chat_messages}")
    # Use the model id from the manager
    model_id = manager.get_model_info(alias).id
    logger.debug(f"Using model id: {model_id}")
    # Create a streaming response using the OpenAI SDK
    stream = openai_client.chat.completions.create(
        model=model_id,
        messages=chat_messages,
        stream=True
    )
    for chunk in stream:
        logger.debug(f"Received chunk from Foundry Local OpenAI SDK: {chunk}")
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

async def process_chat(messages):
    logger.debug(f"Starting process_chat with messages: {messages}")
    model_deployment_name = os.getenv("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME")
    if not model_deployment_name:
        raise ValueError("AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME is not set in the environment.")
    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds) as client,
    ):
        logger.debug("Connected to Azure AI Foundry client.")
        # Log the agent ID being requested
        assistant_id = os.getenv("AZURE_AI_SCI_ASSISTANT")
        logger.debug(f"Requesting assistant agent with ID: {assistant_id}")
        # Try listing agents, but handle 404 gracefully
        try:
            logger.debug("Listing all available agents:")
            agents = []
            async for agent in client.agents.list_agents():
                logger.debug(f"Agent ID: {agent.id}, Name: {getattr(agent, 'name', None)}")
                agents.append(agent)
        except Exception as e:
            logger.error(f"Error listing agents: {e}")
        # Now try to get the assistant agent
        try:
            assistant_agent_definition = await client.agents.get_agent(assistant_id)
            agent_assistant = AzureAIAgent(
                client=client,
                definition=assistant_agent_definition,
            )
            logger.debug(f"Assistant agent definition: {assistant_agent_definition}")
        except Exception as e:
            logger.error(f"Error getting assistant agent: {e}")
            raise
        try:
            energy_agent_definition = await client.agents.get_agent(os.getenv("AZURE_AI_ENERGY"))
            logger.debug(f"Energy agent definition: {energy_agent_definition}")
        except Exception as e:
            logger.error(f"Error getting energy agent: {e}")
            raise
        try:
            embedded_agent_definition = await client.agents.get_agent(os.getenv("AZURE_AI_EMBODIED"))
            logger.debug(f"Embedded agent definition: {embedded_agent_definition}")
        except Exception as e:
            logger.error(f"Error getting embedded agent: {e}")
            raise

        agent_names = [
            assistant_agent_definition["name"],
            energy_agent_definition["name"],
            embedded_agent_definition["name"]
        ]
        logger.debug(f"Agent names: {agent_names}")
        system_prompt = f"Agents available: {', '.join(agent_names)}. Respond as the most appropriate agent."
        foundry_messages = [system_prompt] + messages
        logger.debug(f"Final messages sent to Foundry Local: {foundry_messages}")
        async for chunk in call_foundry_local(foundry_messages):
            logger.debug(f"Yielding chunk from Foundry Local: {chunk}")
            yield chunk

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    logger.debug(f"Received chat request: {request}")
    async def generate():
        async for chunk in process_chat(request.messages):
            logger.debug(f"Streaming chunk to client: {chunk}")
            yield chunk
    return StreamingResponse(generate(), media_type="text/plain")

if __name__ == "__main__":
    logger.debug("Starting API server on 127.0.0.1:8005")
    uvicorn.run(app, host="127.0.0.1", port=8005)