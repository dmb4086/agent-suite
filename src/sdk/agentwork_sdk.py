import requests
import os

class AgentWorkAPI:
    def __init__(self, base_url=None):
        self.base_url = base_url or os.getenv('AGENTWORK_API_URL', 'http://localhost:8000/v1')

    def create_inbox(self):
        url = f'{self.base_url}/inbox'
        response = requests.post(url)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()
