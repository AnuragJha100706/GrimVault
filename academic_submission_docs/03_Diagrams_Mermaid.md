# DEVVAULT: ADVANCED DATABASE SYSTEM ARCHITECTURE & DESIGN DIAGRAMS (MERMAID.JS)
## Comprehensive Diagram Suite for ADBMS Evaluation, Report, and Defense

This document provides clean, renderable **Mermaid.js** code blocks representing the **DevVault** partitioned database architecture, relational schema, procedural triggers, data flow, and optimization pipelines.

---

## 1. TRI-PARTITIONED MULTI-DATABASE TOPOLOGY
*Illustrates the physical separation of concerns across the three partitioned SQLite files, SQLAlchemy binds, and the federated cross-database connection.*

```mermaid
flowchart TD
    subgraph ClientLayer ["Client / Browser Presentation Layer"]
        UI["Web Browser (Bootstrap 5, Chart.js, Vanilla ES6+)"]
    end

    subgraph AppLayer ["Flask 3.x Application Tier"]
        CTRL["Flask Controllers & Routing (app.py)"]
        ORM["SQLAlchemy Multi-Bind Engine"]
        MGR["ADBMS Manager (adbms_service.py)"]
        FED["Federation Engine (ATTACH DATABASE)"]
    end

    subgraph PartitionLayer ["ADBMS Physical Database Storage Tier"]
        subgraph CoreDB ["Partition 1: devvault_core.db"]
            direction TB
            T_PROJ["projects (Metadata & Progress)"]
            T_CAT["project_categories"]
            T_TECH["technologies & project_technologies"]
            T_DOC["project_documents (Abstract, Specs)"]
            T_TASK["project_tasks (Milestones)"]
            T_NOTE["project_notes (Dev Journals)"]
            T_SET["system_settings"]
            TRG_TASK["⚡ Triggers: trg_tasks_recalc_progress"]
            VW_TASK["📊 View: vw_project_task_summary"]
            VW_TECH["📊 View: vw_tech_distribution"]
        end

        subgraph VaultDB ["Partition 2: devvault_vault.db"]
            direction TB
            T_DELIV["project_deliverables"]
            F_SHA["SHA-256 Cryptographic Hashes"]
            F_PATH["Local Filesystem Pointers (/uploads/)"]
            VW_VAULT["📊 View: vw_vault_storage_analytics"]
        end

        subgraph AuditDB ["Partition 3: devvault_audit.db"]
            direction TB
            T_HIST["project_history (Append-Only)"]
            T_CDC["database_change_log (DDL/DML CDC)"]
            IDX_TIME["⚡ B-Tree Index: idx_history_proj_timestamp"]
        end
    end

    UI <-->|HTTP / JSON / AJAX| CTRL
    CTRL --> ORM
    CTRL --> MGR
    MGR --> FED
    ORM -->|Default Bind| CoreDB
    ORM -->|Bind: 'vault'| VaultDB
    ORM -->|Bind: 'audit'| AuditDB
    FED -.->|ATTACH 'devvault_vault.db' AS vault_db| VaultDB
    FED -.->|ATTACH 'devvault_audit.db' AS audit_db| AuditDB
```

---

## 2. ENTITY-RELATIONSHIP (ER) DIAGRAM
*Relational schema representing all 11 tables across the partitioned databases, indicating primary keys, foreign keys, SHA-256 hashes, and cardinalities.*

