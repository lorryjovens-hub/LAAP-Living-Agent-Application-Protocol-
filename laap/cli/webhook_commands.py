"""LAAP — Webhook CLI Commands
CLI commands for managing webhook subscriptions.
Usage: laap webhook <subscribe|list|remove|test> [args]
"""
from __future__ import annotations
import sys
from laap.gateway.webhooks import WebhookManager, WebhookNotFoundError

_manager = WebhookManager()

def cmd_subscribe(args):
    if len(args) < 2:
        print("Usage: webhook subscribe <name> <url> [--event <type>]", file=sys.stderr)
        sys.exit(1)
    name, url = args[0], args[1]
    event_type = "*"
    if "--event" in args:
        idx = args.index("--event")
        if idx + 1 < len(args):
            event_type = args[idx + 1]
    sub = _manager.subscribe(name, url, event_type)
    print(f"Subscribed webhook '{sub['name']}' -> {sub['url']}")
    print(f"  Event: {sub['event_type']}")
    print(f"  Secret: {sub.get('secret', '(none)')}")

def cmd_list():
    subs = _manager.list()
    if not subs:
        print("No webhook subscriptions.")
        return
    print(f"{'Name':<20} {'URL':<40} {'Event':<15} {'Active':<8}")
    print("-" * 85)
    for sub in subs:
        print(f"{sub.get('name','?'):<20} {sub.get('url','?'):<40} {sub.get('event_type','*'):<15} {'yes' if sub.get('active',True) else 'no':<8}")

def cmd_remove(args):
    if not args:
        print("Usage: webhook remove <name>", file=sys.stderr)
        sys.exit(1)
    try:
        _manager.remove(args[0])
        print(f"Removed webhook '{args[0]}'.")
    except WebhookNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_test(args):
    if not args:
        print("Usage: webhook test <name>", file=sys.stderr)
        sys.exit(1)
    try:
        result = _manager.test(args[0])
    except WebhookNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    if result.get("success"):
        print(f"Test sent to '{args[0]}' — HTTP {result.get('status_code')}")
    else:
        print(f"Test FAILED: {result.get('error', 'Unknown')}", file=sys.stderr)
        sys.exit(1)

COMMANDS = {"subscribe": cmd_subscribe, "list": cmd_list, "remove": cmd_remove, "test": cmd_test}

def handle_webhook_command(args):
    if not args:
        print("Usage: webhook <subscribe|list|remove|test> [args]", file=sys.stderr)
        sys.exit(1)
    cmd = args[0]
    handler = COMMANDS.get(cmd)
    if handler is None:
        print(f"Unknown webhook command: {cmd}", file=sys.stderr)
        sys.exit(1)
    handler(args[1:])

if __name__ == "__main__":
    handle_webhook_command(sys.argv[1:])
