-- =================================================================================================
-- DEVVAULT: ADVANCED DATABASE MANAGEMENT SYSTEMS (ADBMS) SUITE
-- SCRIPT 01: SQLite Partitioned Multi-Database DDL, Triggers, Views & Federated Queries
-- =================================================================================================
-- Target Engine: SQLite 3.35+ (with WAL mode & Foreign Keys enabled)
-- Architecture: 3 Partitioned Database Catalogs
--   1. devvault_core.db   : Core relational metadata, tasks, documents, settings
--   2. devvault_vault.db  : Dedicated high-capacity deliverables vault & cryptographic hashes
--   3. devvault_audit.db  : Append-only compliance change data capture & project history
-- =================================================================================================

-- -------------------------------------------------------------------------------------------------
-- SECTION 1: PERFORMANCE PRAGMAS (Execute on every database connection)
-- -------------------------------------------------------------------------------------------------
PRAGMA journal_mode = WAL;         -- Write-Ahead Logging for high concurrent read/write throughput
PRAGMA foreign_keys = ON;          -- Strict referential integrity enforcement
PRAGMA synchronous = NORMAL;       -- Balances ACID safety with SSD I/O latency reduction
PRAGMA busy_timeout = 5000;        -- Prevent immediate "database locked" errors under lock contention
PRAGMA cache_size = -64000;        -- Allocate 64MB memory page cache for intermediate query processing


-- -------------------------------------------------------------------------------------------------
-- SECTION 2: CORE DATABASE SCHEMA (devvault_core.db)
-- -------------------------------------------------------------------------------------------------

-- Table 1: Project Categories
CREATE TABLE IF NOT EXISTS project_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(80) NOT NULL UNIQUE,
    description VARCHAR(255)
);

-- Table 2: Projects
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(150) NOT NULL,
    slug VARCHAR(180) NOT NULL UNIQUE,
    short_description VARCHAR(300),
    category_id INTEGER,
    status VARCHAR(50) DEFAULT 'Idea', -- 'Idea', 'In Progress', 'Completed', 'On Hold', 'Archived'
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    github_url VARCHAR(255),
    live_url VARCHAR(255),
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    github_stars INTEGER DEFAULT 0,
    github_forks INTEGER DEFAULT 0,
    github_open_issues INTEGER DEFAULT 0,
    github_default_branch VARCHAR(50) DEFAULT 'main',
    github_latest_commit_sha VARCHAR(40),
    github_latest_commit_msg VARCHAR(255),
    github_latest_commit_author VARCHAR(100),
    github_synced_at TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES project_categories (id) ON DELETE SET NULL
);

-- Table 3: Technologies
CREATE TABLE IF NOT EXISTS technologies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(60) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL, -- 'Language', 'Framework', 'Database', 'Tool'
    icon_class VARCHAR(80) DEFAULT 'bi bi-code-slash',
    badge_color VARCHAR(20) DEFAULT '#0d6efd'
);

-- Table 4: Project-Technologies Association (Many-to-Many Bridge Table)
CREATE TABLE IF NOT EXISTS project_technologies (
    project_id INTEGER NOT NULL,
    technology_id INTEGER NOT NULL,
    PRIMARY KEY (project_id, technology_id),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (technology_id) REFERENCES technologies (id) ON DELETE CASCADE
);

-- Table 5: Project Documents (1-to-1 Specification)
CREATE TABLE IF NOT EXISTS project_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL UNIQUE,
    abstract TEXT,
    problem_statement TEXT,
    objectives TEXT,
    system_requirements TEXT,
    architecture_notes TEXT,
    readme_content TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- Table 6: Project Tasks & Milestones
CREATE TABLE IF NOT EXISTS project_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    task_name VARCHAR(200) NOT NULL,
    is_completed BOOLEAN DEFAULT 0 CHECK (is_completed IN (0, 1)),
    priority VARCHAR(20) DEFAULT 'Medium', -- 'Low', 'Medium', 'High'
    due_date DATE,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- Table 7: Developer Notes & Journal
CREATE TABLE IF NOT EXISTS project_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title VARCHAR(150) NOT NULL,
    content TEXT NOT NULL,
    note_type VARCHAR(50) DEFAULT 'Dev Log', -- 'Dev Log', 'Bug Fix', 'Idea', 'Todo'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

-- Table 8: System Configuration Settings
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(80) NOT NULL UNIQUE,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- -------------------------------------------------------------------------------------------------
-- SECTION 3: VAULT DATABASE SCHEMA (devvault_vault.db)
-- -------------------------------------------------------------------------------------------------

-- Table 9: Project Deliverables & Academic Attachments
CREATE TABLE IF NOT EXISTS project_deliverables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title VARCHAR(150) NOT NULL,
    deliverable_type VARCHAR(80) NOT NULL, -- 'Project Report', 'Presentation PPT', 'Synopsis/Proposal', etc.
    file_path VARCHAR(300) NOT NULL,
    file_size INTEGER DEFAULT 0,          -- Size in bytes
    file_hash_sha256 VARCHAR(64),         -- SHA-256 cryptographic checksum for tamper verification
    version VARCHAR(50) DEFAULT 'v1.0',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);


