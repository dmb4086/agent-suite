
# AgentWork Python SDK

This SDK provides a Python interface for interacting with the AgentWork API.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/dmb4086/agentwork-infrastructure.git
   ```

2. Navigate to the SDK directory:
   ```bash
   cd agentwork-infrastructure/python-sdk
   ```

## Usage

### Initialize the Client

```python
from client import AgentWorkClient

# Initialize the client with the base URL and API key (if required)
client = AgentWorkClient(base_url="http://localhost:5000/api", api_key="your_api_key")
```

### Create an Agent

```python
# Create a new agent
response = client.create_agent(name="test_agent", task="test_task")
print(response)
```

### Get Agent Status

```python
# Get the status of an agent
agent_id = "your_agent_id"
status = client.get_agent_status(agent_id)
print(status)
```

## Dependencies

- Python 3.6+
- `requests` library (install with `pip install requests`)

## License

MIT
