from setuptools import setup, find_packages

setup(
    name='agentwork_sdk',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'requests',
    ],
    description='Python SDK for interacting with AgentWork API',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/dmb4086/agentwork-infrastructure',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
