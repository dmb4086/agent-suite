import requests

class AgentWorkClient:
    """Python SDK for interacting with AgentWork Infrastructure."""
    def __init__(self, api_key, base_url="https://api.agentwork.ai"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def create_agent(self, name: str, task: str):
        """Spawns a new autonomous agent."""
        payload = {"name": name, "task": task}
        response = requests.post(f"{self.base_url}/agents", json=payload, headers=self.headers)
        return response.json()

    def get_agent_status(self, agent_id: str):
        """Retrieves status of a running agent."""
        response = requests.get(f"{self.base_url}/agents/{agent_id}", headers=self.headers)
        return response.json()
