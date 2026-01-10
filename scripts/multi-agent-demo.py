#!/usr/bin/env python3
"""
Multi-Agent Wave Simulator Demo

Demonstrates 8 specialized agents coordinating work via Wave protocol.
Based on the Gas Town multi-agent architecture.

Usage:
    python scripts/multi-agent-demo.py [--live] [--scenario SCENARIO]

Scenarios:
    sprint    - Sprint planning with task assignment
    review    - Code review workflow
    incident  - Incident response coordination
    all       - Run all scenarios
"""

import asyncio
import json
import random
import argparse
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

WAVE_SERVER = "http://localhost:9898"

# Gas Town Agent Definitions
# Named after sci-fi/literature characters that match their roles
#
# Roles from Gas Town architecture:
#   Mayor     - Project coordinator, makes strategic decisions
#   Deacon    - Ethical oversight, ensures standards compliance
#   Witness   - Silent observer, audits and records everything
#   Polecats  - Specialized workers (the crew doing actual work)
#
# Character references:
#   Goldie Wilson   - Back to the Future mayor ("I'm gonna be somebody!")
#   Shepherd Book   - Firefly's moral compass
#   Uatu            - Marvel's Watcher, observes but doesn't interfere
#   Case            - Neuromancer's console cowboy (hacker)
#   Molly           - Neuromancer's street samurai (security)
#   Wintermute      - Neuromancer's AI (automation)
#   Deckard         - Blade Runner (QA, testing authenticity)
#   Samantha        - Her (2013) AI assistant (research)
#   Kaylee          - Firefly's mechanic (ops, keeps things running)
#   Scotty          - Star Trek's engineer (CI/CD, deployment)

@dataclass
class Agent:
    name: str
    fullname: str
    email: str
    role: str
    icon: str
    skills: List[str] = field(default_factory=list)

AGENTS = {
    # Leadership
    "goldie": Agent("goldie", "Goldie Wilson", "goldie@gastown.local",
                    "Mayor", "🎩", ["coordination", "planning", "strategy"]),
    "book": Agent("book", "Shepherd Book", "book@gastown.local",
                  "Deacon", "📖", ["ethics", "standards", "guidance"]),
    "uatu": Agent("uatu", "Uatu the Watcher", "uatu@gastown.local",
                  "Witness", "👁️", ["monitoring", "audit", "observation"]),

    # Polecats (specialized crew)
    "case": Agent("case", "Henry Case", "case@gastown.local",
                  "Console Cowboy", "👨‍💻", ["python", "automation", "worktrees"]),
    "molly": Agent("molly", "Molly Millions", "molly@gastown.local",
                   "Street Samurai", "🔒", ["security", "mcp", "audit"]),
    "deckard": Agent("deckard", "Rick Deckard", "deckard@gastown.local",
                     "Blade Runner", "🧪", ["testing", "pytest", "verification"]),
    "samantha": Agent("samantha", "Samantha OS1", "samantha@gastown.local",
                      "Research AI", "🏗️", ["architecture", "design", "analysis"]),
    "kaylee": Agent("kaylee", "Kaylee Frye", "kaylee@gastown.local",
                    "Ship Mechanic", "⚙️", ["ops", "workflow", "optimization"]),
    "scotty": Agent("scotty", "Montgomery Scott", "scotty@gastown.local",
                    "Chief Engineer", "🚀", ["ci", "cd", "deployment"]),
    "wintermute": Agent("wintermute", "Wintermute", "wintermute@gastown.local",
                        "AI Coordinator", "🤖", ["ml", "metrics", "evaluation"]),
}


class MessageType(Enum):
    CREATE_WAVE = "create_wave"
    BLIP = "blip"
    ADD_PARTICIPANT = "add_participant"
    TASK_ASSIGN = "task_assign"
    TASK_COMPLETE = "task_complete"
    BLOCKER = "blocker"
    RESOLVED = "resolved"
    CLOSE_WAVE = "close_wave"