```mermaid
erDiagram
    PROJECT_CATEGORIES ||--o{ PROJECTS : "categorizes (1:N)"
    PROJECTS ||--o{ PROJECT_TECHNOLOGIES : "associates (1:N)"
    TECHNOLOGIES ||--o{ PROJECT_TECHNOLOGIES : "linked via (1:N)"
    PROJECTS ||--|| PROJECT_DOCUMENTS : "specifies (1:1)"
    PROJECTS ||--o{ PROJECT_DELIVERABLES : "vaults across DBs (1:N)"
    PROJECTS ||--o{ PROJECT_NOTES : "records (1:N)"
    PROJECTS ||--o{ PROJECT_TASKS : "tracks (1:N)"
    PROJECTS ||--o{ PROJECT_HISTORY : "audits across DBs (1:N)"

    PROJECT_CATEGORIES {
        int id PK
        string name UK
        string description
    }

    PROJECTS {
        int id PK
        string title
        string slug UK
        string short_description
        int category_id FK
        string status
        int progress_percentage
        string github_url
        string live_url
        date start_date
        date end_date
        timestamp created_at
        timestamp updated_at
        int github_stars
        int github_forks
    }

    TECHNOLOGIES {
        int id PK
        string name UK
        string category
        string icon_class
        string badge_color
    }

    PROJECT_TECHNOLOGIES {
        int project_id PK,FK
        int technology_id PK,FK
    }

    PROJECT_DOCUMENTS {
        int id PK
        int project_id FK,UK
        text abstract
        text problem_statement
        text objectives
        text system_requirements
        text architecture_notes
        text readme_content
    }

    PROJECT_TASKS {
        int id PK
        int project_id FK
        string task_name
        boolean is_completed
        string priority
        date due_date
    }

    PROJECT_NOTES {
        int id PK
        int project_id FK
        string title
        text content
        string note_type
        timestamp created_at
    }

    PROJECT_DELIVERABLES {
        int id PK
        int project_id FK
        string title
        string deliverable_type
        string file_path
        int file_size
        string file_hash_sha256
        string version
        timestamp uploaded_at
        text notes
    }

    PROJECT_HISTORY {
        int id PK
        int project_id FK
        string action_type
        text description
        string severity
        timestamp timestamp
    }

    DATABASE_CHANGE_LOG {
        int id PK
        string target_database
        string table_name
        string operation
        int record_id
        text details
        timestamp timestamp
    }
```

---

## 3. PROCEDURAL SQLITE TRIGGER EXECUTION SEQUENCE
*Illustrates how native engine triggers execute directly within the SQLite Virtual Database Engine (VDBE) upon task completion.*

```mermaid
sequenceDiagram
    autonumber
    actor User as Developer / Evaluator
    participant UI as Browser (Workspace / Studio)
    participant Flask as Flask Controller (app.py)
    participant SQLite as SQLite Core Engine (C-VDBE)
    participant Tasks as Table: project_tasks
    participant Projects as Table: projects
    participant Audit as Partition: devvault_audit.db

    User->>UI: Clicks Milestone Checkbox (Task #5)
    UI->>Flask: POST /task/5/toggle (Fetch API JSON)
    Flask->>SQLite: UPDATE project_tasks SET is_completed = 1 WHERE id = 5;
    SQLite->>Tasks: Writes row update to WAL buffer
    Note over SQLite: Event Detected: AFTER UPDATE OF is_completed
    SQLite->>SQLite: Fire Trigger: trg_tasks_after_update_recalc_progress
    SQLite->>Tasks: SELECT COUNT(*), SUM(is_completed) WHERE project_id = 1;
    Tasks-->>SQLite: Returns 6 total tasks, 6 completed
    SQLite->>Projects: UPDATE projects SET progress_percentage = 100, updated_at = NOW();
    SQLite-->>Flask: Transaction Committed (Engine-Enforced)
    Flask->>Audit: INSERT INTO project_history (Task Toggled, Progress 100%)
    Flask-->>UI: 200 OK {success: true, progress_percentage: 100}
    UI->>User: DOM progress bar animates to 100% (Instant)
```

---

## 4. DATA FLOW DIAGRAM (DFD LEVEL 0 - CONTEXT DIAGRAM)
*High-level context diagram showing external entities and interactions with DevVault.*

```mermaid
flowchart TD
    User(["Student Developer / Researcher"])
    Examiner(["External Viva Examiner / Guide"])
    GitHubAPI(["GitHub REST API Service"])

    subgraph DevVaultSystem ["DevVault: ADBMS Repository & Deliverables System"]
        CoreEngine["DevVault Core Engine\n(Multi-Database Partition Manager)"]
    end

    User -->|1. Creates projects, tasks & dev notes| CoreEngine
    User -->|2. Uploads Reports, PPTs, Code ZIPs| CoreEngine
    User -->|3. Syncs GitHub repositories & stars| CoreEngine
    CoreEngine -->|4. Generates live KPI dashboard & task metrics| User

    Examiner -->|5. Inspects submission checklist & SHA-256 hashes| CoreEngine
    Examiner -->|6. Generates printable academic synopsis| CoreEngine
    Examiner -->|7. Executes live queries in Database Studio| CoreEngine

    CoreEngine <-->|8. Authenticates & fetches repo metrics, commits| GitHubAPI
```

---

## 5. DATA FLOW DIAGRAM (DFD LEVEL 1 - DETAILED PROCESS DECOMPOSITION)
*Detailed subsystem decomposition of DevVault data flows.*

