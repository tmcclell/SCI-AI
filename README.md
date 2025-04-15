# SCI_AI

![alt text](<SCI AI.png>)

Currently the code only uses a single agent and is in early stages.

The diagram is desired state which includes Semantic Kernel or agent orchestration. The agents were created in AI Foundry ahead of time and referenced in the code. 

Steps to run solution:
1. Clone the repo.
2. Create 2 agents in AI Foundry (SCI Assistant, Energy, Embodied).
3. Save .env_sample to .env and update variables with your resource identifiers.
4. Install dependencies using pip install -r requirements.txt
5. Start terminal session (fastapi) - uvicorn main:app --port 8005
6. Start terminal session (streamlit - ui) - streamlit run chat_app.py