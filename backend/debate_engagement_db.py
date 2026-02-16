"""
Debate Engagement Database Layer
Copyright (C) 2026 Stephen F Smithers. All Rights Reserved.

PATENT-PROTECTED CODE - Automated Argumentation Processing System
This code implements proprietary algorithms for:
- Real-Time Community Quality Assessment (Patent Claim #5)
- Temporal Engagement Metrics During AI Generation (Patent Claim #6)

NOTICE: This code contains trade secrets and confidential information
belonging to Stephen F Smithers. Unauthorized use, reproduction, or
distribution is strictly prohibited without written permission.

Author: Stephen F Smithers
Date: February 16, 2026
Repository: https://github.com/ssmithers/aidebate
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = "community.db"


def create_engagement_tables():
    """
    Creates database tables for debate engagement features.

    PATENT CLAIM #5: Real-Time Community Quality Assessment
    Enables voting on AI-generated arguments DURING debate execution.
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Completed debates with aggregated metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS completed_debates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER,
                debate_job_id INTEGER,
                pro_model TEXT,
                con_model TEXT,
                total_pro_votes INTEGER DEFAULT 0,
                total_con_votes INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id),
                FOREIGN KEY (debate_job_id) REFERENCES debate_jobs(id)
            )
        """)

        # Individual speeches with vote tracking
        # PATENT INNOVATION: Speech-level quality metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debate_speeches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debate_id INTEGER NOT NULL,
                speech_type TEXT NOT NULL,
                side TEXT NOT NULL,
                content TEXT NOT NULL,
                upvotes INTEGER DEFAULT 0,
                downvotes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (debate_id) REFERENCES completed_debates(id)
            )
        """)

        # Vote history with timestamps
        # PATENT INNOVATION: Temporal engagement tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS speech_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                speech_id INTEGER NOT NULL,
                user_id TEXT NOT NULL,
                vote_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (speech_id) REFERENCES debate_speeches(id),
                UNIQUE(speech_id, user_id)
            )
        """)

        # Threaded comment system
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debate_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debate_id INTEGER NOT NULL,
                speech_id INTEGER,
                user_id TEXT NOT NULL,
                comment_text TEXT NOT NULL,
                parent_comment_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (debate_id) REFERENCES completed_debates(id),
                FOREIGN KEY (speech_id) REFERENCES debate_speeches(id),
                FOREIGN KEY (parent_comment_id) REFERENCES debate_comments(id)
            )
        """)

        conn.commit()


def add_completed_debate(
    topic_id: int,
    job_id: int,
    pro_model: str,
    con_model: str
) -> int:
    """
    Records a completed debate.

    Args:
        topic_id: ID from topics table
        job_id: ID from debate_jobs table
        pro_model: AI model used for pro side
        con_model: AI model used for con side

    Returns:
        debate_id: ID of newly created debate record

    Author: Stephen F Smithers
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO completed_debates
            (topic_id, debate_job_id, pro_model, con_model)
            VALUES (?, ?, ?, ?)
        """, (topic_id, job_id, pro_model, con_model))
        conn.commit()
        return cursor.lastrowid


def add_speech(
    debate_id: int,
    speech_type: str,
    side: str,
    content: str
) -> int:
    """
    Adds a speech to a debate.

    PATENT CLAIM #5: Speech-level quality tracking for real-time assessment.

    Args:
        debate_id: ID of the debate
        speech_type: Speech identifier (1AC, 1NC, CX, 1AR, etc.)
        side: "pro" or "con"
        content: Full text of the speech

    Returns:
        speech_id: ID of newly created speech record

    Copyright (C) 2026 Stephen F Smithers
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO debate_speeches
            (debate_id, speech_type, side, content)
            VALUES (?, ?, ?, ?)
        """, (debate_id, speech_type, side, content))
        conn.commit()
        return cursor.lastrowid