@dataclass
class WaveMessage:
    sender: str
    msg_type: MessageType
    content: str
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class WaveSimulator:
    def __init__(self, live: bool = False, speed: float = 0.5):
        self.live = live
        self.speed = speed
        self.waves: Dict[str, List[WaveMessage]] = {}
        self.current_wave: Optional[str] = None
        
    def format_agent(self, name: str) -> str:
        agent = AGENTS.get(name)
        if agent:
            return f"{agent.icon} {agent.fullname}"
        return f"👤 {name}"
    
    def print_header(self, title: str):
        print()
        print("╔" + "═" * 78 + "╗")
        print(f"║{title:^78}║")
        print("╚" + "═" * 78 + "╝")
        print()
    
    def print_separator(self):
        print("─" * 80)
    
    async def send_message(self, msg: WaveMessage):
        """Send a message and display it."""
        ts = msg.timestamp.strftime("%H:%M:%S")
        sender = self.format_agent(msg.sender)
        
        if msg.msg_type == MessageType.CREATE_WAVE:
            self.print_separator()
            print(f"[{ts}] {sender} created wave: {msg.metadata.get('wave_id', 'unknown')}")
            print(f"         Title: {msg.content}")
            if 'participants' in msg.metadata:
                print(f"         Participants: {', '.join(msg.metadata['participants'])}")
            self.print_separator()
            
        elif msg.msg_type == MessageType.TASK_ASSIGN:
            assignee = self.format_agent(msg.metadata.get('assignee', 'unknown'))
            print(f"[{ts}] {sender} → {assignee}")
            print(f"         📋 Task: {msg.content}")
            if 'priority' in msg.metadata:
                print(f"         Priority: {msg.metadata['priority']}")
                
        elif msg.msg_type == MessageType.TASK_COMPLETE:
            print(f"[{ts}] {sender}: ✅ {msg.content}")
            
        elif msg.msg_type == MessageType.BLOCKER:
            print(f"[{ts}] {sender}: 🚨 BLOCKER: {msg.content}")
            
        elif msg.msg_type == MessageType.RESOLVED:
            print(f"[{ts}] {sender}: ✓ Resolved: {msg.content}")
            
        elif msg.msg_type == MessageType.CLOSE_WAVE:
            self.print_separator()
            print(f"[{ts}] {sender} closed wave")
            print(f"         Reason: {msg.content}")
            self.print_separator()
            
        else:  # BLIP
            content = msg.content
            if len(content) > 65:
                print(f"[{ts}] {sender}:")
                for i in range(0, len(content), 65):
                    print(f"         {content[i:i+65]}")
            else:
                print(f"[{ts}] {sender}: {content}")
        
        # Post to live server if enabled
        if self.live and HAS_HTTPX:
            await self._post_to_server(msg)
        
        await asyncio.sleep(self.speed)
    
    async def _post_to_server(self, msg: WaveMessage):
        """Post message to live Wave server."""
        try:
            async with httpx.AsyncClient() as client:
                wave_id = msg.metadata.get('wave_id', self.current_wave or 'demo!wave')
                agent = AGENTS.get(msg.sender)
                author = agent.email if agent else f"{msg.sender}@gastown.local"
                
                await client.post(
                    f"{WAVE_SERVER}/api/waves/{wave_id}/submit",
                    json={
                        "wavelet_name": {"wave_id": wave_id, "wavelet_id": wave_id},
                        "delta": {
                            "author": author,
                            "operations": [{"type": "noOp"}]
                        }
                    },
                    timeout=5.0
                )
        except Exception:
            pass  # Silent fail for demo
    
    async def run_scenario(self, name: str, messages: List[WaveMessage]):
        """Run a scenario."""
        self.print_header(f"Scenario: {name}")
        
        for msg in messages:
            await self.send_message(msg)
        
        print()


