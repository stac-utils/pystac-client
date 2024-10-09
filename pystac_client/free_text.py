"""Client-side free-text search filtering as described in `OGC API - Features - Part 9:
Text Search <https://docs.ogc.org/DRAFTS/24-031.html#q-parameter>`__

Uses the `SQLite FTS5 Extension <https://www.sqlite.org/fts5.html>`__ to implement
free-text search filtering.
"""

import re
import sqlite3


def parse_query_for_sqlite(q: str) -> str:
    """Translate an OGC Features API free-text search query into the SQLite text search
    syntax
    """
    # separate out search terms, quoted exact phrases, commas, and exact phrases
    tokens = [token.strip() for token in re.findall(r'"[^"]*"|,|[\(\)]|[^,\s\(\)]+', q)]

    # special characters that need to be escaped or quoted for sqlite fts5
    special_chars = set("-@&:^~<>=")

    for i, token in enumerate(tokens):
        if token.startswith("+"):
            tokens[i] = token[1:].strip()
        elif token.startswith("-"):
            tokens[i] = "NOT " + token[1:].strip()
        elif token == ",":
            tokens[i] = "OR"
        elif any(char in token for char in special_chars):
            # Escape any existing double quotes in the token
            escaped_token = token.replace('"', '""')
            tokens[i] = f'"{escaped_token}"'

    return " ".join(tokens)


def sqlite_text_search(q: str, text_fields: dict[str, str]) -> bool:
    """Perform a free-text search against a set of text fields for a single
    collection to determine if that collection matches the query.

    Creates an in-memory SQLite database with a single table and a single row
    then runs the MATCH query to determine if the row matches the search
    criteria.
    """
    column_clause = ", ".join(text_fields.keys())
    value_clause = ", ".join(["?" for _ in text_fields.keys()])

    with sqlite3.connect(":memory:") as conn:  # Use an in-memory database
        cursor = conn.cursor()

        cursor.execute(
            f"""
        CREATE VIRTUAL TABLE collections USING fts5({column_clause});
        """
        )

        cursor.execute(
            f"""
        INSERT INTO collections ({column_clause}) VALUES ({value_clause});
        """,
            tuple(text_fields.values()),
        )

        cursor.execute(
            f"""
        SELECT COUNT(*)
        FROM collections WHERE collections MATCH '{parse_query_for_sqlite(q)}';
        """
        )

        return bool(cursor.fetchone()[0])
