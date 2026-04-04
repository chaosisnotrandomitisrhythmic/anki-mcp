---
name: anki
description: Use when the user asks to "create anki cards", "make flashcards", "add to anki", or wants to save something they learned as spaced repetition cards.
---

# Anki Card Creator

Create Anki flashcards directly via the anki MCP server (AnkiConnect).

## Prerequisites

- Anki desktop must be running
- AnkiConnect addon installed (addon code `2055492159`)
- Run `health` tool first if unsure about connectivity

## Routing

Check the ARGUMENTS passed to this skill:

- **`extract`** → Follow the **Extract Workflow** below
- **`progress`** → Call the `progress` MCP tool and present results
- **Anything else / no args** → Follow the **Manual Card Creation Workflow**

---

## Extract Workflow

**Trigger**: `/anki extract` — scans the full conversation, finds extractable knowledge, deduplicates against existing cards, proposes a batch of new cards and updates, then creates them after user approval.

### Principle: Knowledge Graph, Not Knowledge Dump

Each card is a **unique node** in a knowledge graph. Never duplicate — instead:
- If a concept already has a card, **update it** or create a **follow-up card** that builds on it
- Use tags to connect related concepts across decks
- Ask "next level" questions that deepen understanding rather than restating basics

### Step 1: Gather Context (parallel)

Run these in parallel:
1. `list_decks` — get existing deck structure
2. `search_notes` with broad queries covering the session's main topics (e.g., `tag:terraform`, `deck:Delphi`, keywords from discussion) — get existing cards in relevant areas. Run multiple searches to cover all topics discussed.

### Step 2: Analyze the Conversation

Scan the **full conversation** for extractable knowledge. Look for:

| Signal | Priority | Example |
|--------|----------|---------|
| Struggled to understand | Highest | Concept explained multiple times, user asked follow-ups |
| Aha moment | High | "Oh, so that's why..." / "I see" / sudden understanding |
| Debugging insight | High | Root cause found after investigation |
| Follow-up question | Medium | Something discussed but not fully resolved |
| Useful pattern | Medium | Workflow, command, architecture pattern worth remembering |
| Factual knowledge | Lower | Definitions, syntax, config values |

**Skip**: things the user clearly already knows, trivial operations, session-specific details (file paths, variable names) that won't generalize.

### Step 3: Deduplicate and Place

For each candidate card:
1. **Check against existing cards** from Step 1 — does this concept already exist?
   - If yes and the existing card is **incomplete**: propose an **update** (show old → new)
   - If yes and the existing card is **adequate**: skip it
   - If no: propose a **new card**
2. **Choose deck**: slot into existing deck hierarchy. Only propose a new deck if nothing fits.
3. **Choose tags**: reuse existing tags where possible. Add new tags only when they represent a genuinely new topic.

### Step 4: Present Batch for Approval

Present all proposed cards in a single batch. Format:

```
## Proposed Anki Cards

### New Cards (N)

**1. [Deck::Subdeck]** `tag1` `tag2`
> **Q**: What does X do?
> **A**: It does Y because Z.

**2. [Deck::Subdeck]** `tag1` `tag3`
> **Q**: Why does A happen when B?
> **A**: Because C — the key insight is D.

### Updates (M)

**1. Update note ID 12345** [Deck]
> **Before**: Old back content...
> **After**: Improved back content with new insight...

### Skipped (K duplicates found)
- "concept X" — already covered by note 12345
- "concept Y" — already covered by note 67890

---
Create these? (or tell me what to change)
```

### Step 5: Create and Sync

After user approves (or after applying requested changes):
1. `add_notes` for new cards
2. `update_note` for each update
3. `sync` to push to AnkiWeb

---

## Manual Card Creation Workflow

1. **Check connectivity**: Call `health` if this is the first card creation in the session
2. **Check for existing cards**: Use `search_notes` with relevant query to avoid duplicates
3. **Create cards**: Use `add_notes` with a list of NoteInput objects
4. **Sync**: Call `sync` after adding cards to push to AnkiWeb

---

## Card Quality Rules

1. Front should be a clear question — test **recall**, not recognition
2. Back should be concise but complete
3. One concept per card (atomic cards)
4. Prefer "why" and "how" questions over "what" — they test deeper understanding
5. For debugging insights: front = the symptom/error, back = root cause + fix
6. For patterns: front = "when should you use X?", back = the decision criteria

## Card Formatting

Use HTML in front/back fields:
- `<kbd>key</kbd>` for keyboard keys and shortcuts
- `<code>command</code>` for CLI commands, code snippets, function names
- `<b>term</b>` for emphasis and key terms
- `<br>` for line breaks
- `<ul><li>...</li></ul>` for lists

## Deck Conventions

- Use descriptive deck names with `::` hierarchy (e.g., `AWS::IAM`, `Neovim::Keybindings`)
- Check existing decks with `list_decks` before creating new ones
- Default deck is "Default" — always specify a meaningful deck name

## Tag Conventions

- Lowercase, hyphenated (e.g., `rails`, `python`, `algorithms`, `pr-review`)
- Space-separated in Anki, list in the API
- Add context tags: topic + source (e.g., `["terraform", "aws", "session-review"]`)
- Add `session-extract` tag to all cards created via the extract workflow

## Example (Manual)

```python
add_notes(notes=[
    NoteInput(
        front="What does <code>terraform plan</code> do?",
        back="Shows what changes Terraform <b>would</b> make without applying them.<br>Compares desired state (config) with current state (state file).",
        tags=["terraform", "cli"],
        deck="DevOps::Terraform",
    ),
])
```

Then call `sync` to push to AnkiWeb.
