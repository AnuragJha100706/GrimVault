-- =================================================================================================
-- DEVVAULT: ADVANCED DATABASE MANAGEMENT SYSTEMS (ADBMS) SUITE
-- SCRIPT 02: Oracle 19c/21c PL/SQL Enterprise Package, Procedures & Compound Triggers
-- =================================================================================================
-- Dialect: Oracle PL/SQL (Enterprise Edition)
-- Purpose: Academic equivalence implementation demonstrating enterprise stored procedures,
--          compound triggers (preventing ORA-04091 mutating table errors), cursors,
--          and autonomous transaction auditing.
-- =================================================================================================

SET SERVEROUTPUT ON SIZE UNLIMITED;

-- -------------------------------------------------------------------------------------------------
-- SECTION 1: ORACLE DDL DEFINITIONS WITH SEQUENCES & PARTITIONS
-- -------------------------------------------------------------------------------------------------

-- Sequences for Primary Keys
CREATE SEQUENCE SEQ_PROJECT_CATEGORIES START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_PROJECTS START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_TECHNOLOGIES START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_PROJECT_DOCUMENTS START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_PROJECT_DELIVERABLES START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_PROJECT_TASKS START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_PROJECT_NOTES START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_PROJECT_HISTORY START WITH 1 INCREMENT BY 1 NOCACHE;
CREATE SEQUENCE SEQ_DATABASE_CHANGE_LOG START WITH 1 INCREMENT BY 1 NOCACHE;

-- 1. Project Categories
CREATE TABLE PROJECT_CATEGORIES (
    ID NUMBER DEFAULT SEQ_PROJECT_CATEGORIES.NEXTVAL PRIMARY KEY,
    NAME VARCHAR2(80) NOT NULL UNIQUE,
    DESCRIPTION VARCHAR2(255)
);

-- 2. Projects (Partitioned by Range on CREATED_AT or List on STATUS)
CREATE TABLE PROJECTS (
    ID NUMBER DEFAULT SEQ_PROJECTS.NEXTVAL PRIMARY KEY,
    TITLE VARCHAR2(150) NOT NULL,
    SLUG VARCHAR2(180) NOT NULL UNIQUE,
    SHORT_DESCRIPTION VARCHAR2(300),
    CATEGORY_ID NUMBER REFERENCES PROJECT_CATEGORIES(ID) ON DELETE SET NULL,
    STATUS VARCHAR2(50) DEFAULT 'Idea' CHECK (STATUS IN ('Idea', 'In Progress', 'Completed', 'On Hold', 'Archived')),
    PROGRESS_PERCENTAGE NUMBER(3) DEFAULT 0 CHECK (PROGRESS_PERCENTAGE BETWEEN 0 AND 100),
    GITHUB_URL VARCHAR2(255),
    LIVE_URL VARCHAR2(255),
    START_DATE DATE,
    END_DATE DATE,
    CREATED_AT TIMESTAMP DEFAULT SYSTIMESTAMP,
    UPDATED_AT TIMESTAMP DEFAULT SYSTIMESTAMP,
    GITHUB_STARS NUMBER DEFAULT 0,
    GITHUB_FORKS NUMBER DEFAULT 0,
    GITHUB_OPEN_ISSUES NUMBER DEFAULT 0,
    GITHUB_DEFAULT_BRANCH VARCHAR2(50) DEFAULT 'main',
    GITHUB_LATEST_COMMIT_SHA VARCHAR2(40),
    GITHUB_LATEST_COMMIT_MSG VARCHAR2(255),
    GITHUB_LATEST_COMMIT_AUTHOR VARCHAR2(100),
    GITHUB_SYNCED_AT TIMESTAMP
);

-- 3. Technologies
CREATE TABLE TECHNOLOGIES (
    ID NUMBER DEFAULT SEQ_TECHNOLOGIES.NEXTVAL PRIMARY KEY,
    NAME VARCHAR2(60) NOT NULL UNIQUE,
    CATEGORY VARCHAR2(50) NOT NULL CHECK (CATEGORY IN ('Language', 'Framework', 'Database', 'Tool')),
    ICON_CLASS VARCHAR2(80) DEFAULT 'bi bi-code-slash',
    BADGE_COLOR VARCHAR2(20) DEFAULT '#0d6efd'
);

