#!/usr/bin/env python3
"""
Gas Town Seed Generator

Generates mock Wave messages from Gas Town agents that can be:
1. Saved as JSON/CSV for reproducible demos
2. Replayed through the Wave server
3. Used to seed the database with realistic conversation data

Usage:
    # Generate seed data
    python scripts/gastown-seed-generator.py generate --format json --output seeds/sprint-demo.json
    python scripts/gastown-seed-generator.py generate --format csv --output seeds/sprint-demo.csv

    # Replay seed data to server
    python scripts/gastown-seed-generator.py replay --input seeds/sprint-demo.json --speed 0.5

    # List available scenarios
    python scripts/gastown-seed-generator.py list
"""

import argparse
import asyncio
import csv
import json
import random
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

WAVE_SERVER = "http://localhost:9898"


# =============================================================================
# Agent Definitions (Gas Town Crew)
# =============================================================================

@dataclass
class Agent:
    name: str
    fullname: str
    email: str
    role: str
    icon: str

AGENTS = {
    "goldie": Agent("goldie", "Goldie Wilson", "goldie@gastown.local", "Mayor", "🎩"),
    "book": Agent("book", "Shepherd Book", "book@gastown.local", "Deacon", "📖"),
    "uatu": Agent("uatu", "Uatu the Watcher", "uatu@gastown.local", "Witness", "👁️"),
    "case": Agent("case", "Henry Case", "case@gastown.local", "Console Cowboy", "👨‍💻"),
    "molly": Agent("molly", "Molly Millions", "molly@gastown.local", "Street Samurai", "🔒"),
    "deckard": Agent("deckard", "Rick Deckard", "deckard@gastown.local", "Blade Runner", "🧪"),
    "samantha": Agent("samantha", "Samantha OS1", "samantha@gastown.local", "Research AI", "🏗️"),
    "kaylee": Agent("kaylee", "Kaylee Frye", "kaylee@gastown.local", "Ship Mechanic", "⚙️"),
    "scotty": Agent("scotty", "Montgomery Scott", "scotty@gastown.local", "Chief Engineer", "🚀"),
    "wintermute": Agent("wintermute", "Wintermute", "wintermute@gastown.local", "AI Coordinator", "🤖"),
}


# =============================================================================
# Message Types
# =============================================================================

class MessageType(str, Enum):
    CREATE_WAVE = "create_wave"
    BLIP = "blip"
    TASK_ASSIGN = "task_assign"
    TASK_COMPLETE = "task_complete"
    BLOCKER = "blocker"
    RESOLVED = "resolved"
    CLOSE_WAVE = "close_wave"


@dataclass
class SeedMessage:
    """A single message in a Wave conversation."""
    wave_id: str
    sequence: int
    timestamp: str  # ISO format
    sender: str
    sender_email: str
    msg_type: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "SeedMessage":
        return cls(**data)


@dataclass
class SeedScenario:
    """A complete scenario with multiple messages."""
    name: str
    description: str
    wave_id: str
    created_at: str
    messages: List[SeedMessage] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "wave_id": self.wave_id,
            "created_at": self.created_at,
            "message_count": len(self.messages),
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SeedScenario":
        messages = [SeedMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            name=data["name"],
            description=data["description"],
            wave_id=data["wave_id"],
            created_at=data["created_at"],
            messages=messages,
        )


# =============================================================================
# Scenario Generators
# =============================================================================

