r"""
DevVault - Local Projects Scanner & Vault Service
Manages local project directories, file discovery, deliverable association,
and 1-click importing from E:\COMPLETE PROJECT.
Author: Anurag Jha (GitHub: AnuragJha100706)
"""
import os
import re
import glob
from datetime import datetime
from models import (
    db, Project, ProjectCategory, Technology,
    ProjectDocument, ProjectDeliverable, ProjectTask, ProjectHistory,
    SystemSetting
)
from adbms_service import ADBMSManager

DEFAULT_LOCAL_PROJECTS_DIR = os.environ.get('LOCAL_PROJECTS_DIR', r"E:\COMPLETE PROJECT")

PROJECT_TITLE_MAP = {
    'velvetfork_webproject': 'The Velvet Fork: Luxury Digital Dining & Reservation Platform',
    'music recommandation system': 'VibeNest AI: Intelligent Music Recommendation System',
    'collage event management system': 'College Event Management System (CEMS)',
    'DMDW PROJECT': 'DMDW: Data Mining & Warehousing Predictive Analytics Platform',
    'javareport': 'Java Student Academic Evaluation & Lab Management System',
    'MusicPlayer': 'Harmonix: Smart Audio & Media Player for Android',
    'Notes generator Using camera or prompt': 'OmniNote: Multimodal AI Study Workspace & Flashcard Generator',
    'chatbot shadow new': 'Shadow AI: Conversational Chatbot & Natural Language Assistant',
    'Machine learning project': 'NutriRecipe: Machine Learning Recipe & Nutrition Recommendation Engine',
    'project portfolio': 'Personal Developer Portfolio & Academic Showcase',
    'python game maze': 'CyberMaze: Interactive Python Algorithmic Maze Runner',
    'Qr code generator': 'Dynamic QR Code Generator & Analytics Tool',
    'Restaurant Website Free': 'BistroModern: Responsive Hospitality & Table Reservation Portal',
    'SMS WEB': 'EduSMS: Web-Based Student Notification & Messaging System',
    'weka project imdb': 'IMDB Sentiment Mining & Weka Classifier Benchmark',
    'pymaze': 'PyMaze: Pathfinding Algorithm Visualizer'
}

CATEGORY_MAP = {
    'velvetfork_webproject': 'Web Development',
    'collage event management system': 'Web Development',
    'Restaurant Website Free': 'Web Development',
    'SMS WEB': 'Web Development',
    'project portfolio': 'Web Development',
    'music recommandation system': 'AI & Machine Learning',
    'chatbot shadow new': 'AI & Machine Learning',
    'Machine learning project': 'AI & Machine Learning',
    'Notes generator Using camera or prompt': 'AI & Machine Learning',
    'DMDW PROJECT': 'Academic Research',
    'javareport': 'Academic Research',
    'weka project imdb': 'Academic Research',
    'MusicPlayer': 'Mobile Development',
    'python game maze': 'Academic Research',
    'pymaze': 'Academic Research',
    'Qr code generator': 'Web Development'
}

TECH_RULES = [
    (['package.json'], 'Node.js', 'Framework', 'bi bi-hexagon-fill', '#339933'),
    (['vite.config.js', 'vite.config.ts'], 'Vite', 'Tool', 'bi bi-lightning-fill', '#646cff'),
    (['tailwind.config.js'], 'Tailwind CSS', 'Framework', 'bi bi-palette-fill', '#06b6d4'),
    (['requirements.txt', 'app.py', 'run.py', 'main.py'], 'Python', 'Language', 'bi bi-filetype-py', '#3776ab'),
    (['app.py', 'run.py'], 'Flask', 'Framework', 'bi bi-layers-fill', '#000000'),
    (['build.gradle', 'build.gradle.kts'], 'Kotlin / Android', 'Language', 'bi bi-phone', '#7f52ff'),
    (['index.html'], 'HTML5 / CSS3', 'Language', 'bi bi-filetype-html', '#e34f26'),
    (['*.csv', '*.pickle', '*.h5'], 'Data Science / ML', 'Tool', 'bi bi-graph-up', '#ff6f00'),
    (['*.java'], 'Java', 'Language', 'bi bi-filetype-java', '#b07219'),
    (['*.sqlite', 'database.sqlite', '*.db'], 'SQLite', 'Database', 'bi bi-database-fill', '#003b57')
]


