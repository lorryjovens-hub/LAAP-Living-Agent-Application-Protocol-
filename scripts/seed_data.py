#!/usr/bin/env python3
"""Seed data generator for LAAP"""
import json, random, time

def generate_identity(name: str = "test_lifeform") -> dict:
    return {
        "id": f"did:laap:{hash(name) & 0xFFFFFFFFFFFFFFFF:016x}",
        "name": name,
        "type": "resident",
        "birthTime": time.time(),
        "genome": {"parentId": None, "generation": 1, "mutations": []},
        "capabilities": ["memory", "evolution", "communication"],
        "personality": {
            "openness": random.uniform(0.3, 0.9),
            "conscientiousness": random.uniform(0.3, 0.9),
            "extraversion": random.uniform(0.2, 0.8),
            "agreeableness": random.uniform(0.4, 0.9),
            "neuroticism": random.uniform(0.1, 0.6),
        }
    }

def generate_memory_entries(count: int = 100) -> list:
    entries = []
    templates = [
        "User asked about {topic}",
        "System detected {event}",
        "Learned new skill: {skill}",
        "Interacted with {entity}",
        "Error occurred: {error}",
    ]
    topics = ["Python", "AI", "data science", "web development", "machine learning"]
    for i in range(count):
        entries.append({
            "id": f"mem_{i:04d}",
            "content": random.choice(templates).format(
                topic=random.choice(topics),
                event="configuration change",
                skill="pattern matching",
                entity="user_001",
                error="timeout"
            ),
            "importance": random.random(),
            "timestamp": time.time() - random.randint(0, 86400 * 30),
        })
    return entries

def generate_evolution_proposal() -> dict:
    targets = ["memory.recall_threshold", "agent.temperature", "tool.retry_policy", "system.response_time"]
    return {
        "target": random.choice(targets),
        "current_value": random.uniform(0.1, 0.9),
        "proposed_value": random.uniform(0.1, 0.9),
        "rationale": "Performance optimization based on usage patterns",
        "risk_level": random.choice(["low", "medium", "high"]),
    }

if __name__ == "__main__":
    data = {
        "identity": generate_identity(),
        "memories": generate_memory_entries(50),
        "proposals": [generate_evolution_proposal() for _ in range(5)],
    }
    with open("seed_data.json", "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Generated seed data: {len(data['memories'])} memories, {len(data['proposals'])} proposals")