def generate_sprint_planning(base_time: datetime = None) -> SeedScenario:
    """Generate a sprint planning scenario."""
    base_time = base_time or datetime.now()
    wave_id = f"gastown!sprint-{base_time.strftime('%Y%m%d')}"

    messages = []
    seq = 0

    def add_msg(sender: str, msg_type: MessageType, content: str,
                delay_seconds: int = 30, **metadata):
        nonlocal seq, base_time
        agent = AGENTS[sender]
        base_time += timedelta(seconds=delay_seconds)
        messages.append(SeedMessage(
            wave_id=wave_id,
            sequence=seq,
            timestamp=base_time.isoformat(),
            sender=sender,
            sender_email=agent.email,
            msg_type=msg_type.value,
            content=content,
            metadata=metadata,
        ))
        seq += 1

    # Sprint planning flow
    add_msg("goldie", MessageType.CREATE_WAVE,
            "Sprint Planning - Wave Client Release",
            participants=list(AGENTS.keys()))

    add_msg("goldie", MessageType.BLIP,
            "Good morning Gas Town! Let's plan the wave-client-for-emacs release.")

    add_msg("goldie", MessageType.TASK_ASSIGN,
            "Review OpenAPI spec changes for auth endpoints",
            assignee="molly", priority="P1")

    add_msg("molly", MessageType.BLIP,
            "On it. Running security sweep for OWASP compliance.", delay_seconds=15)

    add_msg("goldie", MessageType.TASK_ASSIGN,
            "Run full integration test suite",
            assignee="deckard", priority="P1")

    add_msg("deckard", MessageType.BLIP,
            "Starting Voigt-Kampff... I mean pytest matrix.", delay_seconds=20)

    add_msg("goldie", MessageType.TASK_ASSIGN,
            "Sync worktrees and check for stale branches",
            assignee="case", priority="P2")

    add_msg("case", MessageType.BLIP,
            "Jacking into the matrix. Found 3 stale worktrees.", delay_seconds=45)

    add_msg("uatu", MessageType.BLIP,
            "Sprint velocity: 42 points available, 38 committed.", delay_seconds=60)

    add_msg("samantha", MessageType.BLIP,
            "Architecture review complete. OT implementation looks solid.")

    add_msg("molly", MessageType.TASK_COMPLETE,
            "Auth endpoints secured. Added rate limiting recommendation.", delay_seconds=180)

    add_msg("deckard", MessageType.BLOCKER,
            "websockets 15.0.1 API changed. Tests showing anomalies.", delay_seconds=120)

    add_msg("case", MessageType.BLIP,
            "I see the problem. Need to use ws.state instead of ws.open", delay_seconds=30)

    add_msg("deckard", MessageType.RESOLVED,
            "Applied fix. All 32 tests confirm authentic behavior.", delay_seconds=90)

    add_msg("scotty", MessageType.BLIP,
            "Captain, the CI pipeline is green. Ready for deployment.")

    add_msg("book", MessageType.BLIP,
            "Code review complete. The code walks a righteous path.")

    add_msg("wintermute", MessageType.BLIP,
            "Metrics analysis complete. Model accuracy: 94.2%")

    add_msg("kaylee", MessageType.BLIP,
            "Shiny! Workflow optimized. Reduced tmux sessions from 12 to 8.")

    add_msg("uatu", MessageType.BLIP,
            "All agents reported. The timeline is secure.")

    add_msg("goldie", MessageType.CLOSE_WAVE,
            "Sprint planning complete. If you put your mind to it, you can accomplish anything!")

    return SeedScenario(
        name="sprint-planning",
        description="Sprint planning session with full Gas Town crew",
        wave_id=wave_id,
        created_at=base_time.isoformat(),
        messages=messages,
    )


def generate_code_review(base_time: datetime = None) -> SeedScenario:
    """Generate a code review scenario."""
    base_time = base_time or datetime.now()
    pr_num = random.randint(100, 999)
    wave_id = f"gastown!review-pr-{pr_num}"

    messages = []
    seq = 0

    def add_msg(sender: str, msg_type: MessageType, content: str,
                delay_seconds: int = 30, **metadata):
        nonlocal seq, base_time
        agent = AGENTS[sender]
        base_time += timedelta(seconds=delay_seconds)
        messages.append(SeedMessage(
            wave_id=wave_id,
            sequence=seq,
            timestamp=base_time.isoformat(),
            sender=sender,
            sender_email=agent.email,
            msg_type=msg_type.value,
            content=content,
            metadata=metadata,
        ))
        seq += 1

    add_msg("case", MessageType.CREATE_WAVE,
            f"PR #{pr_num}: Add OAuth2 authentication endpoints",
            participants=["case", "book", "molly", "uatu"])

    add_msg("case", MessageType.BLIP,
            "Ready for review: specs/wave-api.openapi.yaml (+169 lines)")

    add_msg("book", MessageType.BLIP,
            "Let me examine this. The API must serve all users fairly.", delay_seconds=60)

    add_msg("molly", MessageType.BLIP,
            "Scanning auth endpoints for weaknesses.", delay_seconds=30)

    add_msg("book", MessageType.BLIP,
            "Line 295: Password example should be masked. 'secret' is a sin of exposure.",
            delay_seconds=120, line=295, file="specs/wave-api.openapi.yaml")

    add_msg("case", MessageType.BLIP,
            "Good catch. Flipping bits to '********'.", delay_seconds=45)

    add_msg("molly", MessageType.BLOCKER,
            "/auth/refresh missing request body schema. That's a hole.",
            delay_seconds=90, endpoint="/auth/refresh")

    add_msg("case", MessageType.BLIP,
            "Adding RefreshTokenRequest schema. Patching the ICE.", delay_seconds=60)

    add_msg("case", MessageType.RESOLVED,
            "Added proper OAuth2 standard fields: access_token, expires_in, token_type.",
            delay_seconds=180)

    add_msg("book", MessageType.TASK_COMPLETE,
            "The code has found its path. OAuth2 RFC 6749 compliant.")

    add_msg("molly", MessageType.TASK_COMPLETE,
            "Security sweep complete. No vulnerabilities. We're solid.")

    add_msg("uatu", MessageType.BLIP,
            "Review observed: 2 issues found, 2 resolved. Ready to merge.")

    add_msg("case", MessageType.CLOSE_WAVE,
            "Merged to main. The matrix accepts our changes.")

    return SeedScenario(
        name="code-review",
        description=f"Code review for PR #{pr_num}",
        wave_id=wave_id,
        created_at=base_time.isoformat(),
        messages=messages,
    )