def vote_on_speech(speech_id: int, user_id: str, vote_type: str):
    """
    Records a vote on a speech and updates aggregate counters.

    PATENT CLAIM #5: Real-Time Community Quality Assessment
    This function enables voting DURING debate generation, creating
    a temporal engagement metric that correlates vote timing with
    AI generation progress.

    Args:
        speech_id: ID of speech being voted on
        user_id: Anonymous user identifier
        vote_type: "up" or "down"

    Proprietary Algorithm: Stephen F Smithers, 2026
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Insert or replace vote (users can change their vote)
        cursor.execute("""
            INSERT OR REPLACE INTO speech_votes (speech_id, user_id, vote_type)
            VALUES (?, ?, ?)
        """, (speech_id, user_id, vote_type))

        # Recalculate upvotes and downvotes for this speech
        cursor.execute("""
            SELECT
                SUM(CASE WHEN vote_type = 'up' THEN 1 ELSE 0 END) as upvotes,
                SUM(CASE WHEN vote_type = 'down' THEN 1 ELSE 0 END) as downvotes
            FROM speech_votes
            WHERE speech_id = ?
        """, (speech_id,))

        upvotes, downvotes = cursor.fetchone()

        # Update speech vote counts
        cursor.execute("""
            UPDATE debate_speeches
            SET upvotes = ?, downvotes = ?
            WHERE id = ?
        """, (upvotes or 0, downvotes or 0, speech_id))

        # Update debate-level totals
        cursor.execute("""
            SELECT debate_id, side FROM debate_speeches WHERE id = ?
        """, (speech_id,))
        debate_id, side = cursor.fetchone()

        # Aggregate all votes for this side
        cursor.execute("""
            SELECT SUM(upvotes), SUM(downvotes)
            FROM debate_speeches
            WHERE debate_id = ? AND side = ?
        """, (debate_id, side))

        total_up, total_down = cursor.fetchone()
        net_votes = (total_up or 0) - (total_down or 0)

        # Update debate totals
        if side == 'pro':
            cursor.execute("""
                UPDATE completed_debates
                SET total_pro_votes = ?
                WHERE id = ?
            """, (net_votes, debate_id))
        else:
            cursor.execute("""
                UPDATE completed_debates
                SET total_con_votes = ?
                WHERE id = ?
            """, (net_votes, debate_id))

        conn.commit()


def add_comment(
    debate_id: int,
    user_id: str,
    comment_text: str,
    speech_id: Optional[int] = None,
    parent_id: Optional[int] = None
) -> int:
    """
    Adds a comment to a debate or specific speech.

    Args:
        debate_id: ID of the debate
        user_id: Anonymous user identifier
        comment_text: Comment content
        speech_id: Optional - ID of specific speech being commented on
        parent_id: Optional - ID of parent comment for threading

    Returns:
        comment_id: ID of newly created comment

    Copyright (C) 2026 Stephen F Smithers
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO debate_comments
            (debate_id, speech_id, user_id, comment_text, parent_comment_id)
            VALUES (?, ?, ?, ?, ?)
        """, (debate_id, speech_id, user_id, comment_text, parent_id))

        # Update comment count on debate
        cursor.execute("""
            UPDATE completed_debates
            SET total_comments = total_comments + 1
            WHERE id = ?
        """, (debate_id,))

        conn.commit()
        return cursor.lastrowid


def get_recent_debates(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Returns the most recent completed debates.

    Returns:
        List of debate dictionaries ordered by completion time DESC

    Author: Stephen F Smithers
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                cd.id,
                cd.topic_id,
                t.title as topic_title,
                cd.pro_model,
                cd.con_model,
                cd.total_pro_votes,
                cd.total_con_votes,
                cd.total_comments,
                cd.completed_at
            FROM completed_debates cd
            JOIN topics t ON cd.topic_id = t.id
            ORDER BY cd.completed_at DESC
            LIMIT ?
        """, (limit,))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]


def get_top_debates(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Returns debates ordered by total engagement.

    PATENT CLAIM #6: Temporal Engagement Metrics
    Engagement score = (pro_votes + con_votes + comments)
    This metric reflects community interest over time.

    Proprietary Algorithm: Stephen F Smithers, 2026
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                cd.id,
                cd.topic_id,
                t.title as topic_title,
                cd.pro_model,
                cd.con_model,
                cd.total_pro_votes,
                cd.total_con_votes,
                cd.total_comments,
                cd.completed_at,
                (ABS(cd.total_pro_votes) + ABS(cd.total_con_votes) + cd.total_comments) as engagement_score
            FROM completed_debates cd
            JOIN topics t ON cd.topic_id = t.id
            ORDER BY engagement_score DESC, cd.completed_at DESC
            LIMIT ?
        """, (limit,))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]


def get_debate_details(debate_id: int) -> Dict[str, Any]:
    """
    Returns full debate details with all speeches and metadata.

    Args:
        debate_id: ID of the debate to retrieve

    Returns:
        Dictionary containing debate metadata, speeches, and statistics

    Copyright (C) 2026 Stephen F Smithers
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Get debate metadata
        cursor.execute("""
            SELECT
                cd.id,
                cd.topic_id,
                t.title as topic_title,
                cd.pro_model,
                cd.con_model,
                cd.total_pro_votes,
                cd.total_con_votes,
                cd.total_comments,
                cd.completed_at
            FROM completed_debates cd
            JOIN topics t ON cd.topic_id = t.id
            WHERE cd.id = ?
        """, (debate_id,))

        debate_row = cursor.fetchone()
        if not debate_row:
            return {}

        columns = [desc[0] for desc in cursor.description]
        debate = dict(zip(columns, debate_row))

        # Get all speeches for this debate
        cursor.execute("""
            SELECT
                id,
                speech_type,
                side,
                content,
                upvotes,
                downvotes,
                created_at
            FROM debate_speeches
            WHERE debate_id = ?
            ORDER BY created_at ASC
        """, (debate_id,))

        speech_columns = [desc[0] for desc in cursor.description]
        speech_rows = cursor.fetchall()
        debate['speeches'] = [dict(zip(speech_columns, row)) for row in speech_rows]

        return debate


def get_speech_comments(speech_id: int) -> List[Dict[str, Any]]:
    """
    Returns all comments for a specific speech.

    Args:
        speech_id: ID of the speech

    Returns:
        List of comment dictionaries with threading support

    Author: Stephen F Smithers
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id,
                debate_id,
                speech_id,
                user_id,
                comment_text,
                parent_comment_id,
                timestamp
            FROM debate_comments
            WHERE speech_id = ?
            ORDER BY timestamp ASC
        """, (speech_id,))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]


def get_debate_comments(debate_id: int) -> List[Dict[str, Any]]:
    """
    Returns all comments for an entire debate (overall + per-speech).

    Args:
        debate_id: ID of the debate

    Returns:
        List of all comment dictionaries

    Copyright (C) 2026 Stephen F Smithers
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id,
                debate_id,
                speech_id,
                user_id,
                comment_text,
                parent_comment_id,
                timestamp
            FROM debate_comments
            WHERE debate_id = ?
            ORDER BY timestamp ASC
        """, (debate_id,))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        return [dict(zip(columns, row)) for row in rows]
