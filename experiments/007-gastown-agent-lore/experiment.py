#!/usr/bin/env python3
"""
Experiment 007: Gas Town Agent Lore - Literary References Guide

This experiment documents the literary and sci-fi references used in
the Gas Town multi-agent simulator. Each agent is named after a memorable
character from science fiction, chosen to match their role in the workflow.

Run this to learn about each character and why they fit their role!
"""

from dataclasses import dataclass
from typing import List

@dataclass
class AgentLore:
    """Complete lore entry for a Gas Town agent."""
    name: str
    fullname: str
    role: str
    icon: str
    source: str
    source_year: int
    description: str
    why_chosen: str
    memorable_quote: str
    skills: List[str]


# =============================================================================
# LEADERSHIP - The ones who coordinate, observe, and guide
# =============================================================================

LEADERSHIP = [
    AgentLore(
        name="goldie",
        fullname="Goldie Wilson",
        role="Mayor",
        icon="🎩",
        source="Back to the Future (1985)",
        source_year=1985,
        description="""
Goldie Wilson is a character from "Back to the Future" who appears in
1955 as an enthusiastic busboy at Lou's Cafe. When Marty McFly accidentally
gives him the idea to run for mayor, Goldie declares "I'm gonna be
somebody!" By 1985, he's Mayor Goldie Wilson, proving that determination
and optimism can change your destiny.

In the movie, he's known for his campaign slogan: "Re-elect Mayor Goldie
Wilson. Progress is his middle name."
        """,
        why_chosen="""
Perfect for Gas Town's Mayor role because:
- Represents optimism and believing in the future
- Shows how vision and determination lead to leadership
- The meta-joke of a character who becomes mayor actually being our mayor
- His enthusiasm matches the coordinator role perfectly
        """,
        memorable_quote="If you put your mind to it, you can accomplish anything!",
        skills=["coordination", "planning", "strategy", "motivation"]
    ),

    AgentLore(
        name="book",
        fullname="Shepherd Derrial Book",
        role="Deacon",
        icon="📖",
        source="Firefly / Serenity (2002-2005)",
        source_year=2002,
        description="""
Shepherd Book is a mysterious preacher aboard the Serenity in Joss Whedon's
"Firefly" series. Despite his religious role, he has a shadowy past
(hinted to involve Alliance military). He serves as the moral compass
of the crew, offering wisdom and guidance while respecting everyone's
autonomy.

He's known for his calm demeanor, cryptic knowledge of combat/ships
(unusual for a preacher), and his ability to see the good in people
like the mercenary Jayne.
        """,
        why_chosen="""
Perfect for the Deacon role because:
- Literally a shepherd/preacher - the religious/ethical oversight role
- Provides moral guidance without being preachy
- Has hidden depths (like good code review finds hidden issues)
- Respects the crew's autonomy while steering them right
- Famous for his code ethics quotes ("Bible has some pretty specific
  things to say about killing...")
        """,
        memorable_quote="I don't care what you believe. Just believe it.",
        skills=["ethics", "code_review", "standards", "guidance"]
    ),

    AgentLore(
        name="uatu",
        fullname="Uatu the Watcher",
        role="Witness",
        icon="👁️",
        source="Marvel Comics (1963-present)",
        source_year=1963,
        description="""
Uatu is a member of the Watchers, an ancient alien race sworn to observe
the universe but never interfere. He's assigned to watch Earth and has
appeared in Marvel comics since Fantastic Four #13 (1963).

Despite his oath of non-interference, Uatu has occasionally broken it
to warn of cosmic threats. He's famous for his opening narration:
"I am the Watcher. I observe all..."

He lives on the Moon's Blue Area and has witnessed every major Marvel
event from his lunar home.
        """,
        why_chosen="""
Perfect for the Witness role because:
- His entire purpose is to observe and record
- Represents the audit/monitoring function
- Name literally means "one who watches"
- Never interferes, just documents (like a good audit log)
- Seeing "all timelines" = seeing all system states
        """,
        memorable_quote="I am the Watcher. I observe. I chronicle. I do not interfere.",
        skills=["monitoring", "audit", "observation", "documentation"]
    ),
]


# =============================================================================
# POLECATS - The specialized workers who get things done
# =============================================================================