def generate_incident_response(base_time: datetime = None) -> SeedScenario:
    """Generate an incident response scenario."""
    base_time = base_time or datetime.now()
    wave_id = f"gastown!incident-{base_time.strftime('%H%M')}"

    messages = []
    seq = 0

    def add_msg(sender: str, msg_type: MessageType, content: str,
                delay_seconds: int = 30, **metadata):
        nonlocal seq, base_time
        agent = AGENTS[sender]
        base_time += timedelta(seconds=delay_seconds)
        messages.append(SeedMessage(
            wave_id=wave_id,
            sequence=seq,
            timestamp=base_time.isoformat(),
            sender=sender,
            sender_email=agent.email,
            msg_type=msg_type.value,
            content=content,
            metadata=metadata,
        ))
        seq += 1

    add_msg("scotty", MessageType.CREATE_WAVE,
            "INCIDENT: Production API returning 500 errors",
            participants=["scotty", "case", "deckard", "kaylee", "goldie", "uatu"],
            severity="high")

    add_msg("scotty", MessageType.BLIP,
            "Captain, error rate spiked to 15% at 14:32 UTC. GET /api/waves/{id} affected.",
            error_rate=15, endpoint="/api/waves/{id}")

    add_msg("goldie", MessageType.BLIP,
            "All hands! Case, jack in and check those logs!", delay_seconds=30)

    add_msg("case", MessageType.BLIP,
            "Pulling logs from the matrix. Seeing TypeError in get_wave endpoint.",
            delay_seconds=45, error_type="TypeError")

    add_msg("deckard", MessageType.BLIP,
            "Reproducing locally. Confirmed: doc_data is list, not dict.",
            delay_seconds=60)

    add_msg("case", MessageType.BLIP,
            "Found the glitch! Line 367 in wave_server.py assumes dict but gets list.",
            delay_seconds=30, file="wave_server.py", line=367)

    add_msg("case", MessageType.BLIP,
            "Fix: Add isinstance(doc_data, dict) type check.", delay_seconds=15)

    add_msg("kaylee", MessageType.BLIP,
            "Got the old engine ready if we need to roll back. v0.1.9 is shiny.",
            delay_seconds=30, rollback_version="v0.1.9")

    add_msg("case", MessageType.TASK_COMPLETE,
            "Fix committed: c9fe9b5. Hotfix jacked into production.",
            delay_seconds=120, commit="c9fe9b5")

    add_msg("scotty", MessageType.BLIP,
            "She's holding together! Monitoring error rates.", delay_seconds=60)

    add_msg("deckard", MessageType.BLIP,
            "Error rate dropping: 15% -> 2% -> 0.1%. All clear.",
            delay_seconds=120, error_rate=0.1)

    add_msg("uatu", MessageType.BLIP,
            "Incident timeline: Detection 14:32, Fix 14:41, Resolution 14:45. MTTR: 13 minutes.",
            mttr_minutes=13)

    add_msg("goldie", MessageType.BLIP,
            "Outstanding work, Gas Town!")

    add_msg("scotty", MessageType.CLOSE_WAVE,
            "Incident resolved. Root cause: incomplete type handling.",
            root_cause="type_handling")

    return SeedScenario(
        name="incident-response",
        description="Production incident response",
        wave_id=wave_id,
        created_at=base_time.isoformat(),
        messages=messages,
    )


