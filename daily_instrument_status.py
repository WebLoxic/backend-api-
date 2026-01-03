import psycopg2
import os
from datetime import date

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_F6UtkWr4MNDp@ep-rough-glitter-ahvbr99r-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"
)

def run():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("Running daily instrument status update...")

    # 1️⃣ Mark expired instruments
    cur.execute("""
        UPDATE instruments
        SET is_active = false,
            is_expired = true
        WHERE expiry IS NOT NULL
          AND expiry < CURRENT_DATE;
    """)

    # 2️⃣ Mark active instruments
    cur.execute("""
        UPDATE instruments
        SET is_active = true,
            is_expired = false,
            last_seen = CURRENT_DATE
        WHERE (expiry IS NULL OR expiry >= CURRENT_DATE)
          AND exchange IN ('NSE','BSE','NFO','MCX','CDS');
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("Instrument status update completed.")

if __name__ == "__main__":
    run()