class LocalProjectsService:
    def __init__(self, root_dir=None):
        self.root_dir = root_dir or SystemSetting.get('local_projects_dir', DEFAULT_LOCAL_PROJECTS_DIR)

    def get_projects_directory(self):
        return self.root_dir

    def scan_directory(self):
        r"""
        Scans E:\COMPLETE PROJECT for all project subdirectories,
        inspecting files, documentation, deliverables, and import status.
        """
        if not os.path.exists(self.root_dir):
            return {
                'success': False,
                'error': f"Directory '{self.root_dir}' does not exist on disk.",
                'projects': []
            }

        existing_projects = Project.query.all()
        existing_slugs = {p.slug.lower(): p for p in existing_projects}
        existing_titles = {p.title.lower(): p for p in existing_projects}

        projects = []
        try:
            subdirs = [
                d for d in os.listdir(self.root_dir)
                if os.path.isdir(os.path.join(self.root_dir, d)) and not d.startswith('.')
            ]
        except Exception as e:
            return {'success': False, 'error': str(e), 'projects': []}

        for folder_name in sorted(subdirs):
            folder_path = os.path.join(self.root_dir, folder_name)
            stat = os.stat(folder_path)
            last_modified = datetime.fromtimestamp(stat.st_mtime)

            # Detect title
            display_title = PROJECT_TITLE_MAP.get(
                folder_name,
                folder_name.replace('-', ' ').replace('_', ' ').title()
            )

            # Detect files
            try:
                top_files = os.listdir(folder_path)
            except Exception:
                top_files = []

            # Detect README / Documentation
            doc_file = None
            doc_snippet = ""
            for doc_cand in ['CASE-STUDY.md', 'README.md', 'readme.md', 'README.txt']:
                cand_path = os.path.join(folder_path, doc_cand)
                if os.path.exists(cand_path):
                    doc_file = doc_cand
                    try:
                        with open(cand_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
                            doc_snippet = lines[0] if lines else "Local project documentation available."
                    except Exception:
                        doc_snippet = "Documentation file detected."
                    break

            # Detect associated deliverables in root folder or inside subfolder
            deliverables = []
            
            # 1. Matching ZIP/RAR in E:\COMPLETE PROJECT\
            for ext in ['.zip', '.rar', '.tar.gz', '.7z']:
                cand_archive = os.path.join(self.root_dir, f"{folder_name}{ext}")
                if os.path.exists(cand_archive):
                    size = os.path.getsize(cand_archive)
                    deliverables.append({
                        'title': f"{display_title} Source Code Archive ({ext.lstrip('.').upper()})",
                        'deliverable_type': 'Source Code ZIP',
                        'file_path': cand_archive,
                        'file_size': size,
                        'version': 'v1.0-archive'
                    })

            # 2. Documents inside the project folder (.docx, .pdf, .pptx, .mp4)
            for f in top_files:
                f_lower = f.lower()
                f_path = os.path.join(folder_path, f)
                if os.path.isfile(f_path):
                    if f_lower.endswith('.docx') or f_lower.endswith('.doc'):
                        deliverables.append({
                            'title': f"Project Report: {f}",
                            'deliverable_type': 'Project Report',
                            'file_path': f_path,
                            'file_size': os.path.getsize(f_path),
                            'version': 'v1.0'
                        })
                    elif f_lower.endswith('.pptx') or f_lower.endswith('.ppt'):
                        deliverables.append({
                            'title': f"Presentation Slide Deck: {f}",
                            'deliverable_type': 'Presentation PPT',
                            'file_path': f_path,
                            'file_size': os.path.getsize(f_path),
                            'version': 'v1.0'
                        })
                    elif f_lower.endswith('.pdf') and not f_lower.endswith('manual.pdf'):
                        deliverables.append({
                            'title': f"Academic Deliverable: {f}",
                            'deliverable_type': 'Project Report' if 'report' in f_lower else 'Research Paper',
                            'file_path': f_path,
                            'file_size': os.path.getsize(f_path),
                            'version': 'v1.0'
                        })
                    elif f_lower.endswith('.mp4') or f_lower.endswith('.webm'):
                        deliverables.append({
                            'title': f"Demonstration Video: {f}",
                            'deliverable_type': 'Demo Video/Screenshots',
                            'file_path': f_path,
                            'file_size': os.path.getsize(f_path),
                            'version': 'v1.0'
                        })

            # Detect tech stack
            detected_techs = []
            for patterns, tech_name, cat, icon, color in TECH_RULES:
                matched = False
                for p in patterns:
                    if '*' in p:
                        if glob.glob(os.path.join(folder_path, p)):
                            matched = True
                            break
                    elif p in top_files:
                        matched = True
                        break
                if matched and tech_name not in detected_techs:
                    detected_techs.append(tech_name)

            # Check if imported
            clean_slug = re.sub(r'[^a-zA-Z0-9]+', '-', folder_name.lower()).strip('-')
            is_imported = False
            linked_project = None
            if clean_slug in existing_slugs:
                is_imported = True
                linked_project = existing_slugs[clean_slug]
            elif display_title.lower() in existing_titles:
                is_imported = True
                linked_project = existing_titles[display_title.lower()]

            category_name = CATEGORY_MAP.get(folder_name, 'Web Development')

            projects.append({
                'folder_name': folder_name,
                'folder_path': folder_path,
                'title': display_title,
                'slug': clean_slug,
                'category_name': category_name,
                'last_modified': last_modified,
                'file_count': len(top_files),
                'doc_file': doc_file,
                'doc_snippet': doc_snippet,
                'deliverables': deliverables,
                'detected_techs': detected_techs,
                'is_imported': is_imported,
                'project_id': linked_project.id if linked_project else None,
                'github_suggested_url': f"https://github.com/AnuragJha100706/{clean_slug}"
            })

        return {
            'success': True,
            'root_dir': self.root_dir,
            'total_found': len(projects),
            'projects': projects
        }

    def import_project(self, folder_name):
        r"""Imports a single local project folder from E:\COMPLETE PROJECT into DevVault."""
        scan = self.scan_directory()
        if not scan['success']:
            return {'success': False, 'error': scan['error']}

        target = next((p for p in scan['projects'] if p['folder_name'] == folder_name), None)
        if not target:
            return {'success': False, 'error': f"Project folder '{folder_name}' not found in {self.root_dir}."}

        # Check category
        cat = ProjectCategory.query.filter_by(name=target['category_name']).first()
        if not cat:
            cat = ProjectCategory.query.first()

        # Check existing project
        proj = Project.query.filter_by(slug=target['slug']).first()
        if not proj:
            proj = Project(
                title=target['title'],
                slug=target['slug'],
                short_description=target['doc_snippet'] or f"Imported from local projects vault at E:\\COMPLETE PROJECT\\{folder_name}.",
                category_id=cat.id if cat else None,
                status="Completed" if target['deliverables'] else "In Progress",
                progress_percentage=100 if target['deliverables'] else 80,
                github_url=target['github_suggested_url'],
                local_path=target['folder_path'],
                start_date=target['last_modified'].date(),
                end_date=datetime.utcnow().date(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(proj)
            db.session.flush()
        else:
            proj.local_path = target['folder_path']
            proj.updated_at = datetime.utcnow()

        # Technologies association
        for t_name in target['detected_techs']:
            tech = Technology.query.filter(Technology.name.ilike(f"%{t_name}%")).first()
            if not tech:
                tech = Technology(
                    name=t_name,
                    category='Tool',
                    icon_class='bi bi-code-square',
                    badge_color='#0d6efd'
                )
                db.session.add(tech)
                db.session.flush()
            if tech not in proj.technologies:
                proj.technologies.append(tech)

        # Ingest Documentation
        readme_content = f"# {target['title']}\n\nLocal project repository imported from `{target['folder_path']}`.\n\nAuthor: Anurag Jha (https://github.com/AnuragJha100706)"
        if target['doc_file']:
            doc_path = os.path.join(target['folder_path'], target['doc_file'])
            try:
                with open(doc_path, 'r', encoding='utf-8', errors='ignore') as f:
                    readme_content = f.read()
            except Exception:
                pass

        if not proj.document:
            doc = ProjectDocument(
                project_id=proj.id,
                abstract=target['doc_snippet'] or f"Academic project implemented in {target['category_name']}.",
                problem_statement="Requires structured local and academic deliverables archiving.",
                objectives=f"1. Implement {target['title']}.\n2. Maintain verified local source archive and documentation.",
                system_requirements="Software Requirements: Python / Node / Java, SQLite\nHardware: 4GB RAM minimum",
                architecture_notes="Clean modular architecture managed in DevVault repository.",
                readme_content=readme_content
            )
            db.session.add(doc)
        else:
            proj.document.readme_content = readme_content

        # Register Deliverables in devvault_vault.db with SHA-256
        added_deliverables = 0
        for d in target['deliverables']:
            # Check if deliverable path already registered
            existing_d = ProjectDeliverable.query.filter_by(
                project_id=proj.id,
                file_path=d['file_path']
            ).first()

            if not existing_d:
                sha_hash = ADBMSManager.calculate_file_sha256(d['file_path'])
                deliv = ProjectDeliverable(
                    project_id=proj.id,
                    title=d['title'],
                    deliverable_type=d['deliverable_type'],
                    file_path=d['file_path'],
                    file_size=d['file_size'],
                    file_hash_sha256=sha_hash,
                    version=d['version'],
                    notes=f"Discovered in {self.root_dir}",
                    uploaded_at=datetime.utcnow()
                )
                db.session.add(deliv)
                added_deliverables += 1

        # Tasks
        if not proj.tasks:
            tasks = [
                ProjectTask(project_id=proj.id, task_name="Establish core architecture and repository structure", is_completed=True, priority="High"),
                ProjectTask(project_id=proj.id, task_name="Implement functional requirements and backend logic", is_completed=True, priority="High"),
                ProjectTask(project_id=proj.id, task_name="Integrate responsive user interface and controls", is_completed=True, priority="Medium"),
                ProjectTask(project_id=proj.id, task_name="Package deliverables archive and project documentation", is_completed=bool(target['deliverables']), priority="Medium")
            ]
            db.session.add_all(tasks)

        # Audit History
        log = ProjectHistory(
            project_id=proj.id,
            action_type="Created",
            description=f"Imported from local project directory: '{target['folder_path']}' with {added_deliverables} deliverable attachments.",
            severity="SUCCESS",
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()

        return {
            'success': True,
            'project_id': proj.id,
            'title': proj.title,
            'deliverables_count': added_deliverables
        }

    def import_all(self):
        r"""Imports all detected unimported projects from E:\COMPLETE PROJECT."""
        scan = self.scan_directory()
        if not scan['success']:
            return {'success': False, 'error': scan['error'], 'imported_count': 0}

        imported = 0
        for p in scan['projects']:
            if not p['is_imported']:
                res = self.import_project(p['folder_name'])
                if res['success']:
                    imported += 1

        return {'success': True, 'imported_count': imported}
