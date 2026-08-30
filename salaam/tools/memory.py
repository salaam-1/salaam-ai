"""
Memory tools — remembered facts, notes and reminders that survive restarts.

This is what makes Salaam feel like an assistant rather than a search box:
it can be told something once and recall it a week later.
"""

from __future__ import annotations

from datetime import datetime, timezone

from salaam import store

FACTS = "facts"
NOTES = "notes"
REMINDERS = "reminders"


def _parse_when(value: str) -> datetime | None:
    """Accept ISO-ish datetimes without being fussy about the exact shape."""
    text = (value or "").strip().replace("Z", "+00:00").replace("T", " ")
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[: len(pattern) + 4], pattern)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def register(mcp):

    # -- Facts ------------------------------------------------------------

    @mcp.tool()
    def remember(fact: str, tag: str = "general") -> str:
        """
        Store a fact about the user so it can be recalled in future sessions.
        Use whenever the user shares a preference, name, plan or detail worth
        keeping — "my sister's birthday is 3 March", "I support Arsenal".
        """
        text = fact.strip()
        if not text:
            return "There's nothing to remember — give me the fact."

        existing = store.load(FACTS)
        if any(row["fact"].lower() == text.lower() for row in existing):
            return f'Already noted: "{text}"'

        row = store.append(FACTS, {"fact": text, "tag": tag.strip().lower() or "general"})
        return f'Noted (#{row["id"]}): "{text}"'

    @mcp.tool()
    def recall(query: str = "") -> str:
        """
        Retrieve stored facts about the user. Leave the query empty to list
        everything, or pass a keyword/tag to filter.
        """
        rows = store.load(FACTS)
        if not rows:
            return "I haven't been told anything to remember yet."

        needle = query.strip().lower()
        if needle:
            rows = [
                row
                for row in rows
                if needle in row["fact"].lower() or needle == row.get("tag")
            ]
            if not rows:
                return f'Nothing stored matching "{query}".'

        lines = ["### What I remember"]
        for row in rows:
            lines.append(f"- (#{row['id']}) [{row.get('tag', 'general')}] {row['fact']}")
        return "\n".join(lines)

    @mcp.tool()
    def forget(fact_id: int) -> str:
        """Delete one stored fact by its id (shown by recall)."""
        removed = store.remove(FACTS, fact_id)
        if not removed:
            return f"No stored fact with id {fact_id}."
        return f'Forgotten: "{removed["fact"]}"'

    # -- Notes ------------------------------------------------------------

    @mcp.tool()
    def save_note(content: str, title: str = "") -> str:
        """
        Save a longer note, idea or piece of text for later.
        Use for anything the user dictates and wants kept.
        """
        text = content.strip()
        if not text:
            return "The note is empty."
        row = store.append(
            NOTES, {"title": title.strip() or text[:48], "content": text}
        )
        return f'Saved note #{row["id"]}: "{row["title"]}"'

    @mcp.tool()
    def list_notes(query: str = "") -> str:
        """List saved notes, optionally filtered by a keyword."""
        rows = store.load(NOTES)
        needle = query.strip().lower()
        if needle:
            rows = [
                row
                for row in rows
                if needle in row["title"].lower() or needle in row["content"].lower()
            ]
        if not rows:
            return "No notes found." if needle else "You have no saved notes."

        lines = ["### Notes"]
        for row in rows:
            when = row.get("created_at", "")[:10]
            lines.append(f"- (#{row['id']}) **{row['title']}** — {when}")
            lines.append(f"  {row['content'][:200]}")
        return "\n".join(lines)

    @mcp.tool()
    def delete_note(note_id: int) -> str:
        """Delete a saved note by its id."""
        removed = store.remove(NOTES, note_id)
        if not removed:
            return f"No note with id {note_id}."
        return f'Deleted note "{removed["title"]}".'

    # -- Reminders --------------------------------------------------------

    @mcp.tool()
    def add_reminder(text: str, when: str = "") -> str:
        """
        Add a reminder or to-do item.

        Args:
            text: what to be reminded about.
            when: optional due time as "YYYY-MM-DD HH:MM" or "YYYY-MM-DD".
        """
        body = text.strip()
        if not body:
            return "What should I remind you about?"

        due = None
        if when.strip():
            parsed = _parse_when(when)
            if not parsed:
                return f'I couldn\'t read "{when}" as a date. Use "YYYY-MM-DD HH:MM".'
            due = parsed.isoformat(timespec="minutes")

        row = store.append(REMINDERS, {"text": body, "due": due, "done": False})
        due_text = f" for {due.replace('T', ' ')}" if due else ""
        return f'Reminder #{row["id"]} set{due_text}: "{body}"'

    @mcp.tool()
    def list_reminders(include_done: bool = False) -> str:
        """List reminders, soonest first. Overdue items are flagged."""
        rows = store.load(REMINDERS)
        if not include_done:
            rows = [row for row in rows if not row.get("done")]
        if not rows:
            return "You have no pending reminders."

        rows.sort(key=lambda row: row.get("due") or "9999")
        now = datetime.now().isoformat(timespec="minutes")

        lines = ["### Reminders"]
        for row in rows:
            marks = []
            if row.get("done"):
                marks.append("done")
            elif row.get("due") and row["due"] < now:
                marks.append("OVERDUE")
            due_text = f" — due {row['due'].replace('T', ' ')}" if row.get("due") else ""
            flag = f" [{', '.join(marks)}]" if marks else ""
            lines.append(f"- (#{row['id']}) {row['text']}{due_text}{flag}")
        return "\n".join(lines)

    @mcp.tool()
    def complete_reminder(reminder_id: int) -> str:
        """Mark a reminder as done."""
        updated = store.update(
            REMINDERS, reminder_id, done=True, completed_at=store.now_iso()
        )
        if not updated:
            return f"No reminder with id {reminder_id}."
        return f'Marked done: "{updated["text"]}"'

    @mcp.tool()
    def due_reminders() -> str:
        """
        Reminders that are due now or overdue. Use this proactively at the
        start of a conversation or inside a briefing.
        """
        now = datetime.now().isoformat(timespec="minutes")
        rows = [
            row
            for row in store.load(REMINDERS)
            if not row.get("done") and row.get("due") and row["due"] <= now
        ]
        if not rows:
            return "Nothing is due right now."

        lines = ["### Due now"]
        for row in sorted(rows, key=lambda row: row["due"]):
            lines.append(f"- (#{row['id']}) {row['text']} (due {row['due'].replace('T', ' ')})")
        return "\n".join(lines)
