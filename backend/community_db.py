import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = "community.db"

def create_tables():
    """Creates the database schema if it doesn't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                embedding_vector TEXT,
                consensus_score REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                complexity_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                user_id TEXT,
                vote_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debate_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                flow_state TEXT,
                assigned_models TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                citation_map TEXT,
                winner_score REAL,
                FOREIGN KEY (job_id) REFERENCES debate_jobs(id)
            )
        """)

        conn.commit()

def add_topic(
    title: str,
    embedding_vector: Optional[List[float]] = None,
    consensus_score: float = 0.0,
    status: str = 'active',
    complexity_score: float = 0.0
) -> int:
    """Adds a new topic to the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Serialize embedding_vector to JSON string if provided
        vector_json = json.dumps(embedding_vector) if embedding_vector else None

        cursor.execute("""
            INSERT INTO topics
            (title, embedding_vector, consensus_score, status, complexity_score)
            VALUES (?, ?, ?, ?, ?)
        """, (title, vector_json, consensus_score, status, complexity_score))

        conn.commit()
        return cursor.lastrowid

def add_vote(topic_id: int, user_id: str, vote_type: str) -> int:
    """Adds a vote record for a specific topic."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO votes (topic_id, user_id, vote_type)
            VALUES (?, ?, ?)
        """, (topic_id, user_id, vote_type))
        conn.commit()
        return cursor.lastrowid

def get_ranked_topics(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves topics ordered by consensus_score."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM topics
            ORDER BY consensus_score DESC
            LIMIT ?
        """, (limit,))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        # Convert JSON string back to list for embedding_vector
        result = []
        for row in rows:
            row_dict = dict(zip(columns, row))
            if row_dict['embedding_vector']:
                row_dict['embedding_vector'] = json.loads(row_dict['embedding_vector'])
            result.append(row_dict)

        return result
