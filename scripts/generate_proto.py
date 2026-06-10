#!/usr/bin/env python3
"""Protocol code generation script"""
import os, json

def generate_protocol_stub(protocol_name: str, version: str, fields: list) -> str:
    lines = [f'"""Auto-generated {protocol_name} v{version} stub"""']
    lines.append('from __future__ import annotations')
    lines.append('from dataclasses import dataclass, field')
    lines.append('from typing import Any, Dict, List, Optional')
    lines.append('')
    lines.append(f'')
    lines.append(f'PROTOCOL = "{protocol_name}"')
    lines.append(f'VERSION = "{version}"')
    lines.append('')
    lines.append(f'')
    return '\n'.join(lines)

def generate_all():
    protocols = {
        "LAAP-ID": {"version": "1.0", "fields": ["id", "type", "birthTime", "genome", "capabilities", "signature"]},
        "LAAP-COM": {"version": "1.0", "fields": ["messageId", "sender", "recipient", "type", "intent", "payload", "priority", "ttl"]},
        "LAAP-LIFE": {"version": "1.0", "fields": ["lifeStage", "event", "timestamp", "data"]},
        "LAAP-MEM": {"version": "1.0", "fields": ["level", "type", "content", "importance", "timestamp"]},
        "LAAP-UI": {"version": "1.0", "fields": ["layout", "components", "theme", "events"]},
        "LAAP-SYNC": {"version": "1.0", "fields": ["syncOp", "documentId", "version", "delta"]},
    }
    output_dir = "laap/protocol"
    for name, info in protocols.items():
        stub = generate_protocol_stub(name, info["version"], info["fields"])
        print(f"Generated: {name} v{info['version']}")

if __name__ == "__main__":
    generate_all()