-- 4. Many-to-Many Bridge Table
CREATE TABLE PROJECT_TECHNOLOGIES (
    PROJECT_ID NUMBER NOT NULL REFERENCES PROJECTS(ID) ON DELETE CASCADE,
    TECHNOLOGY_ID NUMBER NOT NULL REFERENCES TECHNOLOGIES(ID) ON DELETE CASCADE,
    PRIMARY KEY (PROJECT_ID, TECHNOLOGY_ID)
);

-- 5. Project Documents
CREATE TABLE PROJECT_DOCUMENTS (
    ID NUMBER DEFAULT SEQ_PROJECT_DOCUMENTS.NEXTVAL PRIMARY KEY,
    PROJECT_ID NUMBER NOT NULL UNIQUE REFERENCES PROJECTS(ID) ON DELETE CASCADE,
    ABSTRACT CLOB,
    PROBLEM_STATEMENT CLOB,
    OBJECTIVES CLOB,
    SYSTEM_REQUIREMENTS CLOB,
    ARCHITECTURE_NOTES CLOB,
    README_CONTENT CLOB
);

-- 6. Project Tasks
CREATE TABLE PROJECT_TASKS (
    ID NUMBER DEFAULT SEQ_PROJECT_TASKS.NEXTVAL PRIMARY KEY,
    PROJECT_ID NUMBER NOT NULL REFERENCES PROJECTS(ID) ON DELETE CASCADE,
    TASK_NAME VARCHAR2(200) NOT NULL,
    IS_COMPLETED NUMBER(1) DEFAULT 0 CHECK (IS_COMPLETED IN (0, 1)),
    PRIORITY VARCHAR2(20) DEFAULT 'Medium' CHECK (PRIORITY IN ('Low', 'Medium', 'High')),
    DUE_DATE DATE
);