def generate_daily_standup(base_time: datetime = None) -> SeedScenario:
    """Generate a daily standup scenario."""
    base_time = base_time or datetime.now().replace(hour=9, minute=0, second=0)
    wave_id = f"gastown!standup-{base_time.strftime('%Y%m%d')}"

    messages = []
    seq = 0

    def add_msg(sender: str, msg_type: MessageType, content: str,
                delay_seconds: int = 20, **metadata):
        nonlocal seq, base_time
        agent = AGENTS[sender]
        base_time += timedelta(seconds=delay_seconds)
        messages.append(SeedMessage(
            wave_id=wave_id,
            sequence=seq,
            timestamp=base_time.isoformat(),
            sender=sender,
            sender_email=agent.email,
            msg_type=msg_type.value,
            content=content,
            metadata=metadata,
        ))
        seq += 1

    add_msg("goldie", MessageType.CREATE_WAVE,
            "Daily Standup",
            participants=list(AGENTS.keys()))

    add_msg("goldie", MessageType.BLIP,
            "Morning Gas Town! Quick round - what's everyone working on?")

    add_msg("case", MessageType.BLIP,
            "Yesterday: Fixed WebSocket reconnection. Today: Implementing OT sync. No blockers.")

    add_msg("molly", MessageType.BLIP,
            "Finished security audit. Starting on rate limiting implementation.")

    add_msg("deckard", MessageType.BLIP,
            "Running extended test suite. 47/50 passing. Investigating 3 flaky tests.")

    add_msg("samantha", MessageType.BLIP,
            "Completed architecture docs. Starting on API versioning strategy.")

    add_msg("kaylee", MessageType.BLIP,
            "Optimized Docker builds - 40% faster now. Looking at CI caching next.")

    add_msg("scotty", MessageType.BLIP,
            "Deployed staging. Production deploy scheduled for 14:00.")

    add_msg("wintermute", MessageType.BLIP,
            "Model training complete. Accuracy improved 2.3%. Deploying to eval.")

    add_msg("book", MessageType.BLIP,
            "Reviewed 5 PRs. All approved. Documentation looking good.")

    add_msg("uatu", MessageType.BLIP,
            "System healthy. 99.9% uptime this week. Memory usage stable.")

    add_msg("goldie", MessageType.CLOSE_WAVE,
            "Great updates everyone. Let's make it a productive day!")

    return SeedScenario(
        name="daily-standup",
        description="Daily standup meeting",
        wave_id=wave_id,
        created_at=base_time.isoformat(),
        messages=messages,
    )


SCENARIOS = {
    "sprint": generate_sprint_planning,
    "review": generate_code_review,
    "incident": generate_incident_response,
    "standup": generate_daily_standup,
}


# =============================================================================
# Output Formatters
# =============================================================================

def save_json(scenario: SeedScenario, output_path: Path):
    """Save scenario as JSON."""
    with open(output_path, "w") as f:
        json.dump(scenario.to_dict(), f, indent=2)
    print(f"Saved {len(scenario.messages)} messages to {output_path}")


def save_csv(scenario: SeedScenario, output_path: Path):
    """Save scenario as CSV."""
    if not scenario.messages:
        print("No messages to save")
        return

    fieldnames = ["wave_id", "sequence", "timestamp", "sender", "sender_email",
                  "msg_type", "content", "metadata"]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for msg in scenario.messages:
            row = msg.to_dict()
            row["metadata"] = json.dumps(row["metadata"])
            writer.writerow(row)

    print(f"Saved {len(scenario.messages)} messages to {output_path}")


def load_json(input_path: Path) -> SeedScenario:
    """Load scenario from JSON."""
    with open(input_path) as f:
        data = json.load(f)
    return SeedScenario.from_dict(data)


