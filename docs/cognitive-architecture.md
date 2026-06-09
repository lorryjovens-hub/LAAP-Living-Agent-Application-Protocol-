# LAAP Cognitive Architecture

## PSI Theory Implementation

LAAP implements a biologically-inspired cognitive architecture based on Dörner's PSI theory, with extensions for modern LLM integration.

### Core Loop

```
Perception → Need Assessment → Emotion Update → Action Selection → Execution → Learning
     ↑                                                                         │
     └───────────────────────── Feedback Loop ────────────────────────────────┘
```

### Five Core Needs (NeedDriveSystem)

| Need | Description | Decay | Satisfiers |
|------|-------------|-------|------------|
| **Certainty** | Predictability of environment | 0.008 | explore, analyze |
| **Competence** | Mastery and skill growth | 0.012 | analyze, learning |
| **Autonomy** | Self-determination | 0.005 | reflect, free choice |
| **Relatedness** | Social connection | 0.010 | communicate, gateway |
| **Energy** | Resource acquisition | 0.015 | rest, efficiency |

### Emotion Gradient (EG-MRSI)

Emotion is computed as a **differential signal** of need satisfaction, not categorical labels:

- **Valence**: Overall satisfaction (needs met → positive)
- **Arousal**: Rate of change in satisfaction
- **Dominance**: Sense of control (task success)
- **Confidence**: Familiarity with situation

### Action Selection

Actions are selected based on:
1. **Dominant need** (lowest satisfaction → highest drive)
2. **Emotional state** (low confidence → explore more)
3. **Skill proficiency** (known skills preferred)
4. **Random exploration** (configurable rate)

### RSI Self-Improvement

The Recursive Self-Improvement engine implements a Darwin-Gödel Machine:

```
Observe → Propose → Sandbox Test → Evaluate → Adopt/Reject
           │                                        │
           └─────────── Cycle repeats ──────────────┘
```

### Memory Architecture

```
Working Memory (9 items) → Episodic Memory → Semantic Memory
                                ↓
                         Skill Memory (Procedural)
                                ↓
                         Reflective Memory
```
