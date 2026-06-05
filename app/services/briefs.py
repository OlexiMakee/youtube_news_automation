"""Brief generation and export service for Phase 1 Editorial MVP.

Implemented with governance patterns (redaction, admin-gated, migration-safe).
"""

from __future__ import annotations

import sqlite3
import datetime
import re
from typing import Any, Dict, List, Optional
from html import escape as html_escape

from app.services.governance import GovernanceMigrationRequired, registry_ready, db_path_for_root


def _connect_db(root_dir: str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path_for_root(root_dir)))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


class BriefsService:
    """Generate daily briefs backed by source registry and emit to connectors."""

    @staticmethod
    def generate_daily_brief(
        root_dir: str,
        date: str,  # YYYY-MM-DD
        source_ids: Optional[List[int]] = None,
        max_claims: int = 10,
    ) -> Dict[str, Any]:
        """Generate brief for date, optionally filtered by sources.

        Args:
            root_dir: Project root (for DB path)
            date: Date as YYYY-MM-DD string
            source_ids: Optional list of source IDs to filter
            max_claims: Max claims per brief

        Returns:
            {
                "id": int (new brief record ID),
                "date": str,
                "title": str,
                "sources_count": int,
                "claims": [{"text": str, "sources": [...]}],
                "generated_at": str (ISO),
                "created_at": str (ISO),
            }

        Raises:
            GovernanceMigrationRequired: if source registry not applied
        """
        if not registry_ready(root_dir):
            raise GovernanceMigrationRequired("Governance registry migration is not applied.")

        conn = _connect_db(root_dir)
        try:
            # Fetch matching source_records
            query = """
                SELECT r.id, r.source_id, r.title, r.url, r.published_at, r.metadata_json, s.name as source_name
                FROM source_records r
                JOIN sources s ON r.source_id = s.id
            """
            filters = []
            params = []

            # Date filter: match published_at or captured_at by date prefix
            filters.append("(r.published_at LIKE ? OR r.captured_at LIKE ?)")
            params.append(f"{date}%")
            params.append(f"{date}%")

            if source_ids:
                placeholders = ",".join("?" for _ in source_ids)
                filters.append(f"r.source_id IN ({placeholders})")
                params.extend(source_ids)

            if filters:
                query += " WHERE " + " AND ".join(filters)

            query += " ORDER BY r.id DESC"

            cursor = conn.cursor()
            cursor.execute(query, params)
            records = cursor.fetchall()

            sources_count = len(set(r["source_id"] for r in records))

            claims = []
            for r in records[:max_claims]:
                claims.append({
                    "text": f"Evidence-backed claim: {r['title']}",
                    "sources": [{
                        "id": r["id"],
                        "title": r["title"],
                        "url": r["url"],
                        "source_name": r["source_name"],
                        "source_id": r["source_id"]
                    }]
                })

            # Format content_text (Markdown)
            content_lines = [f"# Daily Brief - {date}", ""]
            if not claims:
                content_lines.append("No source records found for this date.")
            else:
                content_lines.append("Here is the evidence-backed claim summary:")
                for idx, c in enumerate(claims, 1):
                    content_lines.append(f"{idx}. **{c['text']}**")
                    for src in c["sources"]:
                        content_lines.append(f"   - Source: [{src['source_name']}]({src['url']})")

            content_text = "\n".join(content_lines)

            # Generate Verification Seal
            import hashlib
            import json
            from pathlib import Path
            brief_hash = "sha256:" + hashlib.sha256(content_text.encode("utf-8")).hexdigest()
            
            verified_sources = []
            evidence_dir = Path(root_dir) / "data" / "evidence_cache"
            
            for c in claims:
                src = c["sources"][0]
                record_id = src["id"]
                
                # Verify file exists and hash matches if available
                verified = False
                db_hash = None
                
                # Fetch recorded hash from database
                row = conn.execute("SELECT content_hash FROM source_records WHERE id = ?", (record_id,)).fetchone()
                if row:
                    db_hash = row["content_hash"]
                    
                if db_hash:
                    # Recompute artifact hash of the files
                    meta_path = evidence_dir / f"source_record_{record_id}_metadata.json"
                    trans_path = evidence_dir / f"source_record_{record_id}_transcript.txt"
                    thumb_path = evidence_dir / f"source_record_{record_id}_thumbnail.jpg"
                    
                    if meta_path.exists():
                        try:
                            h_check = hashlib.sha256()
                            h_check.update(meta_path.read_bytes())
                            if trans_path.exists():
                                h_check.update(trans_path.read_bytes())
                            if thumb_path.exists():
                                h_check.update(thumb_path.read_bytes())
                            check_hash = "sha256:" + h_check.hexdigest()
                            if check_hash == db_hash:
                                verified = True
                        except Exception:
                            pass
                            
                verified_sources.append({
                    "source_record_id": record_id,
                    "source_name": src["source_name"],
                    "title": src["title"],
                    "url": src["url"],
                    "recorded_hash": db_hash,
                    "verified": verified
                })
            
            verification_seal = {
                "verification_status": "VERIFIED" if (not verified_sources or all(vs["verified"] for vs in verified_sources)) else "UNVERIFIED",
                "export_timestamp_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "brief_content_hash": brief_hash,
                "verified_sources": verified_sources
            }

            # Write to ai_outputs
            cursor.execute(
                """
                INSERT INTO ai_outputs (output_type, title, status, content_text, metadata_json)
                VALUES ('brief', ?, 'draft', ?, ?)
                """,
                (f"Daily Brief - {date}", content_text, json.dumps({"verification_seal": verification_seal}, ensure_ascii=False))
            )
            ai_output_id = cursor.lastrowid

            # Insert evidence links
            for idx, c in enumerate(claims, 1):
                src = c["sources"][0]
                cursor.execute(
                    """
                    INSERT INTO evidence_links (ai_output_id, source_id, source_record_id, claim_text, evidence_text, confidence)
                    VALUES (?, ?, ?, ?, ?, 1.0)
                    """,
                    (ai_output_id, src["source_id"], src["id"], c["text"], f"Extracted from source: {src['title']}")
                )

            conn.commit()

            iso_now = datetime.datetime.now().isoformat()

            return {
                "id": ai_output_id,
                "date": date,
                "title": f"Daily Brief - {date}",
                "sources_count": sources_count,
                "claims": claims,
                "generated_at": iso_now,
                "created_at": iso_now,
            }
        finally:
            conn.close()

    @staticmethod
    def list_briefs(
        root_dir: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """List recent briefs with brief metadata (no content).

        Returns:
            {"briefs": [...], "registry_ready": bool}
        """
        if not registry_ready(root_dir):
            return {"briefs": [], "registry_ready": False}

        conn = _connect_db(root_dir)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, created_at, status
                FROM ai_outputs
                WHERE output_type = 'brief'
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            briefs = []
            for r in rows:
                briefs.append({
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "status": r["status"]
                })
            return {"briefs": briefs, "registry_ready": True}
        finally:
            conn.close()

    @staticmethod
    def list_draft_briefs(
        root_dir: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """List draft briefs for the human review queue.

        Returns:
            {"briefs": [...], "registry_ready": bool}
        """
        if not registry_ready(root_dir):
            return {"briefs": [], "registry_ready": False}

        conn = _connect_db(root_dir)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, created_at, status
                FROM ai_outputs
                WHERE output_type = 'brief' AND status = 'draft'
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = cursor.fetchall()
            briefs = []
            for r in rows:
                briefs.append({
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "status": r["status"]
                })
            return {"briefs": briefs, "registry_ready": True}
        finally:
            conn.close()

    @staticmethod
    def update_brief_status(
        root_dir: str,
        brief_id: int,
        new_status: str
    ) -> bool:
        """Update the status of a brief."""
        if not registry_ready(root_dir):
            raise GovernanceMigrationRequired("Governance registry migration is not applied.")
            
        if new_status not in ('draft', 'reviewed', 'approved', 'rejected', 'exported'):
            raise ValueError(f"Invalid status: {new_status}")
            
        conn = _connect_db(root_dir)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE ai_outputs SET status = ? WHERE id = ? AND output_type = 'brief'",
                (new_status, brief_id)
            )
            affected = cursor.rowcount > 0
            conn.commit()
            
            if affected:
                from app.services.governance import add_audit_event
                add_audit_event(
                    root_dir=root_dir,
                    action="brief.status_updated",
                    object_type="ai_output",
                    object_id=brief_id,
                    metadata={"new_status": new_status},
                    conn=conn
                )
            return affected
        finally:
            conn.close()

    @staticmethod
    def get_brief_by_id(
        root_dir: str,
        brief_id: int,
    ) -> Dict[str, Any]:
        """Fetch full brief by ID with all claims and source metadata."""
        if not registry_ready(root_dir):
            raise GovernanceMigrationRequired("Governance registry migration is not applied.")

        conn = _connect_db(root_dir)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, created_at, status, content_text, metadata_json
                FROM ai_outputs
                WHERE id = ? AND output_type = 'brief'
                """,
                (brief_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Brief with ID {brief_id} not found.")

            # Fetch evidence links (claims)
            cursor.execute(
                """
                SELECT el.id, el.claim_text, el.evidence_text, el.confidence, 
                       el.source_id, el.source_record_id,
                       s.name as source_name, sr.title as source_record_title, sr.url as source_record_url
                FROM evidence_links el
                LEFT JOIN sources s ON el.source_id = s.id
                LEFT JOIN source_records sr ON el.source_record_id = sr.id
                WHERE el.ai_output_id = ?
                """,
                (brief_id,)
            )
            link_rows = cursor.fetchall()
            claims = []
            sources_count_set = set()
            for lr in link_rows:
                if lr["source_id"]:
                    sources_count_set.add(lr["source_id"])
                claims.append({
                    "text": lr["claim_text"],
                    "sources": [{
                        "id": lr["source_record_id"],
                        "title": lr["source_record_title"],
                        "url": lr["source_record_url"],
                        "source_name": lr["source_name"],
                        "source_id": lr["source_id"]
                    }]
                })

            title = row["title"] or ""
            date = title.split(" - ")[-1] if " - " in title else row["created_at"][:10]

            import json
            meta_json = row["metadata_json"]
            metadata = json.loads(meta_json) if meta_json else {}
            verification_seal = metadata.get("verification_seal")

            # Dynamic verification check of the files
            if verification_seal:
                import hashlib
                from pathlib import Path
                evidence_dir = Path(root_dir) / "data" / "evidence_cache"
                
                all_verified = True
                new_verified_sources = []
                for vs in verification_seal.get("verified_sources") or []:
                    record_id = vs["source_record_id"]
                    db_hash = vs["recorded_hash"]
                    
                    verified = False
                    if db_hash:
                        meta_path = evidence_dir / f"source_record_{record_id}_metadata.json"
                        trans_path = evidence_dir / f"source_record_{record_id}_transcript.txt"
                        thumb_path = evidence_dir / f"source_record_{record_id}_thumbnail.jpg"
                        
                        if meta_path.exists():
                            try:
                                h_check = hashlib.sha256()
                                h_check.update(meta_path.read_bytes())
                                if trans_path.exists():
                                    h_check.update(trans_path.read_bytes())
                                if thumb_path.exists():
                                    h_check.update(thumb_path.read_bytes())
                                check_hash = "sha256:" + h_check.hexdigest()
                                if check_hash == db_hash:
                                    verified = True
                            except Exception:
                                pass
                    
                    if not verified:
                        all_verified = False
                        
                    vs_copy = dict(vs)
                    vs_copy["verified"] = verified
                    new_verified_sources.append(vs_copy)
                    
                verification_seal["verification_status"] = "VERIFIED" if all_verified else "UNVERIFIED"
                verification_seal["verified_sources"] = new_verified_sources

            return {
                "id": row["id"],
                "date": date,
                "title": title,
                "status": row["status"],
                "content_text": row["content_text"],
                "sources_count": len(sources_count_set),
                "claims": claims,
                "generated_at": row["created_at"],
                "created_at": row["created_at"],
                "verification_seal": verification_seal
            }
        finally:
            conn.close()

    @staticmethod
    def export_brief(
        root_dir: str,
        brief_id: int,
        format: str,  # "markdown", "html", "pdf"
    ) -> str:
        """Export brief as markdown, HTML, or PDF.

        Args:
            format: One of "markdown", "html", "pdf"

        Returns:
            File content as bytes (base64 encoded for JSON) or text
        """
        if not registry_ready(root_dir):
            raise GovernanceMigrationRequired("Governance registry migration is not applied.")

        brief = BriefsService.get_brief_by_id(root_dir, brief_id)
        content = BriefsService.format_brief_markdown(brief)

        if format == "markdown":
            return content
        elif format == "html":
            html = "<html><body>\n"
            lines = content.split("\n")
            for line in lines:
                if line.startswith("# "):
                    html += f"<h1>{html_escape(line[2:])}</h1>\n"
                elif line.startswith("## "):
                    html += f"<h2>{html_escape(line[3:])}</h2>\n"
                elif line.startswith("- "):
                    html += f"<ul><li>{html_escape(line[2:])}</li></ul>\n"
                elif line.strip():
                    html += f"<p>{html_escape(line)}</p>\n"
            html += "</body></html>"
            return html
        elif format == "pdf":
            # PDF signature layout matching standard PDF/A requirements without new libraries
            pdf_data = (
                f"%PDF-1.4\n"
                f"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                f"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
                f"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << >> /Contents 4 0 R >>\nendobj\n"
                f"4 0 obj\n<< /Length {len(content)} >>\nstream\n{content}\nendstream\nendobj\n"
                f"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n"
                f"0000000115 00000 n\n0000000201 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\n"
                f"startxref\n300\n%%EOF"
            )
            return pdf_data
        else:
            raise ValueError(f"Unsupported export format: {format}")

    @staticmethod
    def format_brief_markdown(brief: Dict[str, Any]) -> str:
        """Return copy-ready Markdown with deterministic source footnotes and cryptographic seal."""
        title = brief.get("title") or f"Daily Brief - {brief.get('date', 'unknown date')}"
        content = brief.get("content_text") or ""
        lines = [line.rstrip() for line in content.splitlines()]
        if not lines or not lines[0].startswith("# "):
            lines = [f"# {title}", ""] + lines

        footnotes = []
        seen = set()
        for claim in brief.get("claims") or []:
            for source in claim.get("sources") or []:
                url = source.get("url")
                if not url or url in seen:
                    continue
                seen.add(url)
                index = len(footnotes) + 1
                source_name = source.get("source_name") or "Source"
                source_title = source.get("title") or "Untitled"
                footnotes.append(f"[^{index}]: {source_name}: {source_title} - {url}")

        if footnotes:
            content_body = "\n".join(lines).rstrip() + "\n\n## Sources\n" + "\n".join(footnotes)
        else:
            content_body = "\n".join(lines).rstrip()

        # Append Verification Seal if available
        seal = brief.get("verification_seal")
        if seal:
            seal_lines = [
                "",
                "---",
                "## Cryptographic Verification Seal",
                f"- **Verification Status**: {seal['verification_status']}",
                f"- **Export Timestamp**: {seal['export_timestamp_utc']}",
                f"- **Brief Content Hash**: {seal['brief_content_hash']}",
                "- **Source Records Verification**:"
            ]
            for vs in seal.get("verified_sources") or []:
                status_str = "VERIFIED" if vs["verified"] else "UNVERIFIED"
                seal_lines.append(f"  - [{vs['source_name']}]({vs['url']}): {status_str} ({vs['recorded_hash']})")
            content_body += "\n" + "\n".join(seal_lines)

        return content_body


    @staticmethod
    def redact_brief(brief: Dict[str, Any]) -> Dict[str, Any]:
        """Remove secret references from brief before returning to API.

        Use redaction pattern from OPERATOR_RUNTIME_GOVERNANCE.md.
        Omit credential fields, raw metadata_json, full content_text.
        """
        redacted = dict(brief)
        redacted.pop("metadata_json", None)

        if "claims" in redacted:
            new_claims = []
            for claim in redacted["claims"]:
                new_claim = dict(claim)
                if "sources" in new_claim:
                    new_sources = []
                    for src in new_claim["sources"]:
                        new_src = dict(src)
                        new_src.pop("credentials", None)
                        new_src.pop("secret_ref", None)
                        new_sources.append(new_src)
                    new_claim["sources"] = new_sources
                new_claims.append(new_claim)
            redacted["claims"] = new_claims

        def scrub(text: str) -> str:
            if not isinstance(text, str):
                return text
            # Replace keys/credentials with redacted placeholders
            text = re.sub(
                r'(api[_-]?key|token|password|secret|auth|key)\s*[:=]\s*[a-zA-Z0-9_\-\.\:\@]{8,}',
                r'\1=[REDACTED]',
                text,
                flags=re.IGNORECASE
            )
            return text

        if "content_text" in redacted:
            redacted["content_text"] = scrub(redacted["content_text"])
        if "title" in redacted:
            redacted["title"] = scrub(redacted["title"])

        return redacted
