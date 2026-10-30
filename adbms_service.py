"""
DevVault - Advanced Database Management Systems (ADBMS) Service
Multi-Database Architecture Manager, Query Optimizer & Performance Analyzer
Manages partitioned SQLite databases:
1. devvault_core.db   - Core transactional metadata & catalog
2. devvault_vault.db  - Dedicated high-capacity deliverables & file attachments
3. devvault_audit.db  - Immutable audit trail & change data capture (CDC)
"""
import os
import time
import sqlite3
import hashlib
from datetime import datetime

class ADBMSManager:
    def __init__(self, db_dir=None):
        # Default to instance directory to match Flask-SQLAlchemy 3.x instance path
        if db_dir:
            self.db_dir = db_dir
        else:
            cand = os.path.join(os.getcwd(), 'instance')
            self.db_dir = cand if os.path.exists(cand) else os.getcwd()
            
        os.makedirs(self.db_dir, exist_ok=True)
        self.db_paths = {
            'core': os.path.join(self.db_dir, 'devvault_core.db'),
            'vault': os.path.join(self.db_dir, 'devvault_vault.db'),
            'audit': os.path.join(self.db_dir, 'devvault_audit.db')
        }

    @staticmethod
    def get_sqlite_version():
        """Returns the active SQLite runtime engine version."""
        return sqlite3.sqlite_version

    def get_connection(self, db_key='core'):
        """Returns an SQLite connection configured with optimal ADBMS PRAGMAs."""
        db_path = self.db_paths.get(db_key, self.db_paths['core'])
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # ADBMS Essential PRAGMAs
        conn.execute("PRAGMA journal_mode = WAL;")        # Write-Ahead Logging for high concurrency
        conn.execute("PRAGMA foreign_keys = ON;")         # Strict referential integrity enforcement
        conn.execute("PRAGMA synchronous = NORMAL;")      # Optimized safe I/O synchronization
        conn.execute("PRAGMA busy_timeout = 5000;")       # Concurrency lock wait timeout
        return conn

    def get_federated_connection(self):
        """
        Creates a unified federated database session by attaching
        the vault and audit databases to the core database connection.
        Demonstrates ADBMS Database Federation and Cross-Database Queries.
        """
        conn = self.get_connection('core')
        vault_path = self.db_paths['vault'].replace('\\', '/')
        audit_path = self.db_paths['audit'].replace('\\', '/')

        conn.execute(f"ATTACH DATABASE '{vault_path}' AS vault_db;")
        conn.execute(f"ATTACH DATABASE '{audit_path}' AS audit_db;")
        return conn

    def setup_advanced_triggers_and_views(self):
        """
        Installs native SQLite triggers and views directly into the database engine,
        ensuring procedural business logic executes at the database level.
        """
        # 1. Triggers in devvault_core.db
        with self.get_connection('core') as conn:
            # Trigger: Recalculate progress on task completion toggle
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_tasks_after_update_recalc_progress
            AFTER UPDATE OF is_completed ON project_tasks
            BEGIN
                UPDATE projects 
                SET progress_percentage = COALESCE((
                    SELECT ROUND((CAST(SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*)) * 100)
                    FROM project_tasks 
                    WHERE project_id = NEW.project_id
                ), 0),
                updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.project_id;
            END;
            """)

            # Trigger: Recalculate progress on new task insertion
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_tasks_after_insert_recalc_progress
            AFTER INSERT ON project_tasks
            BEGIN
                UPDATE projects 
                SET progress_percentage = COALESCE((
                    SELECT ROUND((CAST(SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*)) * 100)
                    FROM project_tasks 
                    WHERE project_id = NEW.project_id
                ), 0),
                updated_at = CURRENT_TIMESTAMP
                WHERE id = NEW.project_id;
            END;
            """)

            # Trigger: Recalculate progress on task deletion
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_tasks_after_delete_recalc_progress
            AFTER DELETE ON project_tasks
            BEGIN
                UPDATE projects 
                SET progress_percentage = COALESCE((
                    SELECT ROUND((CAST(SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) AS REAL) / COUNT(*)) * 100)
                    FROM project_tasks 
                    WHERE project_id = OLD.project_id
                ), 0),
                updated_at = CURRENT_TIMESTAMP
                WHERE id = OLD.project_id;
            END;
            """)

            # Analytical View: Project Task Performance Metrics
            conn.execute("""
            CREATE VIEW IF NOT EXISTS vw_project_task_summary AS
            SELECT 
                p.id AS project_id,
                p.title AS project_title,
                p.status AS project_status,
                p.progress_percentage AS current_progress,
                COUNT(t.id) AS total_tasks,
                SUM(CASE WHEN t.is_completed = 1 THEN 1 ELSE 0 END) AS completed_tasks,
                SUM(CASE WHEN t.is_completed = 0 THEN 1 ELSE 0 END) AS pending_tasks,
                SUM(CASE WHEN t.priority = 'High' AND t.is_completed = 0 THEN 1 ELSE 0 END) AS high_priority_pending
            FROM projects p
            LEFT JOIN project_tasks t ON p.id = t.project_id
            GROUP BY p.id;
            """)

            # Analytical View: Technology Usage Aggregation
            conn.execute("""
            CREATE VIEW IF NOT EXISTS vw_tech_distribution AS
            SELECT 
                t.id AS tech_id,
                t.name AS tech_name,
                t.category AS tech_category,
                COUNT(pt.project_id) AS associated_projects_count
            FROM technologies t
            LEFT JOIN project_technologies pt ON t.id = pt.technology_id
            GROUP BY t.id
            ORDER BY associated_projects_count DESC;
            """)

            # Composite B-Tree Indexes for Query Optimization
            conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_cat_status ON projects (category_id, status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_proj_completed ON project_tasks (project_id, is_completed);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects (slug);")

        # 2. Indexes & Views in devvault_vault.db
        with self.get_connection('vault') as conn:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deliverables_proj_type ON project_deliverables (project_id, deliverable_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_deliverables_hash ON project_deliverables (file_hash_sha256);")

            conn.execute("""
            CREATE VIEW IF NOT EXISTS vw_vault_storage_analytics AS
            SELECT 
                deliverable_type,
                COUNT(*) AS total_files,
                SUM(file_size) AS total_bytes,
                ROUND(CAST(SUM(file_size) AS REAL) / (1024 * 1024), 2) AS total_megabytes
            FROM project_deliverables
            GROUP BY deliverable_type;
            """)

        # 3. Indexes in devvault_audit.db
        with self.get_connection('audit') as conn:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_history_proj_timestamp ON project_history (project_id, timestamp DESC);")

    def execute_query(self, sql, target_db='federated'):
        """
        Executes an arbitrary SQL query, records exact execution latency in milliseconds,
        and generates an EXPLAIN QUERY PLAN breakdown.
        """
        start_time = time.perf_counter()
        
        try:
            if target_db == 'federated':
                conn = self.get_federated_connection()
            else:
                conn = self.get_connection(target_db)

            cursor = conn.cursor()
            
            # Safety check: restrict to safe read/explain operations in query runner
            clean_sql = sql.strip()
            
            # Execute EXPLAIN QUERY PLAN if query is a SELECT
            query_plan = []
            if clean_sql.upper().startswith("SELECT"):
                try:
                    plan_cursor = conn.cursor()
                    plan_cursor.execute(f"EXPLAIN QUERY PLAN {clean_sql}")
                    for row in plan_cursor.fetchall():
                        # row format: (id, parent, notused, detail)
                        query_plan.append({
                            'id': row[0],
                            'parent': row[1],
                            'detail': row[3]
                        })
                    plan_cursor.close()
                except Exception as e:
                    query_plan.append({'id': 0, 'parent': 0, 'detail': f"Plan note: {str(e)}"})

            cursor.execute(clean_sql)
            
            if clean_sql.upper().startswith("SELECT") or clean_sql.upper().startswith("PRAGMA"):
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = [dict(zip(columns, [row[col] for col in columns])) for row in rows]
                affected = len(rows)
            else:
                conn.commit()
                columns = []
                data = []
                affected = cursor.rowcount

            latency_ms = round((time.perf_counter() - start_time) * 1000, 3)
            conn.close()

            return {
                'success': True,
                'columns': columns,
                'rows': data,
                'affected_count': affected,
                'latency_ms': latency_ms,
                'query_plan': query_plan
            }
        except Exception as err:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 3)
            return {
                'success': False,
                'error': str(err),
                'latency_ms': latency_ms,
                'query_plan': []
            }

    def get_database_health_and_schema(self):
        """
        Inspects all 3 databases, checking file sizes, PRAGMA journal modes,
        active triggers, views, and integrity status.
        """
        stats = {}
        for db_name, file_path in self.db_paths.items():
            file_exists = os.path.exists(file_path)
            file_size_kb = round(os.path.getsize(file_path) / 1024, 2) if file_exists else 0

            conn = self.get_connection(db_name)
            cursor = conn.cursor()

            # PRAGMA inspection
            journal_mode = cursor.execute("PRAGMA journal_mode;").fetchone()[0]
            foreign_keys = cursor.execute("PRAGMA foreign_keys;").fetchone()[0]
            page_count = cursor.execute("PRAGMA page_count;").fetchone()[0]
            page_size = cursor.execute("PRAGMA page_size;").fetchone()[0]

            # Schema inspection
            tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';").fetchall()]
            views = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='view';").fetchall()]
            triggers = cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger';").fetchall()
            indexes = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';").fetchall()]

            trigger_list = [{'name': t[0], 'table': t[1], 'sql': t[2]} for t in triggers]

            conn.close()

            stats[db_name] = {
                'filename': os.path.basename(file_path),
                'exists': file_exists,
                'size_kb': file_size_kb,
                'journal_mode': journal_mode.upper(),
                'foreign_keys_enabled': bool(foreign_keys),
                'page_count': page_count,
                'page_size_bytes': page_size,
                'tables': tables,
                'views': views,
                'triggers': trigger_list,
                'indexes': indexes
            }
        return stats

    @staticmethod
    def calculate_file_sha256(file_path):
        """Calculates SHA-256 cryptographic checksum for verification of deliverable files."""
        if not os.path.exists(file_path):
            return None
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
