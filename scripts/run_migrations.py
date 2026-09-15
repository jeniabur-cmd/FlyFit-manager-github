"""מריץ את כל קובצי ה-SQL בתיקיית migrations/ מול מסד הנתונים ב-Supabase, לפי
סדר שמות הקבצים, ושומר טבלת מעקב _migrations כך שכל migration ירוץ פעם אחת
בלבד גם בהרצות חוזרות.

מחרוזת החיבור נקראת מ-st.secrets["SUPABASE_DB_URL"] בזמן ריצה בלבד ואינה
נכתבת או מודפסת לשום מקום - גם לא בהודעות שגיאה (ראו _connect).

הרצה: python scripts/run_migrations.py
"""
import sys
from pathlib import Path

import psycopg2
import streamlit as st

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"

CREATE_TRACKING_TABLE = """
create table if not exists _migrations (
    filename text primary key,
    applied_at timestamptz not null default now()
);
"""


def _get_db_url() -> str:
    db_url = st.secrets.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("SUPABASE_DB_URL לא מוגדר ב-.streamlit/secrets.toml")
    return db_url


def _connect():
    """מתחבר למסד הנתונים. בכוונה לא כולל את פרטי החיבור/השגיאה המקורית
    בהודעת השגיאה - מחרוזת החיבור עלולה להופיע בתוך טקסט שגיאות DSN של
    psycopg2, ואסור שהיא תודפס או תיכתב ללוג."""
    db_url = _get_db_url()
    try:
        return psycopg2.connect(db_url)
    except Exception as exc:
        raise RuntimeError(
            f"החיבור למסד הנתונים נכשל ({type(exc).__name__}). "
            "בדקו את SUPABASE_DB_URL ב-.streamlit/secrets.toml "
            "(מארח, פורט, שם משתמש, סיסמה, מצב SSL)."
        ) from None


def run_migrations() -> list[str]:
    """מריץ migrations חדשים בלבד (שאינם רשומים ב-_migrations).
    מחזיר את רשימת שמות הקבצים שהורצו כעת בפועל."""
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        print("לא נמצאו קובצי migration בתיקיית migrations/")
        return []

    conn = _connect()
    applied_now: list[str] = []
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TRACKING_TABLE)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("select filename from _migrations")
            already_applied = {row[0] for row in cur.fetchall()}

        for path in sql_files:
            if path.name in already_applied:
                print(f"skip  {path.name} (כבר הורץ)")
                continue
            sql = path.read_text(encoding="utf-8")
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    cur.execute("insert into _migrations (filename) values (%s)", (path.name,))
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            applied_now.append(path.name)
            print(f"OK    {path.name}")
    finally:
        conn.close()

    return applied_now


def verify_table(table_name: str, schema: str = "public") -> bool:
    """בודק דרך information_schema.tables האם הטבלה אכן קיימת."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                select table_name, table_schema
                from information_schema.tables
                where table_schema = %s and table_name = %s
                """,
                (schema, table_name),
            )
            row = cur.fetchone()
            print(f"information_schema.tables -> {row if row else '(אין שורה תואמת)'}")
            return row is not None
    finally:
        conn.close()


def main() -> int:
    try:
        applied = run_migrations()
    except RuntimeError as e:
        print(f"שגיאה: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"הרצת ה-migrations נכשלה ({type(e).__name__}): {e}", file=sys.stderr)
        return 1

    if applied:
        print(f"\nבוצעו {len(applied)} migrations חדשים: {', '.join(applied)}")
    else:
        print("\nכל ה-migrations כבר היו מעודכנים - לא בוצע שינוי.")

    try:
        exists = verify_table("arbox_classes")
    except RuntimeError as e:
        print(f"אזהרה: לא ניתן היה לאמת את קיום הטבלה: {e}", file=sys.stderr)
        return 0

    print(f"\nטבלת arbox_classes: {'קיימת ✅' if exists else 'לא נמצאה ❌'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