def load_csv(input_path: Path) -> SeedScenario:
    """Load scenario from CSV."""
    messages = []
    with open(input_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["sequence"] = int(row["sequence"])
            row["metadata"] = json.loads(row["metadata"])
            messages.append(SeedMessage.from_dict(row))

    if not messages:
        raise ValueError("No messages in CSV")

    return SeedScenario(
        name=input_path.stem,
        description=f"Loaded from {input_path}",
        wave_id=messages[0].wave_id,
        created_at=messages[0].timestamp,
        messages=messages,
    )


# =============================================================================
# Replay Engine
# =============================================================================

async def replay_to_server(scenario: SeedScenario, speed: float = 1.0,
                           server_url: str = WAVE_SERVER):
    """Replay messages to Wave server."""
    if not HAS_HTTPX:
        print("httpx required for replay. Install with: pip install httpx")
        return

    print(f"Replaying {len(scenario.messages)} messages to {server_url}")
    print(f"Wave: {scenario.wave_id}")
    print(f"Speed: {speed}x")
    print("-" * 60)

    async with httpx.AsyncClient() as client:
        prev_time = None

        for msg in scenario.messages:
            # Calculate delay based on timestamps
            msg_time = datetime.fromisoformat(msg.timestamp)
            if prev_time:
                delay = (msg_time - prev_time).total_seconds() / speed
                if delay > 0:
                    await asyncio.sleep(min(delay, 5.0))  # Cap at 5 seconds
            prev_time = msg_time

            # Display message
            agent = AGENTS.get(msg.sender)
            icon = agent.icon if agent else "👤"
            print(f"[{msg.timestamp[11:19]}] {icon} {msg.sender}: {msg.content[:60]}")

            # Submit to server
            try:
                payload = {
                    "wavelet_name": {
                        "wave_id": msg.wave_id,
                        "wavelet_id": f"{msg.wave_id.split('!')[0]}!conv+root"
                    },
                    "delta": {
                        "author": msg.sender_email,
                        "operations": [
                            {"type": "noOp"}  # Simplified - real impl would use docOps
                        ]
                    }
                }

                resp = await client.post(
                    f"{server_url}/api/waves/{msg.wave_id}/submit",
                    json=payload,
                    timeout=5.0
                )

                if resp.status_code != 200:
                    print(f"  Warning: Server returned {resp.status_code}")

            except Exception as e:
                print(f"  Error: {e}")

    print("-" * 60)
    print("Replay complete")


# =============================================================================
# CLI
# =============================================================================

def cmd_generate(args):
    """Generate seed data."""
    scenario_fn = SCENARIOS.get(args.scenario)
    if not scenario_fn:
        print(f"Unknown scenario: {args.scenario}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        return 1

    scenario = scenario_fn()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "json":
        save_json(scenario, output)
    elif args.format == "csv":
        save_csv(scenario, output)
    else:
        print(f"Unknown format: {args.format}")
        return 1

    return 0


def cmd_replay(args):
    """Replay seed data to server."""
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"File not found: {input_path}")
        return 1

    if input_path.suffix == ".json":
        scenario = load_json(input_path)
    elif input_path.suffix == ".csv":
        scenario = load_csv(input_path)
    else:
        print(f"Unknown file type: {input_path.suffix}")
        return 1

    asyncio.run(replay_to_server(scenario, speed=args.speed, server_url=args.server))
    return 0


def cmd_list(args):
    """List available scenarios."""
    print("Available scenarios:")
    print()
    for name, fn in SCENARIOS.items():
        scenario = fn()
        print(f"  {name:15} - {scenario.description} ({len(scenario.messages)} messages)")
    print()
    print("Generate with: python gastown-seed-generator.py generate --scenario <name>")


def cmd_preview(args):
    """Preview a scenario without saving."""
    scenario_fn = SCENARIOS.get(args.scenario)
    if not scenario_fn:
        print(f"Unknown scenario: {args.scenario}")
        return 1

    scenario = scenario_fn()
    print(f"Scenario: {scenario.name}")
    print(f"Wave ID: {scenario.wave_id}")
    print(f"Messages: {len(scenario.messages)}")
    print("-" * 60)

    for msg in scenario.messages:
        agent = AGENTS.get(msg.sender)
        icon = agent.icon if agent else "👤"
        print(f"[{msg.timestamp[11:19]}] {icon} {msg.sender}: {msg.content[:60]}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Gas Town Seed Generator - Generate and replay Wave messages"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate seed data")
    gen_parser.add_argument("--scenario", "-s", default="sprint",
                           choices=list(SCENARIOS.keys()),
                           help="Scenario to generate")
    gen_parser.add_argument("--format", "-f", default="json",
                           choices=["json", "csv"],
                           help="Output format")
    gen_parser.add_argument("--output", "-o", default="seeds/scenario.json",
                           help="Output file path")

    # Replay command
    replay_parser = subparsers.add_parser("replay", help="Replay seed data to server")
    replay_parser.add_argument("--input", "-i", required=True,
                              help="Input file (JSON or CSV)")
    replay_parser.add_argument("--speed", type=float, default=1.0,
                              help="Replay speed multiplier")
    replay_parser.add_argument("--server", default=WAVE_SERVER,
                              help="Wave server URL")

    # List command
    subparsers.add_parser("list", help="List available scenarios")

    # Preview command
    preview_parser = subparsers.add_parser("preview", help="Preview a scenario")
    preview_parser.add_argument("--scenario", "-s", default="sprint",
                               choices=list(SCENARIOS.keys()),
                               help="Scenario to preview")

    args = parser.parse_args()

    if args.command == "generate":
        return cmd_generate(args)
    elif args.command == "replay":
        return cmd_replay(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "preview":
        return cmd_preview(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
