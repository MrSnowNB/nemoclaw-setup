import sqlite3
import json
import asyncio
import ollama
from pathlib import Path
from typing import List, Dict, Optional

DB = Path('/home/mr-snow/alice_cyberland/project/data/cyberland.db')


def extract_facts(user_msg: str, response: str) -> dict:
    prompt = f"""
Extract facts about the user from the following message and response.
Output JSON only with these exact keys: "name" (string, user's name if \
mentioned, else null), "facts" (list of strings, e.g. "has a dog named \
Biscuit", etc.), "tone" (string, the general user tone), "summary_worthy" \
(boolean).
User Message: {user_msg}
Agent Response: {response}
"""
    try:
        resp = ollama.chat(
            model="gemma3:270m",
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"num_predict": 512, "temperature": 0.0}
        )
        content = resp['message']['content'].strip()
        data = json.loads(content)
        # Ensure correct types
        return {
            "name": data.get("name", None),
            "facts": data.get("facts", []),
            "tone": data.get("tone", ""),
            "summary_worthy": bool(data.get("summary_worthy", False))
        }
    except Exception as e:
        print(f"Extraction error: {e}")
        return {"name": None, "facts": [], "tone": "", "summary_worthy": False}


def db_upsert_relationship(user_id: str, extracted: dict) -> None:
    if not extracted.get("name") and not extracted.get("facts"):
        return

    with sqlite3.connect(DB) as c:
        row = c.execute(
            "SELECT name, facts FROM relationships WHERE user_id=?",
            (user_id,)
        ).fetchone()

        name = extracted.get("name")
        new_facts = extracted.get("facts", [])
        if not isinstance(new_facts, list):
            new_facts = [new_facts]

        if row:
            db_name, db_facts_str = row
            if not name:
                name = db_name
            try:
                db_facts = json.loads(db_facts_str) if db_facts_str else []
            except json.JSONDecodeError:
                db_facts = []

            # Merge facts avoiding duplicates
            for f in new_facts:
                if f not in db_facts:
                    db_facts.append(f)

            c.execute("""
                UPDATE relationships
                SET name=?, facts=?
                WHERE user_id=?
            """, (name, json.dumps(db_facts), user_id))
        else:
            c.execute("""
                INSERT INTO relationships (user_id, name, facts, summary)
                VALUES (?, ?, ?, '')
            """, (user_id, name, json.dumps(new_facts)))


def db_append_hop_fields(
    hop_id: Optional[int], extracted: dict, flags: list
) -> None:
    if hop_id is None:
        with sqlite3.connect(DB) as c:
            row = c.execute(
                "SELECT id FROM hop ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                hop_id = row[0]
            else:
                return

    with sqlite3.connect(DB) as c:
        c.execute("""
            UPDATE hop
            SET extracted=?, tone=?, flags=?
            WHERE id=?
        """, (
            json.dumps(extracted),
            extracted.get("tone", ""),
            json.dumps(flags),
            hop_id
        ))


async def precompact_summarize(
    prior_messages: List[Dict[str, str]], user_id: str
) -> str:
    history_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in prior_messages
    )
    prompt = (
        f"Summarize the following conversation history into a concise context "
        f"block for an AI agent. Make it highly condensed.\n\n{history_text}"
    )

    try:
        content = await asyncio.to_thread(
            ollama.chat,
            model="gemma3:270m",
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 512, "temperature": 0.0}
        )
        summary = content['message']['content'].strip()

        # Word count check
        words = summary.split()
        if len(words) < 20 or len(words) > 200:
            summary = "Prior conversation summarized due to length."
    except Exception as e:
        print(f"Summarize error: {e}")
        summary = "Prior conversation summarized due to error."

    with sqlite3.connect(DB) as c:
        row = c.execute(
            "SELECT user_id FROM relationships WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if not row:
            c.execute(
                "INSERT INTO relationships (user_id, name, facts, summary) "
                "VALUES (?, NULL, '[]', ?)",
                (user_id, summary)
            )
        else:
            c.execute(
                "UPDATE relationships SET summary=? WHERE user_id=?",
                (summary, user_id)
            )

    return summary


async def run(
    user_msg: str,
    response: str,
    user_id: str,
    hop_id: Optional[int],
    flags: list
) -> None:
    extracted = await asyncio.to_thread(extract_facts, user_msg, response)

    await asyncio.to_thread(db_upsert_relationship, user_id, extracted)
    await asyncio.to_thread(db_append_hop_fields, hop_id, extracted, flags)
