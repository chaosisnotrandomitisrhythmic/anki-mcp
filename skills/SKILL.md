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

## Workflow

1. **Check connectivity**: Call `health` if this is the first card creation in the session
2. **Check for existing cards**: Use `search_notes` with relevant query to avoid duplicates
3. **Create cards**: Use `add_notes` with a list of NoteInput objects
4. **Sync**: Call `sync` after adding cards to push to AnkiWeb

## Card Quality Rules

1. Front should be a clear question — test recall, not recognition
2. Back should be concise but complete
3. One concept per card (atomic cards)
4. When creating cards from the current session, extract the most useful/reusable knowledge
5. If the user says "anki this" or "card this", create cards from what was just discussed

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

- Lowercase, hyphenated (e.g., `rails`, `pundit`, `prescient`, `pr-review`)
- Space-separated in Anki, list in the API
- Add context tags: topic + source (e.g., `["terraform", "aws", "session-review"]`)

## Example

When the user says "make flashcards about what we just discussed" about a Terraform session:

```python
add_notes(notes=[
    NoteInput(
        front="What does <code>terraform plan</code> do?",
        back="Shows what changes Terraform <b>would</b> make without applying them.<br>Compares desired state (config) with current state (state file).",
        tags=["terraform", "cli"],
        deck="DevOps::Terraform",
    ),
    NoteInput(
        front="How do you import an existing AWS resource into Terraform state?",
        back="<code>terraform import aws_instance.example i-1234567890abcdef0</code><br>Maps the resource address to the real infrastructure ID.",
        tags=["terraform", "aws", "state"],
        deck="DevOps::Terraform",
    ),
])
```

Then call `sync` to push to AnkiWeb.
