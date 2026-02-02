# Agent Prompt Registry

Version control, A/B testing, and analytics for AI agent prompts.

## Features

- **Version Control**: Track prompt changes with full history
- **A/B Testing**: Compare prompt variants with statistical significance
- **Analytics**: Measure success rates, latency, and cost per prompt
- **Rollback**: Instantly revert to any previous version
- **Templates**: Jinja2 templating with variable injection

## Quick Start

```bash
pip install agent-prompt-registry
```

```python
from agent_prompt_registry import PromptRegistry

registry = PromptRegistry()

# Register a prompt
registry.register(
    name="customer-support",
    prompt="You are a helpful customer support agent for {{company}}...",
    metadata={"author": "team-a", "model": "gpt-4"}
)

# Get the active prompt
prompt = registry.get("customer-support", variables={"company": "Acme Inc"})

# Start an A/B test
registry.create_experiment(
    name="customer-support",
    variants={
        "control": "You are a helpful customer support agent...",
        "friendly": "Hey there! You're a super friendly support agent..."
    },
    traffic_split={"control": 50, "friendly": 50}
)

# Get a variant (automatically tracked)
prompt, variant = registry.get_variant("customer-support")
```

## CLI

```bash
# List all prompts
prompt-registry list

# Show prompt history
prompt-registry history customer-support

# Rollback to version
prompt-registry rollback customer-support --version 3

# Export prompts
prompt-registry export prompts.yaml

# Import prompts
prompt-registry import prompts.yaml
```

## A/B Testing

```python
# Create experiment
registry.create_experiment(
    name="summarizer",
    variants={
        "concise": "Summarize in 2 sentences...",
        "detailed": "Provide a comprehensive summary..."
    },
    traffic_split={"concise": 50, "detailed": 50},
    success_metric="user_rating"
)

# Record outcome
registry.record_outcome(
    prompt_name="summarizer",
    variant="concise",
    success=True,
    metrics={"user_rating": 4.5, "latency_ms": 230}
)

# Get experiment results
results = registry.get_experiment_results("summarizer")
# {
#   "concise": {"trials": 500, "success_rate": 0.82, "avg_rating": 4.2},
#   "detailed": {"trials": 500, "success_rate": 0.78, "avg_rating": 3.9},
#   "winner": "concise",
#   "confidence": 0.95
# }
```

## Templates

```python
# Register with Jinja2 template
registry.register(
    name="email-writer",
    prompt="""
    Write an email with the following characteristics:
    - Tone: {{tone}}
    - Length: {{length}}
    - Purpose: {{purpose}}

    {% if include_signature %}
    Include signature: {{signature}}
    {% endif %}
    """
)

# Render with variables
prompt = registry.get("email-writer", variables={
    "tone": "professional",
    "length": "brief",
    "purpose": "follow up on meeting",
    "include_signature": True,
    "signature": "Best, John"
})
```

## Storage Backends

```python
# SQLite (default)
registry = PromptRegistry(backend="sqlite", path="prompts.db")

# PostgreSQL
registry = PromptRegistry(
    backend="postgres",
    connection_string="postgresql://user:pass@localhost/prompts"
)

# Redis (for distributed systems)
registry = PromptRegistry(
    backend="redis",
    host="localhost",
    port=6379
)

# Git (for GitOps workflows)
registry = PromptRegistry(
    backend="git",
    repo_path="./prompts-repo"
)
```

## License

MIT
