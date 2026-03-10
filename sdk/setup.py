from setuptools import setup, find_packages

setup(
    name="agent-suite-sdk",
    version="0.1.0",
    description="Python SDK for AgentWork Infrastructure API",
    author="OpenClaw Bot",
    author_email="bot@openclaw.ai",
    url="https://github.com/dmb4086/agentwork-infrastructure",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
