from setuptools import setup, find_packages

setup(
    name="agent-prompt-registry",
    version="0.1.0",
    description="Version control, A/B testing, and analytics for AI agent prompts",
    author="Yoshi Kondo",
    author_email="yksanjo@gmail.com",
    url="https://github.com/yksanjo/agent-prompt-registry",
    packages=find_packages(),
    install_requires=[
        "jinja2>=3.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
        "pyyaml>=6.0.0",
    ],
    entry_points={
        "console_scripts": [
            "prompt-registry=agent_prompt_registry.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)