-- -------------------------------------------------------------------------------------------------
-- SECTION 4: AUDIT DATABASE SCHEMA (devvault_audit.db)
-- -------------------------------------------------------------------------------------------------

-- Table 10: Immutable Project History & Audit Log
CREATE TABLE IF NOT EXISTS project_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    action_type VARCHAR(50) NOT NULL,     -- 'Created', 'Status Updated', 'File Uploaded', etc.
    description TEXT NOT NULL,
    severity VARCHAR(20) DEFAULT 'INFO',  -- 'INFO', 'WARNING', 'SUCCESS', 'CRITICAL'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 11: Change Data Capture (CDC) Log
CREATE TABLE IF NOT EXISTS database_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_database VARCHAR(50) NOT NULL, -- 'core', 'vault', 'audit'
    table_name VARCHAR(80) NOT NULL,
    operation VARCHAR(20) NOT NULL,       -- 'INSERT', 'UPDATE', 'DELETE', 'CREATE'
    record_id INTEGER,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- -------------------------------------------------------------------------------------------------
-- SECTION 5: COMPOSITE B-TREE INDEXES FOR QUERY OPTIMIZATION
-- -------------------------------------------------------------------------------------------------

-- In devvault_core.db:
CREATE INDEX IF NOT EXISTS idx_projects_cat_status ON projects (category_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_proj_completed ON project_tasks (project_id, is_completed);
CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects (slug);

-- In devvault_vault.db:
CREATE INDEX IF NOT EXISTS idx_deliverables_proj_type ON project_deliverables (project_id, deliverable_type);
CREATE INDEX IF NOT EXISTS idx_deliverables_hash ON project_deliverables (file_hash_sha256);

-- In devvault_audit.db:
CREATE INDEX IF NOT EXISTS idx_history_proj_timestamp ON project_history (project_id, timestamp DESC);


-- -------------------------------------------------------------------------------------------------
-- SECTION 6: PROCEDURAL SQLite ECA (EVENT-CONDITION-ACTION) TRIGGERS
-- -------------------------------------------------------------------------------------------------

-- Trigger A: Recalculate progress percentage automatically after task update
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

-- Trigger B: Recalculate progress percentage automatically after new task insertion
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

-- Trigger C: Recalculate progress percentage automatically after task deletion
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


-- -------------------------------------------------------------------------------------------------
-- SECTION 7: ANALYTICAL & REPORTING VIEWS
-- -------------------------------------------------------------------------------------------------

-- View A: Task performance metrics per project (in devvault_core.db)
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

-- View B: Technology adoption across repository (in devvault_core.db)
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

-- View C: Vault deliverable storage distribution (in devvault_vault.db)
CREATE VIEW IF NOT EXISTS vw_vault_storage_analytics AS
SELECT 
    deliverable_type,
    COUNT(*) AS total_files,
    SUM(file_size) AS total_bytes,
    ROUND(CAST(SUM(file_size) AS REAL) / (1024 * 1024), 2) AS total_megabytes
FROM project_deliverables
GROUP BY deliverable_type;


-- -------------------------------------------------------------------------------------------------
-- SECTION 8: FEDERATED CROSS-DATABASE QUERIES (Using SQLite ATTACH DATABASE)
-- -------------------------------------------------------------------------------------------------

-- To execute in SQLite CLI or Python session connected to devvault_core.db:
-- ATTACH DATABASE 'devvault_vault.db' AS vault_db;
-- ATTACH DATABASE 'devvault_audit.db' AS audit_db;

-- Demonstration Query 1: Unified Project Health & Deliverables Audit (Cross-Database Join)
/*
SELECT 
    p.id AS project_id,
    p.title AS project_name,
    p.status AS project_status,
    p.progress_percentage,
    COUNT(DISTINCT v.id) AS uploaded_deliverables,
    COUNT(DISTINCT h.id) AS audit_trail_count,
    MAX(h.timestamp) AS last_audited_action
FROM projects p
LEFT JOIN vault_db.project_deliverables v ON p.id = v.project_id
LEFT JOIN audit_db.project_history h ON p.id = h.project_id
GROUP BY p.id
ORDER BY p.id ASC;
*/

-- Demonstration Query 2: EXPLAIN QUERY PLAN (Verifying B-Tree Index Utilization)
/*
EXPLAIN QUERY PLAN
SELECT p.id, p.title, t.task_name, t.priority
FROM projects p
JOIN project_tasks t ON p.id = t.project_id
WHERE p.category_id = 1 AND p.status = 'In Progress' AND t.is_completed = 0;
*/
-- Expected VDBE Plan:
-- SEARCH p USING INDEX idx_projects_cat_status (category_id=? AND status=?)
-- SEARCH t USING INDEX idx_tasks_proj_completed (project_id=? AND is_completed=?)