```mermaid
flowchart TD
    User(["Student Developer"])

    subgraph Process1 ["Process 1.0: Project & Metadata Management"]
        P1["1.1 Project CRUD & Slug Generation"]
        P2["1.2 Tech Taxonomy Tagging"]
    end

    subgraph Process2 ["Process 2.0: Academic Vault & Cryptographic Verification"]
        P3["2.1 File Ingestion & secure_filename"]
        P4["2.2 SHA-256 Hash Computation"]
        P5["2.3 Submission Readiness Audit"]
    end

    subgraph Process3 ["Process 3.0: Engine Automation & Tracking"]
        P6["3.1 Milestone Task Toggle"]
        P7["3.2 SQLite Trigger Progress Recalculation"]
        P8["3.3 Append-Only Audit Logging"]
    end

    subgraph Process4 ["Process 4.0: ADBMS Studio & Query Optimization"]
        P9["4.1 Query Parser & Execution Timer"]
        P10["4.2 EXPLAIN QUERY PLAN Extraction"]
        P11["4.3 Cross-Database ATTACH Federation"]
    end

    D1[("devvault_core.db")]
    D2[("devvault_vault.db")]
    D3[("devvault_audit.db")]
    FS[("Local File Storage /uploads/")]

    User -->|Submit project form| P1
    P1 -->|Write project records| D1
    P2 -->|Link tech associations| D1

    User -->|Upload Report / PPT file| P3
    P3 -->|Save physical binary| FS
    P3 --> P4
    P4 -->|Write deliverable manifest & SHA256| D2
    D2 --> P5

    User -->|Toggle task completion| P6
    P6 -->|Write task status| D1
    D1 --> P7
    P7 -->|Update progress_percentage| D1
    P7 --> P8
    P8 -->|Write audit trail entry| D3

    User -->|Execute custom SQL query| P9
    P9 --> P10
    P9 --> P11
    P11 <-->|Federated SELECT| D1
    P11 <-->|Federated SELECT| D2
    P11 <-->|Federated SELECT| D3
```

---

## 6. QUERY OPTIMIZATION: B-TREE INDEX vs. FULL TABLE SCAN
*Illustrates the Virtual Database Engine (VDBE) search path through the composite index.*

```mermaid
flowchart TD
    Query["Incoming SQL Query:\nSELECT * FROM project_tasks\nWHERE project_id = 2 AND is_completed = 1;"]

    subgraph UnindexedPath ["Scenario A: Without Composite Index"]
        SCAN["VDBE Opcode: SCAN TABLE project_tasks"]
        PAGES["Sequential I/O: Reads every page from disk\nCost: O(N) linear time complexity"]
    end

    subgraph IndexedPath ["Scenario B: With Composite Index idx_tasks_proj_completed"]
        BTree["B-Tree Root Node (project_id, is_completed)"]
        Level1["Intermediate B-Tree Nodes"]
        Leaf["Leaf Node: Exact RowID Pointer"]
        ROW["Direct Random Access to Target Page\nCost: O(log N) logarithmic complexity"]
    end

    Query -->|No index available| SCAN
    SCAN --> PAGES
    Query -->|Optimizer matches composite index| BTree
    BTree --> Level1
    Level1 --> Leaf
    Leaf --> ROW
```

---

## 7. UML USE CASE DIAGRAM
*Actor use cases across project tracking, academic file management, and database studio exploration.*

```mermaid
flowchart LR
    Student(("Student Developer"))
    Examiner(("External Examiner"))
    SystemAdmin(("System / Evaluator"))

    subgraph UseCases ["DevVault Functional Capabilities"]
        UC1(["Create & Manage Projects"])
        UC2(["Upload Academic Deliverables (PDF, PPT, ZIP)"])
        UC3(["Verify SHA-256 Checksums"])
        UC4(["Sync GitHub Repositories & README"])
        UC5(["Toggle Tasks with Automatic Trigger Progress Sync"])
        UC6(["Generate One-Click Academic Synopsis Report"])
        UC7(["Execute SQL Queries & Inspect Query Plans"])
        UC8(["Run Database PRAGMA Health Checks"])
        UC9(["Download Compressed Multi-DB Backup (.zip)"])
    end

    Student --> UC1
    Student --> UC2
    Student --> UC4
    Student --> UC5
    Student --> UC6
    Student --> UC9

    Examiner --> UC3
    Examiner --> UC6
    Examiner --> UC7
    Examiner --> UC8

    SystemAdmin --> UC7
    SystemAdmin --> UC8
    SystemAdmin --> UC9
```