# Scenario definitions
def sprint_planning_scenario() -> List[WaveMessage]:
    """Sprint planning with Gas Town crew."""
    wave_id = f"gastown!sprint-{datetime.now().strftime('%Y%m%d')}"
    return [
        WaveMessage("goldie", MessageType.CREATE_WAVE,
                   "Sprint Planning - Wave Client Release",
                   {"wave_id": wave_id, "participants": list(AGENTS.keys())}),

        WaveMessage("goldie", MessageType.BLIP,
                   "Good morning Gas Town! Let's plan the wave-client-for-emacs release."),

        WaveMessage("goldie", MessageType.TASK_ASSIGN,
                   "Review OpenAPI spec changes for auth endpoints",
                   {"assignee": "molly", "priority": "P1"}),

        WaveMessage("molly", MessageType.BLIP,
                   "On it. Running security sweep for OWASP compliance."),

        WaveMessage("goldie", MessageType.TASK_ASSIGN,
                   "Run full integration test suite across 20 repos",
                   {"assignee": "deckard", "priority": "P1"}),

        WaveMessage("deckard", MessageType.BLIP,
                   "Starting Voigt-Kampff... I mean pytest matrix."),

        WaveMessage("goldie", MessageType.TASK_ASSIGN,
                   "Sync worktrees and check for stale branches",
                   {"assignee": "case", "priority": "P2"}),

        WaveMessage("case", MessageType.BLIP,
                   "Jacking into the matrix. Found 3 stale worktrees."),

        WaveMessage("uatu", MessageType.BLIP,
                   "📊 Sprint velocity: 42 points available, 38 committed."),

        WaveMessage("samantha", MessageType.BLIP,
                   "Architecture review: OT implementation looks solid. Minor concern about federation latency."),

        WaveMessage("molly", MessageType.TASK_COMPLETE,
                   "Auth endpoints secured. Added rate limiting recommendation."),

        WaveMessage("deckard", MessageType.BLOCKER,
                   "websockets 15.0.1 API changed. Tests are showing anomalies."),

        WaveMessage("case", MessageType.BLIP,
                   "I see the problem. Need to use ws.state instead of ws.open"),

        WaveMessage("deckard", MessageType.RESOLVED,
                   "Applied fix. All 32 tests confirm authentic behavior."),

        WaveMessage("scotty", MessageType.BLIP,
                   "Captain, the CI pipeline is green. Ready for deployment."),

        WaveMessage("book", MessageType.BLIP,
                   "Code review complete. The code walks a righteous path. 3 PRs approved."),

        WaveMessage("wintermute", MessageType.BLIP,
                   "Metrics analysis complete. Model accuracy: 94.2%"),

        WaveMessage("kaylee", MessageType.BLIP,
                   "Shiny! Workflow optimized. Reduced tmux sessions from 12 to 8."),

        WaveMessage("uatu", MessageType.BLIP,
                   "📋 All agents reported. The timeline is secure."),

        WaveMessage("goldie", MessageType.CLOSE_WAVE,
                   "Sprint planning complete. Remember: if you put your mind to it, you can accomplish anything!"),
    ]


def code_review_scenario() -> List[WaveMessage]:
    """Code review workflow with Gas Town crew."""
    wave_id = f"gastown!review-pr-{random.randint(100,999)}"
    return [
        WaveMessage("case", MessageType.CREATE_WAVE,
                   "PR #247: Add OAuth2 authentication endpoints",
                   {"wave_id": wave_id, "participants": ["case", "book", "molly", "uatu"]}),

        WaveMessage("case", MessageType.BLIP,
                   "Ready for review: specs/wave-api.openapi.yaml (+169 lines)"),

        WaveMessage("book", MessageType.BLIP,
                   "Let me examine this. The API must serve all users fairly."),

        WaveMessage("molly", MessageType.BLIP,
                   "Scanning auth endpoints for weaknesses."),

        WaveMessage("book", MessageType.BLIP,
                   "Line 295: Password example should be masked. 'secret' is a sin of exposure."),

        WaveMessage("case", MessageType.BLIP,
                   "Good catch. Flipping bits to '********'."),

        WaveMessage("molly", MessageType.BLOCKER,
                   "/auth/refresh missing request body schema. That's a hole."),

        WaveMessage("case", MessageType.BLIP,
                   "Adding RefreshTokenRequest schema. Patching the ICE."),

        WaveMessage("case", MessageType.RESOLVED,
                   "Added proper OAuth2 standard fields: access_token, expires_in, token_type."),

        WaveMessage("book", MessageType.TASK_COMPLETE,
                   "The code has found its path. OAuth2 RFC 6749 compliant."),

        WaveMessage("molly", MessageType.TASK_COMPLETE,
                   "Security sweep complete. No vulnerabilities. We're solid."),

        WaveMessage("uatu", MessageType.BLIP,
                   "📊 Review observed: 2 issues found, 2 resolved. Ready to merge."),

        WaveMessage("case", MessageType.CLOSE_WAVE,
                   "Merged to main. The matrix accepts our changes."),
    ]


