"""API endpoints for Entity Extraction and Tracking.

Admin-gated triggers and analytics endpoints for dashboard micro-widgets.
"""

from __future__ import annotations

import os
import sqlite3
from flask import Blueprint, jsonify, request
from pathlib import Path
from typing import Any, Dict, List

from app.services.rbac import require_admin as _admin_required
from app.services.entities import EntityExtractionService, _connect_db

entities_bp = Blueprint("entities", __name__)
root_dir = str(Path(__file__).resolve().parents[2])


@entities_bp.route("/api/entities/stats", methods=["GET"])
def get_entity_stats():
    """Retrieve top entities filtered by type, date range, or channels."""
    ent_type = request.args.get("type")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    channels_str = request.args.get("channels")
    limit = int(request.args.get("limit", 20))

    query = """
        SELECT e.id, e.name, e.type, SUM(ve.mentions_count) as total_mentions, COUNT(DISTINCT ve.video_id) as video_count
        FROM entities e
        JOIN video_entities ve ON e.id = ve.entity_id
        JOIN videos v ON ve.video_id = v.video_id
        WHERE 1=1
    """
    params = []

    if ent_type:
        query += " AND e.type = ?"
        params.append(ent_type)

    if start_date:
        query += " AND v.published_at >= ?"
        params.append(start_date)

    if end_date:
        query += " AND v.published_at <= ?"
        params.append(end_date)

    if channels_str:
        channel_list = [c.strip() for c in channels_str.split(",") if c.strip()]
        if channel_list:
            placeholders = ",".join("?" for _ in channel_list)
            query += f" AND v.channel_id IN ({placeholders})"
            params.extend(channel_list)

    query += " GROUP BY e.id, e.name, e.type ORDER BY total_mentions DESC LIMIT ?"
    params.append(limit)

    conn = _connect_db(root_dir)
    try:
        rows = conn.execute(query, params).fetchall()
        result = [dict(row) for row in rows]
        return jsonify({"ok": True, "entities": result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        conn.close()


@entities_bp.route("/api/entities/timeline", methods=["GET"])
def get_entity_timeline():
    """Retrieve chronologically aggregated entity mention timeline coordinates."""
    entity_ids_str = request.args.get("entity_ids")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    channels_str = request.args.get("channels")
    limit_entities = int(request.args.get("limit_entities", 5))

    conn = _connect_db(root_dir)
    try:
        resolved_ids = []
        if entity_ids_str:
            resolved_ids = [int(i.strip()) for i in entity_ids_str.split(",") if i.strip().isdigit()]
        
        # If no specific entity IDs provided, fetch top 5 active entities first
        if not resolved_ids:
            top_query = """
                SELECT e.id
                FROM entities e
                JOIN video_entities ve ON e.id = ve.entity_id
                GROUP BY e.id
                ORDER BY SUM(ve.mentions_count) DESC
                LIMIT ?
            """
            top_rows = conn.execute(top_query, (limit_entities,)).fetchall()
            resolved_ids = [row["id"] for row in top_rows]

        if not resolved_ids:
            return jsonify({"ok": True, "timeline": []})

        query = """
            SELECT SUBSTR(v.published_at, 1, 10) as date, ve.entity_id, e.name, SUM(ve.mentions_count) as count
            FROM video_entities ve
            JOIN entities e ON ve.entity_id = e.id
            JOIN videos v ON ve.video_id = v.video_id
            WHERE ve.entity_id IN ({placeholders})
        """.format(placeholders=",".join("?" for _ in resolved_ids))
        
        params = list(resolved_ids)

        if start_date:
            query += " AND v.published_at >= ?"
            params.append(start_date)

        if end_date:
            query += " AND v.published_at <= ?"
            params.append(end_date)

        if channels_str:
            channel_list = [c.strip() for c in channels_str.split(",") if c.strip()]
            if channel_list:
                placeholders = ",".join("?" for _ in channel_list)
                query += f" AND v.channel_id IN ({placeholders})"
                params.extend(channel_list)

        query += " GROUP BY date, ve.entity_id, e.name ORDER BY date ASC"
        rows = conn.execute(query, params).fetchall()
        result = [dict(row) for row in rows]
        return jsonify({"ok": True, "timeline": result})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        conn.close()


@entities_bp.route("/api/entities/extract", methods=["POST"])
@_admin_required
def extract_entities():
    """Trigger entity extraction for a set of video IDs (Admin only)."""
    data = request.get_json() or {}
    video_ids = data.get("video_ids", [])
    provider = data.get("provider", "gemini")
    model = data.get("model")

    if not video_ids:
        # Fallback: scan recent 10 videos that don't have entities extracted yet
        conn = _connect_db(root_dir)
        try:
            query = """
                SELECT video_id FROM videos
                WHERE video_id NOT IN (SELECT DISTINCT video_id FROM video_entities)
                ORDER BY published_at DESC LIMIT 10
            """
            rows = conn.execute(query).fetchall()
            video_ids = [row["video_id"] for row in rows]
        finally:
            conn.close()

    if not video_ids:
        return jsonify({"ok": True, "message": "No videos found for extraction", "extracted_counts": {}})

    extracted_counts = {}
    for vid in video_ids:
        count = EntityExtractionService.extract_entities_for_video(root_dir, vid, provider, model)
        extracted_counts[vid] = count

    return jsonify({
        "ok": True,
        "message": f"Processed {len(video_ids)} videos",
        "extracted_counts": extracted_counts
    })


@entities_bp.route("/api/entities/aliases", methods=["POST"])
@_admin_required
def register_alias():
    """Register or re-route alias mappings for entity deduplication (Admin only)."""
    data = request.get_json() or {}
    alias_name = data.get("alias_name", "").strip()
    canonical_name = data.get("canonical_name", "").strip()
    ent_type = data.get("type", "person").strip()

    if not alias_name or not canonical_name:
        return jsonify({"ok": False, "error": "alias_name and canonical_name are required"}), 400

    conn = _connect_db(root_dir)
    cursor = conn.cursor()
    try:
        # Find or create canonical entity
        cursor.execute("SELECT id FROM entities WHERE name = ?", (canonical_name,))
        row = cursor.fetchone()
        if row:
            canonical_id = row["id"]
        else:
            cursor.execute(
                "INSERT INTO entities (name, type) VALUES (?, ?)",
                (canonical_name, ent_type)
            )
            canonical_id = cursor.lastrowid

        # Check if alias_name exists in entities as a canonical entity
        cursor.execute("SELECT id FROM entities WHERE name = ?", (alias_name,))
        alias_entity_row = cursor.fetchone()

        if alias_entity_row:
            alias_entity_id = alias_entity_row["id"]
            if alias_entity_id != canonical_id:
                # Merge video_entities from alias_entity_id to canonical_id
                cursor.execute(
                    "SELECT video_id, mentions_count, source FROM video_entities WHERE entity_id = ?",
                    (alias_entity_id,)
                )
                alias_ve_rows = cursor.fetchall()
                for ve in alias_ve_rows:
                    vid = ve["video_id"]
                    m_count = ve["mentions_count"]
                    src = ve["source"]
                    cursor.execute(
                        "SELECT mentions_count FROM video_entities WHERE video_id = ? AND entity_id = ? AND source = ?",
                        (vid, canonical_id, src)
                    )
                    canon_ve = cursor.fetchone()
                    if canon_ve:
                        new_count = canon_ve["mentions_count"] + m_count
                        cursor.execute(
                            "UPDATE video_entities SET mentions_count = ? WHERE video_id = ? AND entity_id = ? AND source = ?",
                            (new_count, vid, canonical_id, src)
                        )
                        cursor.execute(
                            "DELETE FROM video_entities WHERE video_id = ? AND entity_id = ? AND source = ?",
                            (vid, alias_entity_id, src)
                        )
                    else:
                        cursor.execute(
                            "UPDATE video_entities SET entity_id = ? WHERE video_id = ? AND entity_id = ? AND source = ?",
                            (canonical_id, vid, alias_entity_id, src)
                        )
                # Re-route any aliases pointing to alias_entity_id to point to canonical_id
                cursor.execute(
                    "UPDATE entity_aliases SET canonical_id = ? WHERE canonical_id = ?",
                    (canonical_id, alias_entity_id)
                )
                # Delete the old canonical entity
                cursor.execute("DELETE FROM entities WHERE id = ?", (alias_entity_id,))

                # Insert the alias link
                cursor.execute(
                    "INSERT OR IGNORE INTO entity_aliases (canonical_id, alias) VALUES (?, ?)",
                    (canonical_id, alias_name)
                )
        else:
            # Check if it already exists as an alias
            cursor.execute(
                "SELECT id, canonical_id FROM entity_aliases WHERE alias = ?",
                (alias_name,)
            )
            alias_row = cursor.fetchone()
            if alias_row:
                old_canonical_id = alias_row["canonical_id"]
                if old_canonical_id != canonical_id:
                    # Merge video_entities from old_canonical_id to canonical_id
                    cursor.execute(
                        "SELECT video_id, mentions_count, source FROM video_entities WHERE entity_id = ?",
                        (old_canonical_id,)
                    )
                    old_ve_rows = cursor.fetchall()
                    for ve in old_ve_rows:
                        vid = ve["video_id"]
                        m_count = ve["mentions_count"]
                        src = ve["source"]
                        cursor.execute(
                            "SELECT mentions_count FROM video_entities WHERE video_id = ? AND entity_id = ? AND source = ?",
                            (vid, canonical_id, src)
                        )
                        canon_ve = cursor.fetchone()
                        if canon_ve:
                            new_count = canon_ve["mentions_count"] + m_count
                            cursor.execute(
                                "UPDATE video_entities SET mentions_count = ? WHERE video_id = ? AND entity_id = ? AND source = ?",
                                (new_count, vid, canonical_id, src)
                            )
                            cursor.execute(
                                "DELETE FROM video_entities WHERE video_id = ? AND entity_id = ? AND source = ?",
                                (vid, old_canonical_id, src)
                            )
                        else:
                            cursor.execute(
                                "UPDATE video_entities SET entity_id = ? WHERE video_id = ? AND entity_id = ? AND source = ?",
                                (canonical_id, vid, old_canonical_id, src)
                            )
                    # Update alias canonical_id link
                    cursor.execute(
                        "UPDATE entity_aliases SET canonical_id = ? WHERE id = ?",
                        (canonical_id, alias_row["id"])
                    )
                    # If old canonical entity now has no references, prune it
                    cursor.execute(
                        "SELECT 1 FROM video_entities WHERE entity_id = ?",
                        (old_canonical_id,)
                    )
                    if not cursor.fetchone():
                        cursor.execute("DELETE FROM entities WHERE id = ?", (old_canonical_id,))
            else:
                cursor.execute(
                    "INSERT INTO entity_aliases (canonical_id, alias) VALUES (?, ?)",
                    (canonical_id, alias_name)
                )

        conn.commit()
        return jsonify({"ok": True, "message": f"Alias '{alias_name}' mapped to '{canonical_name}'"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        conn.close()
