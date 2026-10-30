# DEVVAULT: 32 ADVANCED DATABASE MANAGEMENT SYSTEMS (ADBMS) VIVA QUESTIONS & ANSWERS
## Comprehensive Technical Defense Guide for External Academic Examination

**Candidate & Project Architect:** Anurag Jha  
**GitHub Profile:** [https://github.com/AnuragJha100706](https://github.com/AnuragJha100706)  
**Local Projects Root:** `E:\COMPLETE PROJECT`  
**Subject:** Advanced Database Management Systems (ADBMS)

---

### SECTION 1: ADBMS ARCHITECTURE & PARTITIONED STORAGE

#### Q1: What is the architectural justification for partitioning DevVault across three distinct SQLite databases instead of using a single database file?
**Answer:**  
In Advanced Database Management Systems, horizontal and functional partitioning decouples data structures based on access frequency, growth velocity, and security requirements. DevVault divides the storage tier into three isolated catalogs:
1. `devvault_core.db`: Contains high-frequency transactional metadata (projects, tasks, developer notes, documentation).
2. `devvault_vault.db`: Dedicated partition storing file deliverable manifests, MIME types, and SHA-256 cryptographic hashes. Decoupling file metadata prevents file table scans from polluting the transactional page cache.
3. `devvault_audit.db`: An append-only partition hosting `project_history` and `database_change_log` (CDC). Isolating audit logs guarantees audit immutability—even if a rollback occurs on the core catalog, audit history cannot be compromised.

#### Q2: How does SQLite support multi-database transactions without a running server daemon?
**Answer:**  
SQLite supports multi-database transactions through its Virtual Database Engine (VDBE) and the `ATTACH DATABASE` command. When multiple databases are attached within a single connection, SQLite utilizes a two-phase commit (2PC) protocol managed through a master journal file (`-mj`). This ensures atomic ACID properties across all attached databases simultaneously.

#### Q3: What is Database Federation in SQLite, and how is it utilized in DevVault?
**Answer:**  
Database Federation allows a single query engine to join data residing in physically separate database catalogs as if they were in a single schema. In DevVault, the `ADBMSManager.get_federated_connection()` issues:
```sql
ATTACH DATABASE 'instance/devvault_vault.db' AS vault_db;
ATTACH DATABASE 'instance/devvault_audit.db' AS audit_db;
```
This enables unified cross-database SQL queries joining `projects` (in `core`) with `vault_db.project_deliverables` and `audit_db.project_history` in a single query execution.

#### Q4: How does Flask-SQLAlchemy interact with multiple partitioned SQLite files?
**Answer:**  
Flask-SQLAlchemy manages partitioned databases using the `SQLALCHEMY_BINDS` configuration dictionary. In DevVault:
- Default bind: `app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/devvault_core.db'`
- Secondary binds: `app.config['SQLALCHEMY_BINDS'] = {'vault': 'sqlite:///instance/devvault_vault.db', 'audit': 'sqlite:///instance/devvault_audit.db'}`  
Models specify their target partition via `__bind_key__ = 'vault'` or `__bind_key__ = 'audit'`. Cross-database entity traversal is achieved through Python descriptor properties that query target models dynamically by foreign key.

---

### SECTION 2: CONCURRENCY CONTROL, WRITE-AHEAD LOGGING (WAL) & PRAGMA TUNING

#### Q5: What is Write-Ahead Logging (WAL) mode, and why is it superior to the default Rollback Journal in SQLite?
**Answer:**  
In the default rollback journal mode, writing requires an exclusive lock on the entire database file, which blocks all concurrent readers. In **WAL mode** (`PRAGMA journal_mode = WAL;`):
- Changes are appended to a separate `-wal` file instead of directly overwriting database pages.
- **Readers do not block writers, and writers do not block readers.**
- Readers access pages from the main database file or the `-wal` file using a WAL index (`-shm`), achieving concurrent multi-threaded read throughput.

#### Q6: Explain what a WAL Checkpoint is and how it works in DevVault.
**Answer:**  
A checkpoint is the process of transferring accumulated transaction pages from the write-ahead log (`-wal`) back into the main `.db` database file. DevVault supports passive checkpointing via `PRAGMA wal_checkpoint(PASSIVE);` in the Database Studio, which flushes as many WAL pages as possible without blocking active read transactions.

#### Q7: Why are foreign key constraints disabled by default in SQLite, and how did you enforce them?
**Answer:**  
For backward compatibility with early SQLite 2.x releases, SQLite leaves foreign key enforcement disabled by default. DevVault strictly enforces referential integrity at the database engine level by executing `PRAGMA foreign_keys = ON;` on every database connection initialization inside `adbms_service.py`.

#### Q8: What does `PRAGMA synchronous = NORMAL;` achieve?
**Answer:**  
`PRAGMA synchronous` controls how aggressively SQLite synchronizes pages to physical storage. In WAL mode, setting synchronous to `NORMAL` ensures that disk syncs occur only during WAL checkpoints and critical commits, which drastically reduces disk I/O latency on modern solid-state drives while retaining full durability against application crashes.

---

### SECTION 3: PROCEDURAL DATABASE TRIGGERS (ECA PARADIGM)

#### Q9: What is the Event-Condition-Action (ECA) rule paradigm in database triggers?
**Answer:**  
ECA rules define active database behavior:
- **Event:** A database modification statement (`INSERT`, `UPDATE`, `DELETE`).
- **Condition:** An optional boolean predicate (e.g., `OF is_completed`).
- **Action:** An executable sequence of SQL commands executed atomically within the database engine.

#### Q10: Describe the native SQLite trigger implemented for automatic progress recalculation.
**Answer:**  
DevVault defines `trg_tasks_after_update_recalc_progress`:
```sql
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
```
This trigger fires immediately when `is_completed` changes, recalculating the project's completion percentage directly inside the C-engine.

#### Q11: What is the advantage of using a database trigger over calculating progress in Python application code?
**Answer:**  
1. **Consistency Guarantee:** Recalculation executes even if updates are performed outside the web app (e.g., direct SQLite CLI updates, automated background migrations, or Studio queries).
2. **Race Condition Elimination:** The calculation occurs inside SQLite's internal transaction boundary, eliminating lost updates.
3. **Network & Overhead Efficiency:** Eliminates round-trip latency; no Python memory allocation or ORM deserialization is required.

#### Q12: How do the triggers handle the edge case where all tasks for a project are deleted?
**Answer:**  
In `trg_tasks_after_delete_recalc_progress`, if all tasks are deleted, the subquery `COUNT(*)` returns `NULL` or division results in `NULL`. The SQL `COALESCE(..., 0)` expression catches this condition and safely resets `progress_percentage` to `0` instead of corrupting the field with `NULL`.

---

### SECTION 4: QUERY OPTIMIZATION, VDBE & INDEXING

#### Q13: What is the SQLite Virtual Database Engine (VDBE)?
**Answer:**  
The VDBE is SQLite's register-based virtual machine. When a SQL query is submitted, the SQLite parser and query planner compile it into low-level VDBE bytecode instructions (such as `OpenRead`, `SeekGE`, `Column`, `ResultRow`). The VDBE executes this bytecode against the B-Tree storage engine to retrieve or update records.

#### Q14: Explain the difference between `SCAN TABLE` and `SEARCH TABLE USING INDEX` in `EXPLAIN QUERY PLAN`.
**Answer:**  
- `SCAN TABLE`: Indicates an unindexed **Full Table Scan**. The engine sequentially reads every disk page in the table to evaluate the `WHERE` clause, resulting in $O(N)$ linear time complexity.
- `SEARCH TABLE USING INDEX`: Indicates that the query planner traversed a balanced **B-Tree Index**, jumping directly to the matching key with $O(\log N)$ logarithmic time complexity.

#### Q15: Why did you implement composite B-Tree indexes, such as `idx_tasks_proj_completed` on `(project_id, is_completed)`?
**Answer:**  
Composite indexes store multi-column keys in hierarchical order. When querying:
```sql
SELECT * FROM project_tasks WHERE project_id = ? AND is_completed = ?;
```
A single-column index on `project_id` would still require SQLite to filter rows by `is_completed` in memory. The composite index allows the query planner to satisfy both equality predicates directly within the B-Tree index structure, producing a covering search.

#### Q16: What is the purpose of the in-app ADBMS Database Studio?
**Answer:**  
The Database Studio (`/database-studio`) provides an interactive interface to:
1. Execute raw SQL queries against individual partitions or the federated session.
2. Measure sub-millisecond query execution latency via `time.perf_counter()`.
3. Extract and visualize the `EXPLAIN QUERY PLAN` tree.
4. Run diagnostic PRAGMA health checks (`integrity_check`, `foreign_key_check`).
5. Inspect the Change Data Capture (CDC) audit trail.

---

### SECTION 5: NORMALIZATION, RELATIONAL INTEGRITY & CRYPTOGRAPHIC SECURITY

#### Q17: Prove that the DevVault relational schema is normalized up to Boyce-Codd Normal Form (BCNF).
**Answer:**  
A relation is in BCNF if, for every non-trivial functional dependency $X \rightarrow Y$, $X$ is a superkey.
- In `projects`, the functional dependencies are $id \rightarrow \text{attributes}$ and $slug \rightarrow \text{attributes}$. Since both $id$ (primary key) and $slug$ (unique key) are superkeys, BCNF is satisfied.
- In `project_technologies`, the primary key is $(project\_id, technology\_id)$. No non-prime attributes exist, so no partial dependencies exist.
- All non-prime attributes in all tables depend strictly on their respective primary keys with no transitive dependencies, satisfying 3NF and BCNF.

#### Q18: How does DevVault ensure document authenticity in the Academic Deliverables Vault?
**Answer:**  
Upon file upload, DevVault streams the physical bytes through the SHA-256 cryptographic hashing algorithm (`hashlib.sha256()`). The resulting 64-character hexadecimal checksum is stored in `devvault_vault.db` alongside the file path. During academic evaluation, the stored hash can be compared against the physical file to prove the document has not been altered or tampered with.

#### Q19: How are uploaded files protected against path traversal and file collisions?
**Answer:**  
1. `werkzeug.utils.secure_filename()` sanitizes file names by stripping dangerous relative directory characters (e.g., `../`).
2. Unique timestamp prefixes and project IDs are prepended (e.g., `1_20261030_120000_report.pdf`).
3. Files are sorted into dedicated directory trees based on deliverable type (`/static/uploads/reports`, `/ppts`, `/archives`).

#### Q20: How does the submission readiness checklist calculate completion?
**Answer:**  
The `checklist_status` property queries `devvault_vault.db` for the presence of four mandatory deliverable categories: Synopsis, Report, PPT, and Source Code ZIP. It evaluates to `True` only when all four mandatory deliverables are uploaded, allowing evaluators to verify submission readiness at a glance.

---

### SECTION 6: DUAL-DIALECT ENTERPRISE EQUIVALENCE & ORACLE PL/SQL COMPARISON

#### Q21: What is the "Mutating Table" error (`ORA-04091`) in Oracle PL/SQL, and how does your suite solve it?
**Answer:**  
In Oracle, if a row-level trigger on table $T$ attempts to query table $T$ while an `UPDATE` or `INSERT` statement is running, Oracle throws `ORA-04091: table is mutating`. DevVault's Oracle package resolves this by implementing a **Compound Trigger** (`TRG_TASKS_COMPOUND_PROGRESS`). The trigger collects affected project IDs in a PL/SQL collection during row-level execution and performs the progress recalculation once at the statement level (`AFTER STATEMENT`), when the table is no longer mutating.

#### Q22: What are Autonomous Transactions in Oracle, and why are they used for Change Data Capture (CDC)?
**Answer:**  
An autonomous transaction (`PRAGMA AUTONOMOUS_TRANSACTION`) executes in its own transaction context independent of the main transaction. If the main transaction encounters an error and issues a `ROLLBACK`, the audit entry committed in the autonomous transaction is **not rolled back**. This ensures that failed or malicious operations are permanently recorded in the audit log.

#### Q23: Compare SQLite with Oracle in terms of architecture and resource overhead.
**Answer:**  
- **SQLite:** In-process, serverless library directly embedded into the application address space. Zero network latency, zero administration, minimal footprint (< 1MB binary), ideal for embedded systems and workstation tooling.
- **Oracle Database:** Client-server multi-process architecture with background daemons (PMON, SMON, DBWn), complex System Global Area (SGA) memory, tablespace management, and sophisticated multi-tenant pluggable database support.

#### Q24: What is a Database View, and what advantages do the views in DevVault provide?
**Answer:**  
A view is a stored virtual query that does not store data itself, but dynamically retrieves records from underlying base tables. DevVault provides:
- `vw_project_task_summary`: Decouples progress aggregation logic from the web controllers.
- `vw_vault_storage_analytics`: Computes storage byte totals and megabytes dynamically.
- `vw_tech_distribution`: Provides pre-compiled analytical aggregations for Chart.js.

#### Q25: How does DevVault handle cascading deletes across partitions?
**Answer:**  
In `devvault_core.db`, foreign key definitions specify `ON DELETE CASCADE` (e.g., deleting a project automatically cascades to delete associated documents, tasks, and notes). For cross-database partitions (`devvault_vault.db` and `devvault_audit.db`), application-level controllers explicitly delete related file records and purge physical files from disk to eliminate orphan records.

#### Q26: What is Change Data Capture (CDC), and how is it implemented in `database_change_log`?
**Answer:**  
Change Data Capture tracks schema and data state changes over time. DevVault records DDL and DML operations into `devvault_audit.db.database_change_log`, storing the target database partition, table affected, operation type (`CREATE`, `UPDATE`, `INSERT`), and query preview, facilitating rigorous institutional auditing.

#### Q27: How does DevVault maintain data portability?
**Answer:**  
DevVault provides three levels of data export:
1. Single project JSON specifications (`/project/<id>/export/json`).
2. Catalog-wide summary CSV exports (`/export/projects/csv`).
3. Compressed multi-database ZIP archives (`/export/database/backup`) bundling all three SQLite database files.

#### Q28: How does the One-Click Academic Synopsis generator format documents for printing?
**Answer:**  
The `/project/<id>/synopsis` endpoint compiles Abstract, Problem Statement, Objectives, and System Requirements into a formal academic layout. CSS `@media print` directives suppress navbars and buttons, apply standardized serif typography, and insert candidate and faculty supervisor signature blocks.

#### Q29: What is the significance of the SQLite `-shm` and `-wal` files?
**Answer:**  
When WAL mode is active:
- `.db-wal`: Contains all uncommitted and recently committed transaction pages that have not yet been flushed to the main database file.
- `.db-shm`: Shared-memory index mapping WAL pages to main database pages, allowing concurrent readers to locate the most recent version of a page quickly.

#### Q30: Why is SQLite considered a full ACID-compliant database?
**Answer:**  
- **Atomicity:** All statements within a transaction succeed or all fail together.
- **Consistency:** Enforced via SQLite column data types, `CHECK` constraints, `NOT NULL`, and `FOREIGN KEY` cascades.
- **Isolation:** Provided through serializable or read-uncommitted isolation levels via WAL locks.
- **Durability:** Guaranteed using Write-Ahead Logging and OS page syncing.

#### Q31: Can SQLite handle high-traffic production workloads?
**Answer:**  
Yes. With WAL mode enabled, SQLite can sustain thousands of read transactions per second and hundreds of write transactions per second, making it ideal for workstations, developer repositories, edge nodes, and read-heavy production web services.

#### Q32: What was the most significant technical challenge encountered during the implementation of DevVault?
**Answer:**  
The most significant challenge was executing transactions and relationships across three physically separate SQLite files without causing database locking conflicts. This was solved by configuring Write-Ahead Logging (`WAL`), utilizing Flask-SQLAlchemy binds, implementing cross-database accessor properties, and developing the federated `ATTACH DATABASE` session in `adbms_service.py`.
