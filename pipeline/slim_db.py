"""Make the smaller copy of bible.db that ships in the release download.

    python3 pipeline/slim_db.py db/bible.db dist/.../db/bible.db

db/bible.db stays the full build: it keeps the raw source tags that the build's verification
and debugging use. The reader never reads those, so the release copy leaves them out, stores
three key-ordered lookup tables WITHOUT ROWID (so their primary key isn't kept a second time as
an index), drops the indexes that this makes redundant, and is vacuumed. The copy is checked
before it is accepted: SQLite and FTS5 integrity checks, and the same row count in every table.
"""
import sqlite3
import sys
from pathlib import Path

# token columns the reader doesn't use (raw source tags and ids; the parsed data is in morpheme)
DROP_COLUMNS = {"token": ["lemma_raw", "morph_raw", "source_ref", "variant_group"]}
# looked up only by a prefix of their primary key, so the table itself can be the index
WITHOUT_ROWID = {
    "cross_ref": {"cross_ref_from"},   # (from_canon, votes): from_canon is the key's first column
    "lemma_link": {"lemma_link_rank"},  # (direction, from_key, rank): ditto, and lists are short
    "verse_map": set(),
}


def mb(path: Path) -> str:
    return f"{path.stat().st_size / 1048576:.0f} MB"


def counts(con: sqlite3.Connection) -> dict[str, int]:
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'verse_fts%'")]
    return {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}


def to_without_rowid(con: sqlite3.Connection, table: str, redundant: set[str]):
    (sql,) = con.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    if "WITHOUT ROWID" in sql.upper():
        return
    indexes = [(n, s) for n, s in con.execute(
        "SELECT name, sql FROM sqlite_master WHERE type = 'index' AND tbl_name = ? AND sql IS NOT NULL", (table,))]
    new = f"{table}__new"
    body = sql[sql.index("("):].rstrip().rstrip(";")
    con.execute(f'CREATE TABLE "{new}" {body} WITHOUT ROWID')
    con.execute(f'INSERT INTO "{new}" SELECT * FROM "{table}"')
    con.execute(f'DROP TABLE "{table}"')
    con.execute(f'ALTER TABLE "{new}" RENAME TO "{table}"')
    for name, isql in indexes:
        if name not in redundant:
            con.execute(isql)


def main(src: Path, dst: Path):
    if sqlite3.sqlite_version_info < (3, 35):
        sys.exit(f"SQLite {sqlite3.sqlite_version} is too old (DROP COLUMN needs 3.35+)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.unlink(missing_ok=True)
    with sqlite3.connect(f"file:{src}?mode=ro", uri=True) as s, sqlite3.connect(dst) as d:
        s.backup(d)
        before = counts(s)
    con = sqlite3.connect(dst, isolation_level=None)
    con.execute("BEGIN")
    # views name these tables, which blocks rebuilding them: set the views aside meanwhile
    views = con.execute("SELECT name, sql FROM sqlite_master WHERE type = 'view'").fetchall()
    for name, _ in views:
        con.execute(f'DROP VIEW "{name}"')
    for table, cols in DROP_COLUMNS.items():
        have = {r[1] for r in con.execute(f'PRAGMA table_info("{table}")')}
        for c in cols:
            if c in have:
                con.execute(f'ALTER TABLE "{table}" DROP COLUMN "{c}"')
    for table, redundant in WITHOUT_ROWID.items():
        to_without_rowid(con, table, redundant)
    for _, vsql in views:
        con.execute(vsql)
    con.execute("INSERT INTO verse_fts(verse_fts) VALUES ('optimize')")
    con.execute("COMMIT")
    con.execute("VACUUM")

    problems = []
    if (ic := con.execute("PRAGMA integrity_check").fetchone()[0]) != "ok":
        problems.append(f"integrity_check: {ic}")
    try:
        con.execute("INSERT INTO verse_fts(verse_fts, rank) VALUES ('integrity-check', 1)")
    except sqlite3.DatabaseError as e:
        problems.append(f"FTS5 integrity-check: {e}")
    for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'view'").fetchall():
        try:
            con.execute(f'SELECT * FROM "{name}" LIMIT 1').fetchall()
        except sqlite3.DatabaseError as e:
            problems.append(f"view {name}: {e}")
    after = counts(con)
    if after != before:
        problems.append(f"row counts changed: { {t: (before.get(t), after.get(t)) for t in before.keys() | after.keys() if before.get(t) != after.get(t)} }")
    con.close()
    if problems:
        dst.unlink()
        sys.exit("slim copy rejected:\n  " + "\n  ".join(problems))
    print(f"slim copy: {mb(src)} -> {mb(dst)} ({sum(after.values()):,} rows in {len(after)} tables, all checks ok)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
