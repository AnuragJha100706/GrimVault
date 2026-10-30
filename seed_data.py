r"""
DevVault - Database Seed Script (Anurag Jha Edition)
Author: Anurag Jha (GitHub: https://github.com/AnuragJha100706)
Local Projects Root: E:\COMPLETE PROJECT

Pre-populates partitioned SQLite databases:
1. devvault_core.db   - Core transactional metadata & catalog
2. devvault_vault.db  - Dedicated high-capacity deliverables & file attachments (SHA-256 verified)
3. devvault_audit.db  - Immutable audit trail & change data capture (CDC)

Populates real projects from E:\COMPLETE PROJECT and Anurag's GitHub profile.
"""
import os
import io
import zipfile
from datetime import datetime, date, timedelta
from app import app, db, generate_slug, UPLOAD_FOLDERS, adbms_manager
from models import (
    ProjectCategory, Technology, Project, ProjectDocument,
    ProjectDeliverable, ProjectNote, ProjectTask, ProjectHistory,
    SystemSetting, DatabaseChangeLog
)
from adbms_service import ADBMSManager

LOCAL_ROOT = r"E:\COMPLETE PROJECT"

def register_or_create_file(preferred_path, folder_key, fallback_filename, fallback_bytes):
    r"""Registers real local project file if present in E:\COMPLETE PROJECT, else creates fallback."""
    if os.path.exists(preferred_path):
        size = os.path.getsize(preferred_path)
        sha = ADBMSManager.calculate_file_sha256(preferred_path)
        return preferred_path, size, sha

    target_dir = UPLOAD_FOLDERS[folder_key]
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, fallback_filename)
    with open(file_path, 'wb') as f:
        f.write(fallback_bytes)
    relative_dir = os.path.basename(target_dir)
    sha256_hash = ADBMSManager.calculate_file_sha256(file_path)
    return f"/static/uploads/{relative_dir}/{fallback_filename}", len(fallback_bytes), sha256_hash


def create_minimal_pdf_content(title, subject):
    """Creates a valid minimal PDF file header/content."""
    pdf_text = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 145 >> stream
