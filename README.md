# DevVault: Advanced Engineering & Academic Repository System
### *High-Performance Partitioned SQLite Architecture • Procedural Triggers • Vibrant Glassmorphic UI*

<div align="center">

[![Python 3.12](https://img.shields.io/badge/Python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask 3.0](https://img.shields.io/badge/Flask-3.0%2B-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite 3 WAL](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Bootstrap 5.3](https://img.shields.io/badge/Bootstrap-5.3-7952B3.svg?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![Chart.js 4.4](https://img.shields.io/badge/Chart.js-4.4-FF6384.svg?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![GitHub AnuragJha100706](https://img.shields.io/badge/GitHub-@AnuragJha100706-indigo.svg?logo=github&logoColor=white)](https://github.com/AnuragJha100706)

**"A Centralized Engineering & Academic Workspace for Organizing, Documenting, and Vaulting Projects"**

</div>

---

## 🌟 Overview

**DevVault** is an enterprise-grade repository and artifact management platform engineered for software developers, engineering students, and researchers. It combines a **partitioned multi-database SQLite engine** with an **Aurora glassmorphic SaaS interface**.

DevVault replaces bloated monolithic tools with a clean, focused system structured around **strictly 4 core navigation pages** and a dedicated **Single Project Workspace**, backed by cryptographic SHA-256 deliverable verification and automated local filesystem scanning (`E:\COMPLETE PROJECT`).

---

## 💎 Core Pages & User Experience

DevVault features a modern **v2.4 Pro Glassmorphic UI** powered by Google Fonts (`Plus Jakarta Sans` and `JetBrains Mono`), Aurora mesh backgrounds, and a persistent dark/light mode toggle.

```
+---------------------------------------------------------------------------------------------------+
|  [DevVault v2.4 Pro]     [Dashboard]   [Projects]   [GitHub Profile]   [Export & Import]   [@Anurag]  |
+---------------------------------------------------------------------------------------------------+
```

### 1. Dashboard (`/` & `/dashboard`)
- **Author & Vault Status Banner:** Shows author `@AnuragJha100706` and local storage root with direct scanning triggers.
- **4 Vibrant KPI Cards:** Total Projects, In Progress, Vault Deliverables, and GitHub Linked metrics with top gradient accent bars.
- **3 Chart.js Visualizations:** Project Status Distribution (66% doughnut), Projects by Category (vertical bar), and Top Tech Stack distribution (horizontal bar).
- **Recent Projects & Timeline:** 8-column recent projects overview alongside an Activity Trail with academic readiness indicators.

### 2. Projects Repository (`/projects`)
- **Quick-Filter Category Chips:** One-click filtering across `All`, `AI & Machine Learning`, `Web Development`, and `Academic Research`.
- **Search & Filter Bar:** Instant search across title, short description, category, and tech stack tags.
- **3-Column Project Grid:** Cards featuring 6px category-matched top gradient accent bars, status badges, tech stack pills, and a monospace terminal path box with **one-click Copy Path**.
- **Integrated Creation Modal:** Add new projects directly without page reloads.

### 3. GitHub Profile & Sync (`/github`)
- **Developer Showcase:** Profile card featuring an Aurora gradient banner, verified checkmark badge, developer bio, and 3 tinted stat boxes (Public Repos, Followers, Active Status).
- **Direct Repository Importer:** Pulls repository metadata, descriptions, primary language, stars, forks, and `README.md` specs directly via the GitHub REST API.
- **3-Column Public Repositories Grid:** Displays repositories with color-coded language tags (Python, JavaScript, C++, HTML/CSS), live star/fork counters, and one-click import into DevVault.

### 4. Export & Import Hub (`/export`)
- **4 Partitioned Backup & Export Cards:**
  1. *Multi-DB Backup:* Bundles all 3 SQLite databases (`devvault_core.db`, `devvault_vault.db`, `devvault_audit.db`) in a single ZIP.
  2. *Full System Backup:* Bundles databases alongside all uploaded PDFs, PPTs, and source archives.
  3. *CSV Summary:* Exports spreadsheet catalog of projects and submission readiness.
  4. *JSON Data Export:* Complete machine-readable data export for portfolio ingestion.
- **Local Vault Scanner Table:** Detects folders in `E:\COMPLETE PROJECT`, automatically identifies tech stacks and archives, and enables **1-Click Import All**.

### 5. Nested Single Project Workspace (`/project/<id>`)
- **System Location & Project Links:** Monospace terminal path box with one-click `Copy Path`, GitHub Repository link, and Live Demo URL.
- **Deliverables & Document Vault:** Version-controlled uploads for Project Reports (`.pdf`, `.docx`), Slide Decks (`.pptx`), and source archives with automatic **SHA-256 cryptographic checksum** generation.
- **Edit Project Information:** In-place form to update titles, categories, progress status, system paths, and descriptions.

---

## 🏛️ Advanced Database Architecture (ADBMS)

DevVault uses a **partitioned multi-database SQLite architecture** with Write-Ahead Logging (WAL) and native Event-Condition-Action (ECA) procedural triggers:

```
                                 +-----------------------+
                                 |  DevVault Application |
                                 +-----------+-----------+
                                             |
                      +----------------------+----------------------+
                      |                      |                      |
                      v                      v                      v
             +-----------------+    +-----------------+    +-----------------+
             | devvault_core.db|    |devvault_vault.db|    |devvault_audit.db|
             +-----------------+    +-----------------+    +-----------------+
             | • Projects      |    | • Deliverables  |    | • Audit History |
             | • Categories    |    | • File Mimes    |    | • CDC Log       |
             | • Technologies  |    | • SHA-256 Hashes|    | • User Activity |
             | • Documentation |    +-----------------+    +-----------------+
             | • System Config |
             +-----------------+
```

- **Partition Isolation:** Transactional catalog data (`devvault_core.db`), high-capacity artifact manifests (`devvault_vault.db`), and immutable compliance history (`devvault_audit.db`) live in separate physical files under `instance/`.
- **Write-Ahead Logging (WAL):** Configured via `PRAGMA journal_mode = WAL;`, enabling simultaneous non-blocking concurrent reads and writes.
- **Native Engine Triggers:** SQLite ECA triggers automatically calculate project progress percentages at the C-engine layer.
- **Cryptographic Verification:** Every uploaded deliverable is hashed through `hashlib.sha256` to guarantee file integrity.

---

## 📁 Repository Structure

```text
devvault/
├── app.py                      # Flask backend, routing, API endpoints, and export handlers
├── models.py                   # Multi-bind SQLAlchemy models (Core, Vault, Audit partitions)
├── adbms_service.py            # SQLite WAL pragmas, ECA triggers, views, and federated joins
├── local_projects_service.py   # Filesystem scanner and 1-click importer for local projects
├── github_service.py           # GitHub REST API client (repo discovery, metadata sync)
├── seed_data.py                # Database seeder with realistic engineering projects
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules for Python, SQLite logs, and OS files
├── LICENSE                     # MIT License
├── instance/                   # Isolated physical SQLite database files
│   ├── devvault_core.db        # Partition 1: Projects, categories, techs, settings
│   ├── devvault_vault.db       # Partition 2: Deliverables manifest & SHA-256 hashes
│   └── devvault_audit.db       # Partition 3: Append-only compliance history & CDC
├── adbms_database_suite/       # Academic SQL scripts (SQLite & Oracle 19c PL/SQL)
│   ├── 01_SQLite_Multi_Database_Setup.sql
│   └── 02_Oracle_PLSQL_Enterprise_Package.sql
├── academic_submission_docs/   # Academic documentation suite
│   ├── 01_Project_Report.md
│   ├── 02_PPT_Slide_Deck.md
│   ├── 03_Diagrams_Mermaid.md
│   └── 04_Viva_Questions.md
├── static/
│   ├── css/style.css           # Vibrant glassmorphic stylesheet & Aurora mesh
│   ├── js/main.js              # Theme switcher, Chart.js integrations, toast notifications
│   └── uploads/                # Deliverable file vaults (reports, ppts, synopses, archives)
└── templates/
    ├── base.html               # Shared master layout with strictly 4 navigation links
    ├── dashboard.html          # Page 1: Dashboard overview & analytics
    ├── projects.html           # Page 2: Projects repository & creation modal
    ├── github.html             # Page 3: GitHub profile & repository sync
    ├── export.html             # Page 4: Export & import hub, local scanner
    └── project_detail.html     # Nested: Single project detail workspace
```

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/AnuragJha100706/DevVault.git
cd DevVault
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment (Optional)
```bash
cp .env.example .env
```
Edit `.env` if you wish to customize `LOCAL_PROJECTS_DIR` (defaults to `E:\COMPLETE PROJECT`) or add a `GITHUB_TOKEN` to increase API rate limits.

### 5. Initialize the Partitioned Databases
```bash
python seed_data.py
```

### 6. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 👤 Author & Maintainer

- **Developer:** Anurag Jha ([@AnuragJha100706](https://github.com/AnuragJha100706))
- **Email / Portfolio:** Available via [GitHub Profile](https://github.com/AnuragJha100706)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