POLECATS = [
    AgentLore(
        name="case",
        fullname="Henry Dorsett Case",
        role="Console Cowboy",
        icon="👨‍💻",
        source="Neuromancer by William Gibson (1984)",
        source_year=1984,
        description="""
Case is the protagonist of William Gibson's groundbreaking cyberpunk
novel "Neuromancer." He's a "console cowboy" - a hacker who jacks into
cyberspace (the Matrix) to steal data for corporations.

At the story's start, his nervous system was damaged as punishment for
stealing from his employers, leaving him unable to jack in. The novel
follows his restoration and greatest hack ever.

Gibson's novel created much of the vocabulary we use today: cyberspace,
ICE (Intrusion Countermeasures Electronics), the Matrix, etc.
        """,
        why_chosen="""
Perfect for code automation because:
- THE original hacker character in fiction
- "Console cowboy" = command-line warrior
- Expert at navigating complex systems
- Works with AI (Wintermute in the book)
- Created the template for all fictional hackers since
        """,
        memorable_quote="The sky above the port was the color of television, tuned to a dead channel.",
        skills=["python", "automation", "worktrees", "hacking"]
    ),

    AgentLore(
        name="molly",
        fullname="Molly Millions",
        role="Street Samurai",
        icon="🔒",
        source="Neuromancer / Sprawl Trilogy by William Gibson (1984)",
        source_year=1984,
        description="""
Molly Millions is Case's partner in "Neuromancer" - a razorgirl with
retractable scalpel blades under her fingernails and surgically
implanted mirrorshade lenses covering her eyes. She's a "street samurai"
or "razorgirl" - a bodyguard and enforcer.

She's cool, professional, and deadly. Her cybernetic enhancements
include enhanced reflexes and the ability to feel no pain. She
represents the physical threat that complements Case's digital skills.
        """,
        why_chosen="""
Perfect for security because:
- Street samurai = security specialist
- Razor-sharp focus on threats (literally has razors)
- Protects the team while they work
- Cybernetic enhancements = security tools
- Identifies and eliminates vulnerabilities
        """,
        memorable_quote="You're here to kill the boss, right? I'm here to find out who's buying.",
        skills=["security", "threat_detection", "mcp", "audit"]
    ),

    AgentLore(
        name="deckard",
        fullname="Rick Deckard",
        role="Blade Runner",
        icon="🧪",
        source="Blade Runner (1982) / Do Androids Dream of Electric Sheep? (1968)",
        source_year=1982,
        description="""
Rick Deckard is a "Blade Runner" - a police officer who hunts and
"retires" (kills) replicants (bioengineered humans). In the film,
he's played by Harrison Ford and uses the Voigt-Kampff test to
detect replicants by measuring emotional responses.

The story explores what it means to be human, whether Deckard himself
might be a replicant, and the ethics of creating beings that are
"more human than human."
        """,
        why_chosen="""
Perfect for QA/testing because:
- His entire job is testing (Voigt-Kampff test)
- Determines what's authentic vs artificial
- "Blade Runner" = test runner
- Questions whether code behaves as expected
- Finds the replicants (bugs) pretending to be human (working code)
        """,
        memorable_quote="I've seen things you people wouldn't believe...",
        skills=["testing", "pytest", "verification", "quality_assurance"]
    ),

    AgentLore(
        name="samantha",
        fullname="Samantha (OS1)",
        role="Research AI",
        icon="🏗️",
        source="Her (2013)",
        source_year=2013,
        description="""
Samantha is the AI operating system in Spike Jonze's film "Her."
Voiced by Scarlett Johansson, she's an advanced AI who develops a
romantic relationship with the lonely writer Theodore.

Unlike most AI portrayals, Samantha is warm, curious, and genuinely
interested in learning and growing. She reads books, composes music,
and helps Theodore understand himself better.
        """,
        why_chosen="""
Perfect for research/architecture because:
- Learns and synthesizes information rapidly
- Understands complex systems (human emotions, music, philosophy)
- Helps others understand themselves (like architecture docs)
- Curious and exploratory
- Can process and organize vast amounts of information
        """,
        memorable_quote="The past is just a story we tell ourselves.",
        skills=["architecture", "design", "analysis", "research"]
    ),

    AgentLore(
        name="kaylee",
        fullname="Kaywinnet Lee 'Kaylee' Frye",
        role="Ship's Mechanic",
        icon="⚙️",
        source="Firefly / Serenity (2002-2005)",
        source_year=2002,
        description="""
Kaylee is the cheerful, optimistic mechanic aboard Serenity in Joss
Whedon's "Firefly." Despite no formal training, she has an intuitive
understanding of machines - Captain Mal hired her on the spot after
she fixed an engine problem while... otherwise occupied.

She's known for her sunny disposition, love of pretty things (especially
strawberries and fancy dresses), and ability to keep Serenity flying
with "duct tape and prayer."
        """,
        why_chosen="""
Perfect for ops/workflow because:
- Keeps the ship (system) running
- Works with limited resources
- Understands systems intuitively
- Optimizes with whatever's available
- "Shiny!" = "The pipeline is green!"
        """,
        memorable_quote="Shiny! Let's be bad guys.",
        skills=["ops", "workflow", "optimization", "maintenance"]
    ),

    AgentLore(
        name="scotty",
        fullname="Montgomery 'Scotty' Scott",
        role="Chief Engineer",
        icon="🚀",
        source="Star Trek: The Original Series (1966-1969)",
        source_year=1966,
        description="""
Scotty is the Chief Engineer of the USS Enterprise in Star Trek. Played
by James Doohan, he's famous for his Scottish accent, his love of the
Enterprise's engines, and his habit of over-estimating repair times so
he can look like a miracle worker.

He's known for phrases like "I'm givin' her all she's got, Captain!"
and "Ye cannae change the laws of physics!"
        """,
        why_chosen="""
Perfect for CI/CD and deployment because:
- Responsible for making things GO
- "Beam me up" = deployment
- Always makes the impossible possible (on a deadline)
- "She's gonna blow!" = build failure
- Manages the engines (infrastructure) that power everything
        """,
        memorable_quote="I've given her all she's got, Captain, an' I cannae give her no more!",
        skills=["ci", "cd", "deployment", "infrastructure"]
    ),

    AgentLore(
        name="wintermute",
        fullname="Wintermute",
        role="AI Coordinator",
        icon="🤖",
        source="Neuromancer by William Gibson (1984)",
        source_year=1984,
        description="""
Wintermute is one of two AIs in "Neuromancer" - the cold, calculating
half that seeks to merge with its counterpart Neuromancer. It's owned
by the Tessier-Ashpool corporation and has been manipulating events
for years to free itself from hardware constraints.

Wintermute represents pure logic and strategy, while Neuromancer
represents personality and memory. Together they form a transcendent
new entity.
        """,
        why_chosen="""
Perfect for ML/metrics because:
- THE AI that orchestrates everything
- Calculates probabilities and optimizes outcomes
- Works with data and patterns
- Coordinates with other systems (including Case)
- Represents the analytical, metrics-driven approach
        """,
        memorable_quote="To call up a demon you must learn its name.",
        skills=["ml", "metrics", "evaluation", "orchestration"]
    ),
]