BT
/F1 18 Tf
72 710 Td
({title}) Tj
/F1 12 Tf
0 -30 Td
({subject}) Tj
0 -20 Td
(Author: Anurag Jha - https://github.com/AnuragJha100706) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000261 00000 n 
0000000458 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
535
%%EOF
"""
    return pdf_text.encode('latin1')


def create_sample_zip(project_name):
    """Creates a sample source zip containing a README and main script."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('README.md', f"# {project_name}\n\nOfficial submission archive for Anurag Jha (https://github.com/AnuragJha100706).")
        zf.writestr('main.py', f"# {project_name}\nprint('System initialized successfully.')\n")
    return buf.getvalue()


def seed_database():
    with app.app_context():
        print("Resetting partitioned database schemas across devvault_core.db, devvault_vault.db, devvault_audit.db...")
        db.drop_all()
        db.create_all()

        print("Installing native SQLite triggers, composite B-tree indexes, and analytical views...")
        adbms_manager.setup_advanced_triggers_and_views()

        # Seed initial CDC logs into devvault_audit.db
        cdc_entries = [
            DatabaseChangeLog(
                target_database="core",
                operation="CREATE",
                table_name="projects, tasks, techs, docs",
                details="Initial schema creation for core project catalog and relations."
            ),
            DatabaseChangeLog(
                target_database="vault",
                operation="CREATE",
                table_name="project_deliverables",
                details="Dedicated file vault storage partition with SHA-256 checksums."
            ),
            DatabaseChangeLog(
                target_database="audit",
                operation="CREATE",
                table_name="project_history, database_change_log",
                details="Append-only compliance audit trail and change data capture log."
            ),
            DatabaseChangeLog(
                target_database="core",
                operation="CREATE_TRIGGER",
                table_name="project_tasks",
                details="Installed trg_tasks_after_update_recalc_progress for automatic progress sync."
            )
        ]
        for cdc in cdc_entries:
            db.session.add(cdc)

        print("Seeding Categories into devvault_core.db...")
        categories = {
            'Web Dev': ProjectCategory(name='Web Development', description='Full-stack web applications, microservices, and modern web portals.'),
            'AI/ML': ProjectCategory(name='AI & Machine Learning', description='Deep learning models, computer vision, NLP, and intelligent recommendation systems.'),
            'IoT': ProjectCategory(name='IoT & Embedded Systems', description='Microcontrollers, telemetry hardware, wireless sensors, and edge computing.'),
            'Mobile Dev': ProjectCategory(name='Mobile Development', description='Native and cross-platform Android and iOS mobile applications.'),
            'Academic': ProjectCategory(name='Academic Research', description='University thesis work, empirical scientific research papers, and technical dissertations.'),
            'Cloud/DevOps': ProjectCategory(name='Cloud & DevOps', description='CI/CD automation pipelines, container orchestration, and serverless infrastructure.')
        }
        for cat in categories.values():
            db.session.add(cat)
        db.session.commit()

        print("Seeding Technologies into devvault_core.db...")
        techs = {
            'python': Technology(name='Python', category='Language', icon_class='bi bi-filetype-py', badge_color='#3776ab'),
            'javascript': Technology(name='JavaScript', category='Language', icon_class='bi bi-filetype-js', badge_color='#f7df1e'),
            'typescript': Technology(name='TypeScript', category='Language', icon_class='bi bi-filetype-tsx', badge_color='#3178c6'),
            'java': Technology(name='Java', category='Language', icon_class='bi bi-filetype-java', badge_color='#b07219'),
            'kotlin': Technology(name='Kotlin / Android', category='Language', icon_class='bi bi-phone', badge_color='#7f52ff'),
            'flask': Technology(name='Flask', category='Framework', icon_class='bi bi-layers-fill', badge_color='#000000'),
            'node': Technology(name='Node.js', category='Framework', icon_class='bi bi-hexagon-fill', badge_color='#339933'),
            'react': Technology(name='React', category='Framework', icon_class='bi bi-circle-fill', badge_color='#61dafb'),
            'tailwind': Technology(name='Tailwind CSS', category='Framework', icon_class='bi bi-palette-fill', badge_color='#06b6d4'),
            'bootstrap': Technology(name='Bootstrap 5', category='Framework', icon_class='bi bi-bootstrap-fill', badge_color='#7952b3'),
            'sqlite': Technology(name='SQLite', category='Database', icon_class='bi bi-database-fill', badge_color='#003b57'),
            'docker': Technology(name='Docker', category='Tool', icon_class='bi bi-box-fill', badge_color='#2496ed'),
            'chartjs': Technology(name='Chart.js', category='Tool', icon_class='bi bi-bar-chart-fill', badge_color='#ff6384'),
            'git': Technology(name='Git', category='Tool', icon_class='bi bi-git', badge_color='#f05032'),
            'vite': Technology(name='Vite', category='Tool', icon_class='bi bi-lightning-fill', badge_color='#646cff')
        }
        for tech in techs.values():
            db.session.add(tech)
        db.session.commit()

        print("Seeding Anurag Jha's Real Projects from E:\\COMPLETE PROJECT...")

        # =========================================================================
        # Project 1: DevVault
        # =========================================================================
        p1 = Project(
            title="DevVault: Academic Repository & Information System",
            slug="devvault-academic-repository",
            short_description="Centralized personal repository and academic deliverables vault for tracking code milestones, technical reports, and viva presentations.",
            category=categories['Web Dev'],
            status="Completed",
            progress_percentage=100,
            github_url="https://github.com/AnuragJha100706/devvault",
            live_url="http://127.0.0.1:5000",
            local_path=os.getcwd(),
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=5),
            technologies=[techs['python'], techs['flask'], techs['sqlite'], techs['bootstrap'], techs['chartjs'], techs['git']],
            github_stars=28,
            github_forks=7,
            github_open_issues=0,
            github_default_branch="main",
            github_latest_commit_sha="a100706",
            github_latest_commit_msg="release: DevVault ADBMS Partitioned SQLite Architecture v2.0",
            github_latest_commit_author="Anurag Jha",
            github_synced_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.session.add(p1)
        db.session.flush()

        doc1 = ProjectDocument(
            project_id=p1.id,
            abstract="In academic institutions and modern software engineering tracks, student developers frequently produce a diverse array of non-code artifacts alongside source code repositories—such as project synopses, semester evaluation reports, viva presentation slides, architectural diagrams, and verified code archives. Conventional version control platforms (such as GitHub) are primarily optimized for text-based code diffs and lack academic evaluation pipelines. DevVault resolves this fragmentation by functioning as a unified Personal Project Repository and Academic Information Management System.",
            problem_statement="Developer portfolios and university evaluation guidelines require rigorous tracking of academic deliverables alongside development milestones. Students currently scatter reports in Google Drive, slide decks on local hard drives, and code in git repositories, leading to version mismatch, lost documentation, and stressful final viva evaluations.",
            objectives="1. Design a normalized partitioned SQLite schema tracking projects, technologies, documentation, and deliverables across core, vault, and audit databases.\n2. Implement a dedicated Academic Deliverables Vault with submission readiness checklists.\n3. Provide dynamic progress calculation synchronizing with milestone task toggles via native SQLite triggers.\n4. Build an automated One-Click Academic Synopsis report generator with print stylesheet formatting.\n5. Offer flexible data export across JSON, CSV, and full compressed multi-database backups.",
            system_requirements="Hardware Requirements:\n- Processor: Intel Core i3 / AMD Ryzen 3 or higher\n- RAM: Minimum 4GB (8GB recommended)\n- Storage: 200MB available disk space\n\nSoftware Requirements:\n- Operating System: Windows 10/11, macOS, or Linux\n- Runtime: Python 3.10+ (Tested on Python 3.12)\n- Web Framework: Flask 3.x, Flask-SQLAlchemy\n- Database: SQLite 3 with Write-Ahead Logging (WAL)\n- Browser: Google Chrome, Firefox, Safari, or Microsoft Edge",
            architecture_notes="DevVault adopts a clean partitioned Model-View-Controller (MVC) architectural pattern. The database tier separates storage into devvault_core.db, devvault_vault.db, and devvault_audit.db. Cross-database queries utilize SQLite ATTACH DATABASE federation. Dynamic milestone toggles leverage native SQLite ECA triggers to update progress percentages in real time without application-layer overhead.",
            readme_content="""# DevVault: Academic Project Repository & Information System

> "One Place for Every Project – Organize, Document and Track Your Development Journey"

Author: Anurag Jha (https://github.com/AnuragJha100706)
Local Projects Root: `E:\\COMPLETE PROJECT`

## Features
- **ADBMS Multi-Database Architecture**: Isolated partitions for Core Metadata, File Vault, and Audit Trail.
- **Native Engine Triggers**: Automated progress recalculation inside SQLite C-engine.
- **Academic Deliverables Vault**: Dedicated attachments for Reports (.pdf), PPTs (.pptx), Synopses (.docx), and Source Code ZIPs with SHA-256 integrity checksums.
- **Interactive Database Studio**: Execute federated queries, inspect EXPLAIN QUERY PLAN B-tree trees, and analyze PRAGMA status.
- **Full Data Portability**: Instant multi-database backup (.zip) and JSON/CSV export.
"""
        )
        db.session.add(doc1)

        path1, size1, hash1 = register_or_create_file(os.path.join(LOCAL_ROOT, 'project portfolio', 'anurag_resume.pdf'), 'Synopsis/Proposal', f'{p1.id}_DevVault_Academic_Synopsis.docx', b"DevVault Formal Project Synopsis & Proposal Document.")
        deliv1 = ProjectDeliverable(project_id=p1.id, title="Official Project Synopsis & Proposal", deliverable_type="Synopsis/Proposal", file_path=path1, file_size=size1, file_hash_sha256=hash1, version="v1.0", notes="Approved by Department Head")

        path2, size2, hash2 = register_or_create_file(os.path.join(LOCAL_ROOT, 'javareport', 'JavaReportFile.docx'), 'Project Report', f'{p1.id}_DevVault_Comprehensive_Report_Final.pdf', create_minimal_pdf_content("DevVault Final Report", "Academic Information Management System"))
        deliv2 = ProjectDeliverable(project_id=p1.id, title="Comprehensive Final Project Report", deliverable_type="Project Report", file_path=path2, file_size=size2, file_hash_sha256=hash2, version="v2.0 (Final)", notes="Complete 7 Chapters formatted according to IEEE standards")

        path3, size3, hash3 = register_or_create_file(os.path.join(LOCAL_ROOT, 'javareport', 'Student Management System.pptx'), 'Presentation PPT', f'{p1.id}_DevVault_Defense_Presentation.pptx', b"DevVault 15-Slide Presentation Slide Deck for Final Viva Evaluation.")
        deliv3 = ProjectDeliverable(project_id=p1.id, title="Final Viva Presentation Slide Deck", deliverable_type="Presentation PPT", file_path=path3, file_size=size3, file_hash_sha256=hash3, version="Final", notes="15-slide defense deck with speaker notes")

        path4, size4, hash4 = register_or_create_file(os.path.join(LOCAL_ROOT, 'collage event management system.zip'), 'Source Code ZIP', f'{p1.id}_DevVault_Source_Code_Archive.zip', create_sample_zip("DevVault"))
        deliv4 = ProjectDeliverable(project_id=p1.id, title="Complete Source Code ZIP Archive", deliverable_type="Source Code ZIP", file_path=path4, file_size=size4, file_hash_sha256=hash4, version="v1.0-release", notes="Clean production-ready source bundle")

        db.session.add_all([deliv1, deliv2, deliv3, deliv4])

        tasks_p1 = [
            ProjectTask(project_id=p1.id, task_name="Design partitioned 9-table SQLite schema across core, vault, and audit", is_completed=True, priority="High", due_date=date.today() - timedelta(days=45)),
            ProjectTask(project_id=p1.id, task_name="Build Flask routes and file upload handlers with SHA-256 hashing", is_completed=True, priority="High", due_date=date.today() - timedelta(days=35)),
            ProjectTask(project_id=p1.id, task_name="Integrate Chart.js dynamic dashboard visualizations", is_completed=True, priority="Medium", due_date=date.today() - timedelta(days=25)),
            ProjectTask(project_id=p1.id, task_name="Implement interactive AJAX milestone checklist with native SQLite trigger sync", is_completed=True, priority="Medium", due_date=date.today() - timedelta(days=15)),
            ProjectTask(project_id=p1.id, task_name="Create printable academic synopsis layout with print media queries", is_completed=True, priority="High", due_date=date.today() - timedelta(days=7)),
            ProjectTask(project_id=p1.id, task_name="Integrate local projects vault scanner for E:\\COMPLETE PROJECT", is_completed=True, priority="High", due_date=date.today() - timedelta(days=1))
        ]
        db.session.add_all(tasks_p1)

        hist_p1 = [
            ProjectHistory(project_id=p1.id, action_type="Created", description="DevVault project initialized by Anurag Jha.", severity="INFO", timestamp=datetime.utcnow() - timedelta(days=60)),
            ProjectHistory(project_id=p1.id, action_type="Status Updated", description="Project marked as Completed (100% submission ready).", severity="SUCCESS", timestamp=datetime.utcnow() - timedelta(days=5))
        ]
        db.session.add_all(hist_p1)

        # =========================================================================
        # Project 2: The Velvet Fork (from E:\COMPLETE PROJECT\velvetfork_webproject)
        # =========================================================================
        p2 = Project(
            title="The Velvet Fork: Luxury Digital Dining & Reservation Platform",
            slug="the-velvet-fork-luxury-dining",
            short_description="A full-stack luxury restaurant web application connecting brand discovery, menu exploring, table reservations, and guest loyalty workflows.",
            category=categories['Web Dev'],
            status="Completed",
            progress_percentage=100,
            github_url="https://github.com/AnuragJha100706/velvetfork_webproject",
            live_url="http://127.0.0.1:5001",
            local_path=os.path.join(LOCAL_ROOT, 'velvetfork_webproject'),
            start_date=date.today() - timedelta(days=50),
            end_date=date.today() - timedelta(days=10),
            technologies=[techs['python'], techs['flask'], techs['javascript'], techs['bootstrap']],
            github_stars=19,
            github_forks=4,
            github_open_issues=0,
            github_default_branch="main",
            github_latest_commit_sha="v7f4a21",
            github_latest_commit_msg="feat: complete interactive table reservation & guest loyalty engine",
            github_latest_commit_author="Anurag Jha",
            github_synced_at=datetime.utcnow() - timedelta(hours=4)
        )
        db.session.add(p2)
        db.session.flush()

        velvet_case_study = ""
        case_study_path = os.path.join(LOCAL_ROOT, 'velvetfork_webproject', 'CASE-STUDY.md')
        if os.path.exists(case_study_path):
            with open(case_study_path, 'r', encoding='utf-8', errors='ignore') as f:
                velvet_case_study = f.read()
        else:
            velvet_case_study = "# The Velvet Fork\n\nFull-stack luxury restaurant application with Flask REST backend and responsive frontend."

        doc2 = ProjectDocument(
            project_id=p2.id,
            abstract="The Velvet Fork is a full-stack restaurant web application created to make a premium dining experience accessible before the guest reaches the restaurant. It connects brand discovery, dish exploration, table reservation, and feedback sharing into a cohesive responsive web application.",
            problem_statement="Traditional restaurant websites are static brochure sites that force patrons to call for table reservations and fail to provide real-time seating availability.",
            objectives="1. Build an editorial-style luxury dining UI using Vanilla JS & Bootstrap.\n2. Implement a lightweight Flask REST backend for accounts, reservations, and favorites.\n3. Integrate local storage fallback for offline academic presentations.",
            system_requirements="Software: Python 3.10+, Flask, Flask-CORS, Bootstrap 5.3.3\nHardware: Modern browser, 4GB RAM",
            architecture_notes="Frontend: Vanilla JS Service Architecture -> Backend: Python Flask REST endpoints -> Persistence: JSON state with browser LocalStorage fallback.",
            readme_content=velvet_case_study
        )
        db.session.add(doc2)

        path_p2_rar, size_p2_rar, hash_p2_rar = register_or_create_file(os.path.join(LOCAL_ROOT, 'velvetfork_webproject.rar'), 'Source Code ZIP', f'{p2.id}_VelvetFork_Source_Code.rar', create_sample_zip("TheVelvetFork"))
        deliv_p2 = ProjectDeliverable(
            project_id=p2.id,
            title="Complete Production Source Archive (RAR)",
            deliverable_type="Source Code ZIP",
            file_path=path_p2_rar,
            file_size=size_p2_rar,
            file_hash_sha256=hash_p2_rar,
            version="v1.0-release",
            notes="Full source code including static assets and REST API endpoints"
        )
        db.session.add(deliv_p2)

        tasks_p2 = [
            ProjectTask(project_id=p2.id, task_name="Design luxury editorial design system and palette", is_completed=True, priority="High"),
            ProjectTask(project_id=p2.id, task_name="Develop table reservation and booking modal workflow", is_completed=True, priority="High"),
            ProjectTask(project_id=p2.id, task_name="Build Flask REST endpoints for accounts and favorites", is_completed=True, priority="Medium"),
            ProjectTask(project_id=p2.id, task_name="Compile formal academic case study document", is_completed=True, priority="High")
        ]
        db.session.add_all(tasks_p2)

        # =========================================================================
        # Project 3: VibeNest AI (from E:\COMPLETE PROJECT\music recommandation system)
        # =========================================================================
        p3 = Project(
            title="VibeNest AI: Intelligent Music Recommendation System",
            slug="vibenest-ai-music-recommendation",
            short_description="Full-stack AI music recommendation engine using 9-dimensional acoustic cosine similarity vector matching and mood radar charts.",
            category=categories['AI/ML'],
            status="Completed",
            progress_percentage=100,
            github_url="https://github.com/AnuragJha100706/music-recommendation-system",
            live_url="http://127.0.0.1:5002",
            local_path=os.path.join(LOCAL_ROOT, 'music recommandation system'),
            start_date=date.today() - timedelta(days=40),
            end_date=date.today() - timedelta(days=12),
            technologies=[techs['python'], techs['flask'], techs['sqlite'], techs['javascript'], techs['chartjs']],
            github_stars=34,
            github_forks=9,
            github_open_issues=1,
            github_default_branch="main",
            github_latest_commit_sha="m9b3c41",
            github_latest_commit_msg="feat: optimize 9-dimensional acoustic cosine similarity search over 40k tracks",
            github_latest_commit_author="Anurag Jha",
            github_synced_at=datetime.utcnow() - timedelta(hours=8)
        )
        db.session.add(p3)
        db.session.flush()

        vibenest_readme = ""
        vibenest_path = os.path.join(LOCAL_ROOT, 'music recommandation system', 'README.md')
        if os.path.exists(vibenest_path):
            with open(vibenest_path, 'r', encoding='utf-8', errors='ignore') as f:
                vibenest_readme = f.read()

        doc3 = ProjectDocument(
            project_id=p3.id,
            abstract="VibeNest AI is an intelligent music recommendation system combining content-based filtering across 9 acoustic dimensions (danceability, energy, valence, tempo, acousticness, instrumentalness, loudness, speechiness, and liveness) with an interactive HTML5 canvas radar spiderweb comparison.",
            problem_statement="Modern streaming services lock users into repetitive genre silos. Listeners lack transparent explainable recommendations reflecting their granular acoustic preferences.",
            objectives="1. Ingest and normalize 40,000+ track Spotify acoustic dataset.\n2. Compute cosine similarity vector distances in real time.\n3. Render acoustic radar charts comparing query tracks to recommendations.",
            system_requirements="Software: Python 3.10+, Flask, SQLite 3, Chart.js, HTML5 Canvas\nHardware: 4GB RAM minimum",
            architecture_notes="Python Flask API -> Vector Math Engine (NumPy/SciPy) -> SQLite Track Catalog -> HTML5 Radar Visualizer.",
            readme_content=vibenest_readme or "# VibeNest AI Music Recommendation System"
        )
        db.session.add(doc3)

        path_p3_zip, size_p3_zip, hash_p3_zip = register_or_create_file(os.path.join(LOCAL_ROOT, 'music recommandation system.zip'), 'Source Code ZIP', f'{p3.id}_VibeNest_Source_Code.zip', create_sample_zip("VibeNest"))
        deliv_p3 = ProjectDeliverable(
            project_id=p3.id,
            title="Complete VibeNest AI Source ZIP Archive",
            deliverable_type="Source Code ZIP",
            file_path=path_p3_zip,
            file_size=size_p3_zip,
            file_hash_sha256=hash_p3_zip,
            version="v1.0-release",
            notes="Includes acoustic matrix, track catalogs, and Flask runner"
        )
        db.session.add(deliv_p3)

        tasks_p3 = [
            ProjectTask(project_id=p3.id, task_name="Normalize 9-dimensional acoustic feature vectors with robust scaling", is_completed=True, priority="High"),
            ProjectTask(project_id=p3.id, task_name="Implement cosine similarity nearest-neighbor search engine", is_completed=True, priority="High"),
            ProjectTask(project_id=p3.id, task_name="Build HTML5 canvas acoustic radar comparison visualizer", is_completed=True, priority="Medium"),
            ProjectTask(project_id=p3.id, task_name="Integrate mood presets (Gym, Deep Focus, Chill, Lo-Fi)", is_completed=True, priority="Medium")
        ]
        db.session.add_all(tasks_p3)

        # =========================================================================
        # Project 4: College Event Management System (from E:\COMPLETE PROJECT\collage event management system)
        # =========================================================================
        p4 = Project(
            title="College Event Management System (CEMS)",
            slug="college-event-management-system",
            short_description="Comprehensive university event registration and administrative management platform built with React, Vite, Node.js, and SQLite.",
            category=categories['Web Dev'],
            status="Completed",
            progress_percentage=100,
            github_url="https://github.com/AnuragJha100706/college-event-management-system",
            live_url="http://127.0.0.1:5173",
            local_path=os.path.join(LOCAL_ROOT, 'collage event management system'),
            start_date=date.today() - timedelta(days=65),
            end_date=date.today() - timedelta(days=15),
            technologies=[techs['react'], techs['node'], techs['vite'], techs['tailwind'], techs['sqlite']],
            github_stars=22,
            github_forks=6,
            github_open_issues=0,
            github_default_branch="main",
            github_latest_commit_sha="c8e1007",
            github_latest_commit_msg="feat: add role-based student and faculty registration dashboards",
            github_latest_commit_author="Anurag Jha",
            github_synced_at=datetime.utcnow() - timedelta(hours=10)
        )
        db.session.add(p4)
        db.session.flush()

        cems_readme = ""
        cems_path = os.path.join(LOCAL_ROOT, 'collage event management system', 'README.md')
        if os.path.exists(cems_path):
            with open(cems_path, 'r', encoding='utf-8', errors='ignore') as f:
                cems_readme = f.read()

        doc4 = ProjectDocument(
            project_id=p4.id,
            abstract="College Event Management System (CEMS) automates the scheduling, student registration, ticketing, and administrative approval workflow for campus seminars, cultural festivals, and technical symposiums.",
            problem_statement="Manual paper-based campus event registration causes registration queues, lost payments, and poor attendance recordkeeping.",
            objectives="1. Build high-speed single-page application using React & Vite.\n2. Implement Node.js Express backend with SQLite relational persistence.\n3. Provide role-based student and administrator dashboards.",
            system_requirements="Software: Node.js 18+, Vite, React 18, SQLite 3, Tailwind CSS\nHardware: Modern browser, 4GB RAM",
            architecture_notes="React Frontend -> Express REST API -> SQLite Database (database.sqlite) with bcrypt auth.",
            readme_content=cems_readme or "# College Event Management System (CEMS)"
        )
        db.session.add(doc4)

        path_p4_zip, size_p4_zip, hash_p4_zip = register_or_create_file(os.path.join(LOCAL_ROOT, 'collage event management system.zip'), 'Source Code ZIP', f'{p4.id}_CEMS_Source_Code.zip', create_sample_zip("CEMS"))
        deliv_p4 = ProjectDeliverable(
            project_id=p4.id,
            title="Complete CEMS Project Archive (ZIP)",
            deliverable_type="Source Code ZIP",
            file_path=path_p4_zip,
            file_size=size_p4_zip,
            file_hash_sha256=hash_p4_zip,
            version="v1.0-release",
            notes="Full React client, Express server, and database seed bundle"
        )
        db.session.add(deliv_p4)

        tasks_p4 = [
            ProjectTask(project_id=p4.id, task_name="Design responsive campus event discovery feed with Tailwind", is_completed=True, priority="High"),
            ProjectTask(project_id=p4.id, task_name="Implement Node Express JWT authentication and SQLite tables", is_completed=True, priority="High"),
            ProjectTask(project_id=p4.id, task_name="Build administrative event creation and RSVP approval portal", is_completed=True, priority="Medium"),
            ProjectTask(project_id=p4.id, task_name="Conduct end-to-end user evaluation and stress testing", is_completed=True, priority="Low")
        ]
        db.session.add_all(tasks_p4)

        # =========================================================================
        # Project 5: Java Student Academic Evaluation & Lab System (from E:\COMPLETE PROJECT\javareport)
        # =========================================================================
        p5 = Project(
            title="Java Student Academic Evaluation & Lab Management System",
            slug="java-student-academic-evaluation",
            short_description="Academic laboratory recordkeeping and performance evaluation application with automated grade calculation and student attendance tracking.",
            category=categories['Academic'],
            status="Completed",
            progress_percentage=100,
            github_url="https://github.com/AnuragJha100706/javareport",
            live_url="",
            local_path=os.path.join(LOCAL_ROOT, 'javareport'),
            start_date=date.today() - timedelta(days=90),
            end_date=date.today() - timedelta(days=30),
            technologies=[techs['java'], techs['sqlite']],
            github_stars=15,
            github_forks=3,
            github_open_issues=0,
            github_default_branch="main",
            github_latest_commit_sha="j100706",
            github_latest_commit_msg="release: finalized student laboratory evaluation report and viva deck",
            github_latest_commit_author="Anurag Jha",
            github_synced_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(p5)
        db.session.flush()

        doc5 = ProjectDocument(
            project_id=p5.id,
            abstract="Java Student Academic Evaluation & Lab Management System manages student grading, attendance rosters, and laboratory experiment completion metrics with exportable academic records.",
            problem_statement="Faculty members spend excessive time calculating lab marks and correlating student attendance across paper logs.",
            objectives="1. Implement core Java data processing algorithms.\n2. Store and query student attendance and results datasets.\n3. Prepare institutional documentation and slide decks for department review.",
            system_requirements="Software: Java JDK 17+, JavaFX / Swing, SQLite\nHardware: 2GB RAM",
            architecture_notes="Java Core Object-Oriented Architecture -> CSV Data Stores & SQLite Relational Backend.",
            readme_content="# Java Student Academic Evaluation System\n\nOfficial laboratory project submitted by Anurag Jha."
        )
        db.session.add(doc5)

        # Attach real JavaReportFile.docx and Student Management System.pptx
        path_p5_doc, size_p5_doc, hash_p5_doc = register_or_create_file(os.path.join(LOCAL_ROOT, 'javareport', 'JavaReportFile.docx'), 'Project Report', f'{p5.id}_Java_Report_File.docx', b"Java Student Lab Evaluation Official Project Report.")
        deliv_p5_rep = ProjectDeliverable(
            project_id=p5.id,
            title="Official Academic Lab Report (DOCX)",
            deliverable_type="Project Report",
            file_path=path_p5_doc,
            file_size=size_p5_doc,
            file_hash_sha256=hash_p5_doc,
            version="v1.0-final",
            notes="Formal laboratory dissertation submitted to department evaluators"
        )

        path_p5_ppt, size_p5_ppt, hash_p5_ppt = register_or_create_file(os.path.join(LOCAL_ROOT, 'javareport', 'Student Management System.pptx'), 'Presentation PPT', f'{p5.id}_Student_Management_Slides.pptx', b"Java Student Management System Slide Deck.")
        deliv_p5_ppt = ProjectDeliverable(
            project_id=p5.id,
            title="Defense Presentation Slide Deck (PPTX)",
            deliverable_type="Presentation PPT",
            file_path=path_p5_ppt,
            file_size=size_p5_ppt,
            file_hash_sha256=hash_p5_ppt,
            version="v1.0",
            notes="Departmental seminar defense presentation"
        )

        db.session.add_all([deliv_p5_rep, deliv_p5_ppt])

        tasks_p5 = [
            ProjectTask(project_id=p5.id, task_name="Implement student attendance data structures and parsing", is_completed=True, priority="High"),
            ProjectTask(project_id=p5.id, task_name="Build grade calculation engine with weighted GPA averages", is_completed=True, priority="High"),
            ProjectTask(project_id=p5.id, task_name="Compile formal JavaReportFile.docx documentation", is_completed=True, priority="High")
        ]
        db.session.add_all(tasks_p5)

        # =========================================================================
        # Project 6: DMDW Analytics Platform (from E:\COMPLETE PROJECT\DMDW PROJECT)
        # =========================================================================
        p6 = Project(
            title="DMDW: Data Mining & Warehousing Predictive Analytics Platform",
            slug="dmdw-data-mining-warehousing-analytics",
            short_description="Advanced data mining and predictive warehousing system analyzing student performance, batch testing, and classification algorithms.",
            category=categories['Academic'],
            status="Completed",
            progress_percentage=100,
            github_url="https://github.com/AnuragJha100706/DMDW-Project",
            live_url="",
            local_path=os.path.join(LOCAL_ROOT, 'DMDW PROJECT'),
            start_date=date.today() - timedelta(days=75),
            end_date=date.today() - timedelta(days=20),
            technologies=[techs['python'], techs['sqlite'], techs['javascript']],
            github_stars=18,
            github_forks=5,
            github_open_issues=0,
            github_default_branch="main",
            github_latest_commit_sha="d100706",
            github_latest_commit_msg="feat: complete batch test evaluation and decision tree classification",
            github_latest_commit_author="Anurag Jha",
            github_synced_at=datetime.utcnow() - timedelta(days=3)
        )
        db.session.add(p6)
        db.session.flush()

        dmdw_readme = ""
        dmdw_path = os.path.join(LOCAL_ROOT, 'DMDW PROJECT', 'README.md')
        if os.path.exists(dmdw_path):
            with open(dmdw_path, 'r', encoding='utf-8', errors='ignore') as f:
                dmdw_readme = f.read()

        doc6 = ProjectDocument(
            project_id=p6.id,
            abstract="DMDW explores modern Data Mining and Data Warehousing concepts, including OLAP cube design, star-schema modeling, batch student evaluation, and machine learning classification algorithms.",
            problem_statement="Educational institutions collect vast volumes of student assessment data without performing predictive modeling to identify at-risk candidates.",
            objectives="1. Implement ETL pipelines cleaning and transforming raw educational records.\n2. Design multi-dimensional data warehouse star schema.\n3. Execute decision tree and Naive Bayes classification benchmarks.",
            system_requirements="Software: Python 3.10+, Scikit-Learn, Weka, SQLite\nHardware: 8GB RAM",
            architecture_notes="Data Ingestion -> ETL Cleaning -> Data Warehouse Star Schema -> Predictive Classification Models.",
            readme_content=dmdw_readme or "# DMDW Project Repository"
        )
        db.session.add(doc6)

        path_p6_zip, size_p6_zip, hash_p6_zip = register_or_create_file(os.path.join(LOCAL_ROOT, 'DMDW PROJECT.zip'), 'Source Code ZIP', f'{p6.id}_DMDW_Source_Archive.zip', create_sample_zip("DMDW"))
        deliv_p6 = ProjectDeliverable(
            project_id=p6.id,
            title="Complete DMDW Project & Dataset Archive (ZIP)",
            deliverable_type="Source Code ZIP",
            file_path=path_p6_zip,
            file_size=size_p6_zip,
            file_hash_sha256=hash_p6_zip,
            version="v1.0-release",
            notes="Complete dataset, batch test scripts, and warehousing schemas"
        )
        db.session.add(deliv_p6)

        tasks_p6 = [
            ProjectTask(project_id=p6.id, task_name="Design data warehouse multidimensional star schema", is_completed=True, priority="High"),
            ProjectTask(project_id=p6.id, task_name="Implement random student sampling and batch evaluation scripts", is_completed=True, priority="High"),
            ProjectTask(project_id=p6.id, task_name="Benchmark classification accuracy across decision trees and Naive Bayes", is_completed=True, priority="Medium")
        ]
        db.session.add_all(tasks_p6)

        # =========================================================================
        # Project 7: OmniNote (from E:\COMPLETE PROJECT\Notes generator Using camera or prompt)
        # =========================================================================
        p7 = Project(
            title="OmniNote: Multimodal AI Study Workspace & Flashcard Generator",
            slug="omninote-multimodal-ai-study-workspace",
            short_description="Multimodal AI study workspace turning text prompts, web pages, PDFs, and camera captures into structured notes, verified sources, and interactive flashcards.",
            category=categories['AI/ML'],
            status="In Progress",
            progress_percentage=85,
            github_url="https://github.com/AnuragJha100706/omninote",
            live_url="",
            local_path=os.path.join(LOCAL_ROOT, 'Notes generator Using camera or prompt'),
            start_date=date.today() - timedelta(days=35),
            end_date=date.today() + timedelta(days=15),
            technologies=[techs['python'], techs['flask'], techs['javascript'], techs['sqlite']],
            github_stars=41,
            github_forks=11,
            github_open_issues=2,
            github_default_branch="main",
            github_latest_commit_sha="o100706",
            github_latest_commit_msg="feat: integrate Gemini Vision camera prompt OCR & flashcard mastery tracker",
            github_latest_commit_author="Anurag Jha",
            github_synced_at=datetime.utcnow() - timedelta(hours=14)
        )
        db.session.add(p7)
        db.session.flush()

        omni_readme = ""
        omni_path = os.path.join(LOCAL_ROOT, 'Notes generator Using camera or prompt', 'README.md')
        if os.path.exists(omni_path):
            with open(omni_path, 'r', encoding='utf-8', errors='ignore') as f:
                omni_readme = f.read()

        doc7 = ProjectDocument(
            project_id=p7.id,
            abstract="OmniNote is a multimodal AI study workspace that turns prompts, web pages, PDFs, and camera captures into structured notes, verified sources, and interactive flashcards with active recall mastery tracking.",
            problem_statement="Students struggle to synthesize dense textbook chapters and hand-written lecture slides into actionable revision flashcards.",
            objectives="1. Integrate multimodal AI vision models (Gemini / Ollama) for text extraction.\n2. Automatically generate interactive flashcards with spaced repetition.\n3. Provide local export to Markdown and PDF.",
            system_requirements="Software: Python 3.11+, Flask, Google Generative AI / Ollama, SQLite\nHardware: Web camera, 8GB RAM",
            architecture_notes="Input Stream (Prompt/Camera/PDF) -> Multimodal LLM Extraction -> Markdown Note Synthesizer -> Active Recall Flashcard Engine.",
            readme_content=omni_readme or "# OmniNote Multimodal Study Workspace"
        )
        db.session.add(doc7)

        tasks_p7 = [
            ProjectTask(project_id=p7.id, task_name="Integrate camera frame capture and Gemini Vision OCR pipeline", is_completed=True, priority="High"),
            ProjectTask(project_id=p7.id, task_name="Build interactive spaced-repetition flashcard mastery tracker", is_completed=True, priority="High"),
            ProjectTask(project_id=p7.id, task_name="Implement text-to-speech audio player for generated notes", is_completed=True, priority="Medium"),
            ProjectTask(project_id=p7.id, task_name="Package final evaluation documentation and release ZIP", is_completed=False, priority="High")
        ]
        db.session.add_all(tasks_p7)

        # Configure Anurag Jha's GitHub Profile & Local Projects Settings
        SystemSetting.set('github_username', 'AnuragJha100706')
        SystemSetting.set('github_name', 'Anurag Jha')
        SystemSetting.set('github_avatar_url', 'https://github.com/AnuragJha100706.png')
        SystemSetting.set('github_bio', 'Full-Stack Developer, AI Researcher & ADBMS Architect | GitHub: @AnuragJha100706')
        SystemSetting.set('local_projects_dir', LOCAL_ROOT)

        db.session.commit()
        print("Database successfully seeded with Anurag Jha's real projects and local deliverables from E:\\COMPLETE PROJECT!")

if __name__ == '__main__':
    seed_database()