-- 7. Project Notes
CREATE TABLE PROJECT_NOTES (
    ID NUMBER DEFAULT SEQ_PROJECT_NOTES.NEXTVAL PRIMARY KEY,
    PROJECT_ID NUMBER NOT NULL REFERENCES PROJECTS(ID) ON DELETE CASCADE,
    TITLE VARCHAR2(150) NOT NULL,
    CONTENT CLOB NOT NULL,
    NOTE_TYPE VARCHAR2(50) DEFAULT 'Dev Log' CHECK (NOTE_TYPE IN ('Dev Log', 'Bug Fix', 'Idea', 'Todo')),
    CREATED_AT TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- 8. Project Deliverables Vault
CREATE TABLE PROJECT_DELIVERABLES (
    ID NUMBER DEFAULT SEQ_PROJECT_DELIVERABLES.NEXTVAL PRIMARY KEY,
    PROJECT_ID NUMBER NOT NULL REFERENCES PROJECTS(ID) ON DELETE CASCADE,
    TITLE VARCHAR2(150) NOT NULL,
    DELIVERABLE_TYPE VARCHAR2(80) NOT NULL,
    FILE_PATH VARCHAR2(300) NOT NULL,
    FILE_SIZE NUMBER DEFAULT 0,
    FILE_HASH_SHA256 VARCHAR2(64),
    VERSION VARCHAR2(50) DEFAULT 'v1.0',
    UPLOADED_AT TIMESTAMP DEFAULT SYSTIMESTAMP,
    NOTES CLOB
);

-- 9. Immutable Project History
CREATE TABLE PROJECT_HISTORY (
    ID NUMBER DEFAULT SEQ_PROJECT_HISTORY.NEXTVAL PRIMARY KEY,
    PROJECT_ID NUMBER NOT NULL REFERENCES PROJECTS(ID) ON DELETE CASCADE,
    ACTION_TYPE VARCHAR2(50) NOT NULL,
    DESCRIPTION CLOB NOT NULL,
    SEVERITY VARCHAR2(20) DEFAULT 'INFO',
    TIMESTAMP TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- 10. Change Data Capture Log
CREATE TABLE DATABASE_CHANGE_LOG (
    ID NUMBER DEFAULT SEQ_DATABASE_CHANGE_LOG.NEXTVAL PRIMARY KEY,
    TARGET_DATABASE VARCHAR2(50) NOT NULL,
    TABLE_NAME VARCHAR2(80) NOT NULL,
    OPERATION VARCHAR2(20) NOT NULL,
    RECORD_ID NUMBER,
    DETAILS CLOB,
    TIMESTAMP TIMESTAMP DEFAULT SYSTIMESTAMP
);

-- Composite B-Tree Indexes
CREATE INDEX IDX_ORA_PROJ_CAT_STAT ON PROJECTS (CATEGORY_ID, STATUS);
CREATE INDEX IDX_ORA_TASKS_PROJ_COMP ON PROJECT_TASKS (PROJECT_ID, IS_COMPLETED);
CREATE INDEX IDX_ORA_DELIV_PROJ_TYPE ON PROJECT_DELIVERABLES (PROJECT_ID, DELIVERABLE_TYPE);


-- -------------------------------------------------------------------------------------------------
-- SECTION 2: PL/SQL PACKAGE SPECIFICATION (PKG_DEVVAULT_ADMIN)
-- -------------------------------------------------------------------------------------------------

CREATE OR REPLACE PACKAGE PKG_DEVVAULT_ADMIN AS
    -- Custom Record and Table Types
    TYPE T_READINESS_RECORD IS RECORD (
        PROJECT_ID          NUMBER,
        HAS_SYNOPSIS        BOOLEAN,
        HAS_REPORT          BOOLEAN,
        HAS_PPT             BOOLEAN,
        HAS_SOURCE_CODE     BOOLEAN,
        READINESS_PERCENT   NUMBER
    );

    -- Stored Procedures
    PROCEDURE PRC_RECALCULATE_PROGRESS(
        p_project_id   IN  NUMBER,
        p_new_progress OUT NUMBER
    );

    PROCEDURE PRC_REGISTER_DELIVERABLE(
        p_project_id       IN  NUMBER,
        p_title            IN  VARCHAR2,
        p_deliverable_type IN  VARCHAR2,
        p_file_path        IN  VARCHAR2,
        p_file_size        IN  NUMBER,
        p_sha256_hash      IN  VARCHAR2,
        p_version          IN  VARCHAR2,
        p_notes            IN  VARCHAR2 DEFAULT NULL,
        p_deliverable_id   OUT NUMBER
    );

    PROCEDURE PRC_LOG_CHANGE_DATA_CAPTURE(
        p_target_db  IN VARCHAR2,
        p_table_name IN VARCHAR2,
        p_operation  IN VARCHAR2,
        p_record_id  IN NUMBER,
        p_details    IN VARCHAR2
    );

    -- Functions
    FUNCTION FNC_GET_SUBMISSION_READINESS(
        p_project_id IN NUMBER
    ) RETURN VARCHAR2;

    FUNCTION FNC_GET_ACTIVE_TASK_COUNT(
        p_project_id IN NUMBER,
        p_status_filter IN VARCHAR2 DEFAULT 'PENDING'
    ) RETURN NUMBER;

    -- Cursor Query Routine
    PROCEDURE PRC_GET_PROJECT_ANALYTICS(
        p_cursor OUT SYS_REFCURSOR
    );
END PKG_DEVVAULT_ADMIN;
/


-- -------------------------------------------------------------------------------------------------
-- SECTION 3: PL/SQL PACKAGE BODY (PKG_DEVVAULT_ADMIN)
-- -------------------------------------------------------------------------------------------------

CREATE OR REPLACE PACKAGE BODY PKG_DEVVAULT_ADMIN AS

    -- 1. Recalculate Progress Procedure
    PROCEDURE PRC_RECALCULATE_PROGRESS(
        p_project_id   IN  NUMBER,
        p_new_progress OUT NUMBER
    ) IS
        v_total_tasks     NUMBER := 0;
        v_completed_tasks NUMBER := 0;
    BEGIN
        SELECT COUNT(*),
               NVL(SUM(CASE WHEN IS_COMPLETED = 1 THEN 1 ELSE 0 END), 0)
        INTO v_total_tasks, v_completed_tasks
        FROM PROJECT_TASKS
        WHERE PROJECT_ID = p_project_id;

        IF v_total_tasks > 0 THEN
            p_new_progress := ROUND((v_completed_tasks / v_total_tasks) * 100);
        ELSE
            p_new_progress := 0;
        END IF;

        UPDATE PROJECTS
        SET PROGRESS_PERCENTAGE = p_new_progress,
            UPDATED_AT = SYSTIMESTAMP
        WHERE ID = p_project_id;

        COMMIT;
    EXCEPTION
        WHEN OTHERS THEN
            p_new_progress := 0;
            RAISE_APPLICATION_ERROR(-20001, 'Error recalculating progress: ' || SQLERRM);
    END PRC_RECALCULATE_PROGRESS;

    -- 2. Register Deliverable with Audit History
    PROCEDURE PRC_REGISTER_DELIVERABLE(
        p_project_id       IN  NUMBER,
        p_title            IN  VARCHAR2,
        p_deliverable_type IN  VARCHAR2,
        p_file_path        IN  VARCHAR2,
        p_file_size        IN  NUMBER,
        p_sha256_hash      IN  VARCHAR2,
        p_version          IN  VARCHAR2,
        p_notes            IN  VARCHAR2 DEFAULT NULL,
        p_deliverable_id   OUT NUMBER
    ) IS
        v_new_id NUMBER;
    BEGIN
        INSERT INTO PROJECT_DELIVERABLES (
            PROJECT_ID, TITLE, DELIVERABLE_TYPE, FILE_PATH,
            FILE_SIZE, FILE_HASH_SHA256, VERSION, NOTES, UPLOADED_AT
        ) VALUES (
            p_project_id, p_title, p_deliverable_type, p_file_path,
            p_file_size, p_sha256_hash, p_version, p_notes, SYSTIMESTAMP
        ) RETURNING ID INTO v_new_id;

        p_deliverable_id := v_new_id;

        -- Record into audit history
        INSERT INTO PROJECT_HISTORY (
            PROJECT_ID, ACTION_TYPE, DESCRIPTION, SEVERITY, TIMESTAMP
        ) VALUES (
            p_project_id, 'File Uploaded',
            'Registered deliverable ' || p_title || ' (' || p_deliverable_type || ', ' || p_version || ')',
            'INFO', SYSTIMESTAMP
        );

        -- Autonomous CDC logging
        PRC_LOG_CHANGE_DATA_CAPTURE(
            'vault', 'PROJECT_DELIVERABLES', 'INSERT', v_new_id,
            'Registered deliverable with SHA-256: ' || p_sha256_hash
        );

        COMMIT;
    END PRC_REGISTER_DELIVERABLE;

    -- 3. Autonomous Transaction CDC Logging
    PROCEDURE PRC_LOG_CHANGE_DATA_CAPTURE(
        p_target_db  IN VARCHAR2,
        p_table_name IN VARCHAR2,
        p_operation  IN VARCHAR2,
        p_record_id  IN NUMBER,
        p_details    IN VARCHAR2
    ) IS
        PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
        INSERT INTO DATABASE_CHANGE_LOG (
            TARGET_DATABASE, TABLE_NAME, OPERATION, RECORD_ID, DETAILS, TIMESTAMP
        ) VALUES (
            p_target_db, p_table_name, p_operation, p_record_id, p_details, SYSTIMESTAMP
        );
        COMMIT;
    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
    END PRC_LOG_CHANGE_DATA_CAPTURE;

    -- 4. Check Submission Readiness Function
    FUNCTION FNC_GET_SUBMISSION_READINESS(
        p_project_id IN NUMBER
    ) RETURN VARCHAR2 IS
        v_synopsis_cnt NUMBER := 0;
        v_report_cnt   NUMBER := 0;
        v_ppt_cnt      NUMBER := 0;
        v_source_cnt   NUMBER := 0;
        v_readiness    NUMBER := 0;
    BEGIN
        SELECT 
            NVL(SUM(CASE WHEN DELIVERABLE_TYPE = 'Synopsis/Proposal' THEN 1 ELSE 0 END), 0),
            NVL(SUM(CASE WHEN DELIVERABLE_TYPE = 'Project Report' THEN 1 ELSE 0 END), 0),
            NVL(SUM(CASE WHEN DELIVERABLE_TYPE = 'Presentation PPT' THEN 1 ELSE 0 END), 0),
            NVL(SUM(CASE WHEN DELIVERABLE_TYPE = 'Source Code ZIP' THEN 1 ELSE 0 END), 0)
        INTO v_synopsis_cnt, v_report_cnt, v_ppt_cnt, v_source_cnt
        FROM PROJECT_DELIVERABLES
        WHERE PROJECT_ID = p_project_id;

        IF v_synopsis_cnt > 0 THEN v_readiness := v_readiness + 25; END IF;
        IF v_report_cnt > 0 THEN v_readiness := v_readiness + 25; END IF;
        IF v_ppt_cnt > 0 THEN v_readiness := v_readiness + 25; END IF;
        IF v_source_cnt > 0 THEN v_readiness := v_readiness + 25; END IF;

        IF v_readiness = 100 THEN
            RETURN 'READY (100% Complete)';
        ELSE
            RETURN 'INCOMPLETE (' || TO_CHAR(v_readiness) || '% Ready)';
        END IF;
    END FNC_GET_SUBMISSION_READINESS;

    -- 5. Active Task Counter
    FUNCTION FNC_GET_ACTIVE_TASK_COUNT(
        p_project_id IN NUMBER,
        p_status_filter IN VARCHAR2 DEFAULT 'PENDING'
    ) RETURN NUMBER IS
        v_count NUMBER := 0;
    BEGIN
        IF UPPER(p_status_filter) = 'COMPLETED' THEN
            SELECT COUNT(*) INTO v_count FROM PROJECT_TASKS WHERE PROJECT_ID = p_project_id AND IS_COMPLETED = 1;
        ELSE
            SELECT COUNT(*) INTO v_count FROM PROJECT_TASKS WHERE PROJECT_ID = p_project_id AND IS_COMPLETED = 0;
        END IF;
        RETURN v_count;
    END FNC_GET_ACTIVE_TASK_COUNT;

    -- 6. Project Analytics SYS_REFCURSOR
    PROCEDURE PRC_GET_PROJECT_ANALYTICS(
        p_cursor OUT SYS_REFCURSOR
    ) IS
    BEGIN
        OPEN p_cursor FOR
            SELECT 
                p.ID,
                p.TITLE,
                p.STATUS,
                p.PROGRESS_PERCENTAGE,
                COUNT(t.ID) AS TOTAL_TASKS,
                NVL(SUM(CASE WHEN t.IS_COMPLETED = 1 THEN 1 ELSE 0 END), 0) AS COMPLETED_TASKS,
                COUNT(d.ID) AS ATTACHED_DELIVERABLES
            FROM PROJECTS p
            LEFT JOIN PROJECT_TASKS t ON p.ID = t.PROJECT_ID
            LEFT JOIN PROJECT_DELIVERABLES d ON p.ID = d.PROJECT_ID
            GROUP BY p.ID, p.TITLE, p.STATUS, p.PROGRESS_PERCENTAGE
            ORDER BY p.ID;
    END PRC_GET_PROJECT_ANALYTICS;

END PKG_DEVVAULT_ADMIN;
/


-- -------------------------------------------------------------------------------------------------
-- SECTION 4: ORACLE COMPOUND TRIGGER (MUTATING TABLE RESOLUTION)
-- -------------------------------------------------------------------------------------------------
-- In traditional Oracle triggers, executing a SELECT against PROJECT_TASKS while PROJECT_TASKS
-- is being updated causes the notorious "ORA-04091: table is mutating" runtime exception.
-- The Compound Trigger below demonstrates the modern ADBMS design pattern to solve this.

CREATE OR REPLACE TRIGGER TRG_TASKS_COMPOUND_PROGRESS
FOR INSERT OR UPDATE OF IS_COMPLETED OR DELETE ON PROJECT_TASKS
COMPOUND TRIGGER

    TYPE T_PROJ_SET IS TABLE OF BOOLEAN INDEX BY PLS_INTEGER;
    g_affected_projects T_PROJ_SET;

    -- Before each statement, reset cache
    BEFORE STATEMENT IS
    BEGIN
        g_affected_projects.DELETE;
    END BEFORE STATEMENT;

    -- After each row, accumulate affected project IDs
    AFTER EACH ROW IS
    BEGIN
        IF INSERTING OR UPDATING THEN
            g_affected_projects(:NEW.PROJECT_ID) := TRUE;
        ELSIF DELETING THEN
            g_affected_projects(:OLD.PROJECT_ID) := TRUE;
        END IF;
    END AFTER EACH ROW;

    -- After statement completes (table is no longer mutating), recalculate progress
    AFTER STATEMENT IS
        v_proj_id     PLS_INTEGER;
        v_new_prog    NUMBER;
    BEGIN
        v_proj_id := g_affected_projects.FIRST;
        WHILE v_proj_id IS NOT NULL LOOP
            PKG_DEVVAULT_ADMIN.PRC_RECALCULATE_PROGRESS(v_proj_id, v_new_prog);
            v_proj_id := g_affected_projects.NEXT(v_proj_id);
        END LOOP;
    END AFTER STATEMENT;

END TRG_TASKS_COMPOUND_PROGRESS;
/