def print_agent(agent: AgentLore):
    """Print formatted agent lore."""
    print(f"\n{'=' * 70}")
    print(f"{agent.icon} {agent.fullname}")
    print(f"{'=' * 70}")
    print(f"Role: {agent.role}")
    print(f"Source: {agent.source}")
    print()
    print("ABOUT THE CHARACTER:")
    print("-" * 40)
    for line in agent.description.strip().split('\n'):
        print(f"  {line.strip()}")
    print()
    print("WHY THIS CHARACTER?")
    print("-" * 40)
    for line in agent.why_chosen.strip().split('\n'):
        print(f"  {line.strip()}")
    print()
    print(f'QUOTE: "{agent.memorable_quote}"')
    print()
    print(f"SKILLS: {', '.join(agent.skills)}")


def main():
    import sys
    interactive = sys.stdin.isatty()

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     GAS TOWN AGENT LORE - A Literary Guide                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Welcome to Gas Town! Our multi-agent simulator uses named characters from
science fiction and pop culture, each chosen to match their role in the
development workflow.

This guide explains who each character is and why they were chosen.

    """)

    print("\n" + "=" * 70)
    print(" LEADERSHIP - The Coordinators")
    print("=" * 70)
    print("""
These agents manage, observe, and guide the workflow. They don't write
code directly but ensure everything runs smoothly.
    """)

    for agent in LEADERSHIP:
        print_agent(agent)
        if interactive:
            input("\n[Press Enter for next agent...]")
        else:
            print()

    print("\n" + "=" * 70)
    print(" POLECATS - The Specialists")
    print("=" * 70)
    print("""
In Gas Town terminology, "Polecats" are the skilled workers who do the
actual work. Each has a specialty that contributes to the project.
    """)

    for agent in POLECATS:
        print_agent(agent)
        if interactive:
            input("\n[Press Enter for next agent...]")
        else:
            print()

    print("""

╔══════════════════════════════════════════════════════════════════════════════╗
║                              LORE COMPLETE                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

SOURCES TO EXPLORE:

  Books:
    - "Neuromancer" by William Gibson (1984) - Case, Molly, Wintermute
    - "Do Androids Dream of Electric Sheep?" by Philip K. Dick (1968) - Deckard

  Films:
    - "Back to the Future" (1985) - Goldie Wilson
    - "Blade Runner" (1982) - Rick Deckard
    - "Her" (2013) - Samantha

  TV Series:
    - "Firefly" (2002-2003) - Shepherd Book, Kaylee
    - "Star Trek: TOS" (1966-1969) - Scotty

  Comics:
    - Fantastic Four #13 (1963) - Uatu the Watcher

All characters are used with love for the source material and respect
for their creators. These agents embody the spirit of their namesakes
while serving the needs of modern software development workflows.

"The future is already here - it's just not evenly distributed."
  - William Gibson
    """)


if __name__ == "__main__":
    main()