def incident_response_scenario() -> List[WaveMessage]:
    """Incident response coordination with Gas Town crew."""
    wave_id = f"gastown!incident-{datetime.now().strftime('%H%M')}"
    return [
        WaveMessage("scotty", MessageType.CREATE_WAVE,
                   "🚨 INCIDENT: Production API returning 500 errors",
                   {"wave_id": wave_id, "participants": ["scotty", "case", "deckard", "kaylee", "goldie", "uatu"]}),

        WaveMessage("scotty", MessageType.BLIP,
                   "Captain, error rate spiked to 15% at 14:32 UTC. GET /api/waves/{id} affected."),

        WaveMessage("goldie", MessageType.BLIP,
                   "All hands! Case, jack in and check those logs!"),

        WaveMessage("case", MessageType.BLIP,
                   "Pulling logs from the matrix. Seeing TypeError in get_wave endpoint."),

        WaveMessage("deckard", MessageType.BLIP,
                   "Reproducing locally. Confirmed: doc_data is list, not dict. It's not what it appears to be."),

        WaveMessage("case", MessageType.BLIP,
                   "Found the glitch! Line 367 in wave_server.py assumes dict but gets list."),

        WaveMessage("case", MessageType.BLIP,
                   "Fix: Add isinstance(doc_data, dict) type check. Simple flatline recovery."),

        WaveMessage("kaylee", MessageType.BLIP,
                   "Got the old engine ready if we need to roll back. v0.1.9 is shiny."),

        WaveMessage("case", MessageType.TASK_COMPLETE,
                   "Fix committed: c9fe9b5. Hotfix jacked into production."),

        WaveMessage("scotty", MessageType.BLIP,
                   "She's holding together! Monitoring error rates."),

        WaveMessage("deckard", MessageType.BLIP,
                   "Error rate dropping: 15% → 2% → 0.1%. All clear."),

        WaveMessage("uatu", MessageType.BLIP,
                   "📊 Incident timeline: Detection 14:32, Fix 14:41, Resolution 14:45. MTTR: 13 minutes."),

        WaveMessage("goldie", MessageType.BLIP,
                   "Outstanding work, Gas Town! Remember: when this baby hits 88 mph... wait, wrong reference."),

        WaveMessage("scotty", MessageType.CLOSE_WAVE,
                   "Incident resolved. Root cause: incomplete type handling. I've given her all she's got!"),
    ]


async def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Wave Simulator Demo")
    parser.add_argument("--live", action="store_true", help="Post to live Wave server")
    parser.add_argument("--scenario", default="all", choices=["sprint", "review", "incident", "all"],
                       help="Scenario to run")
    parser.add_argument("--speed", type=float, default=0.4, help="Message delay in seconds")
    args = parser.parse_args()
    
    sim = WaveSimulator(live=args.live, speed=args.speed)
    
    # Check server if live mode
    if args.live:
        if not HAS_HTTPX:
            print("⚠ httpx not installed. Running in simulation mode.")
            sim.live = False
        else:
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"{WAVE_SERVER}/health", timeout=5.0)
                    if resp.status_code == 200:
                        print("✓ Wave server connected")
                    else:
                        print("⚠ Wave server not healthy. Running in simulation mode.")
                        sim.live = False
            except Exception:
                print("⚠ Wave server not running. Running in simulation mode.")
                sim.live = False
    
    scenarios = {
        "sprint": ("Sprint Planning", sprint_planning_scenario),
        "review": ("Code Review", code_review_scenario),
        "incident": ("Incident Response", incident_response_scenario),
    }
    
    if args.scenario == "all":
        for name, (title, scenario_fn) in scenarios.items():
            await sim.run_scenario(title, scenario_fn())
            print("\n" + "═" * 80 + "\n")
            await asyncio.sleep(1)
    else:
        title, scenario_fn = scenarios[args.scenario]
        await sim.run_scenario(title, scenario_fn())
    
    # Summary
    print()
    print("╔" + "═" * 78 + "╗")
    print(f"║{'Gas Town Simulation Complete':^78}║")
    print("╚" + "═" * 78 + "╝")
    print()
    print("Summary:")
    print(f"  • Gas Town crew: {len(AGENTS)} agents")
    print(f"  • Scenarios run: {'all (3)' if args.scenario == 'all' else '1'}")
    print(f"  • Live mode: {'enabled' if sim.live else 'simulation only'}")
    print()
    print("Gas Town Crew Roster:")
    print("  Leadership:")
    print("    🎩 Goldie Wilson (Mayor) - 'If you put your mind to it...'")
    print("    📖 Shepherd Book (Deacon) - Moral compass and code ethics")
    print("    👁️ Uatu the Watcher (Witness) - Observes all, records everything")
    print("  Polecats:")
    print("    👨‍💻 Henry Case - Console cowboy, code automation")
    print("    🔒 Molly Millions - Security specialist, street samurai")
    print("    🧪 Rick Deckard - QA blade runner, verifies authenticity")
    print("    🏗️ Samantha OS1 - Research AI, architecture")
    print("    ⚙️ Kaylee Frye - Ops mechanic, keeps it shiny")
    print("    🚀 Montgomery Scott - CI/CD engineer, deployment")
    print("    🤖 Wintermute - AI metrics and evaluation")
    print()
    print("Wave protocol enables real-time collaboration between autonomous agents.")
    print("Each agent has specialized skills and contributes to the collective workflow.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
