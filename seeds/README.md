# Gas Town Seed Data

Pre-generated Wave message scenarios for testing and demos.

## Files

| File | Scenario | Messages | Description |
|------|----------|----------|-------------|
| `sprint-planning.json` | Sprint Planning | 20 | Full Gas Town crew planning a release |
| `code-review.json` | Code Review | 13 | PR review with Case, Book, Molly, Uatu |
| `incident-response.json` | Incident | 14 | Production 500 error response |
| `daily-standup.json` | Standup | 12 | Quick morning sync |
| `sprint-planning.csv` | Sprint Planning | 20 | CSV format example |

## Usage

### Generate new seed data

```bash
# List available scenarios
python scripts/gastown-seed-generator.py list

# Generate JSON
python scripts/gastown-seed-generator.py generate --scenario sprint --output seeds/my-sprint.json

# Generate CSV
python scripts/gastown-seed-generator.py generate --scenario review --format csv --output seeds/my-review.csv

# Preview without saving
python scripts/gastown-seed-generator.py preview --scenario incident
```

### Replay to Wave server

```bash
# Start the server first
make server

# Replay at normal speed
python scripts/gastown-seed-generator.py replay --input seeds/sprint-planning.json

# Replay at 2x speed
python scripts/gastown-seed-generator.py replay --input seeds/daily-standup.json --speed 2.0

# Replay to different server
python scripts/gastown-seed-generator.py replay --input seeds/incident-response.json --server http://localhost:9999
```

## JSON Format

```json
{
  "name": "sprint-planning",
  "description": "Sprint planning session with full Gas Town crew",
  "wave_id": "gastown!sprint-20260110",
  "created_at": "2026-01-10T09:00:00",
  "message_count": 20,
  "messages": [
    {
      "wave_id": "gastown!sprint-20260110",
      "sequence": 0,
      "timestamp": "2026-01-10T09:00:30",
      "sender": "goldie",
      "sender_email": "goldie@gastown.local",
      "msg_type": "create_wave",
      "content": "Sprint Planning - Wave Client Release",
      "metadata": {"participants": ["goldie", "book", ...]}
    }
  ]
}
```

## Gas Town Crew

| Agent | Role | Source |
|-------|------|--------|
| 🎩 Goldie Wilson | Mayor | Back to the Future |
| 📖 Shepherd Book | Deacon | Firefly |
| 👁️ Uatu | Witness | Marvel Comics |
| 👨‍💻 Henry Case | Console Cowboy | Neuromancer |
| 🔒 Molly Millions | Street Samurai | Neuromancer |
| 🧪 Rick Deckard | Blade Runner | Blade Runner |
| 🏗️ Samantha OS1 | Research AI | Her |
| ⚙️ Kaylee Frye | Mechanic | Firefly |
| 🚀 Montgomery Scott | Engineer | Star Trek |
| 🤖 Wintermute | AI | Neuromancer |
