"""
DevVault - Database Models
Normalized SQLite Database using Flask-SQLAlchemy (9 Tables)
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 4. Many-to-Many Association Table: project_technologies
project_technologies = db.Table(
    'project_technologies',
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    db.Column('technology_id', db.Integer, db.ForeignKey('technologies.id', ondelete='CASCADE'), primary_key=True)
)


# 1. Project Categories
class ProjectCategory(db.Model):
    __tablename__ = 'project_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Relationships
    projects = db.relationship('Project', backref='category', lazy=True)

    def __repr__(self):
        return f"<ProjectCategory {self.name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'projects_count': len(self.projects)
        }


# 3. Technologies
class Technology(db.Model):
    __tablename__ = 'technologies'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Language, Framework, Database, Tool
    icon_class = db.Column(db.String(80), default='bi bi-code-slash')
    badge_color = db.Column(db.String(30), default='#0d6efd')

    def __repr__(self):
        return f"<Technology {self.name} ({self.category})>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'icon_class': self.icon_class,
            'badge_color': self.badge_color,
            'projects_count': len(self.projects)
        }


# 2. Projects
class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    short_description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('project_categories.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(50), default='In Progress')  # Idea, In Progress, Completed, On Hold, Archived
    progress_percentage = db.Column(db.Integer, default=0)    # 0 to 100
    github_url = db.Column(db.String(255), nullable=True)
    live_url = db.Column(db.String(255), nullable=True)
    local_path = db.Column(db.String(300), nullable=True)  # System location on local disk (e.g. E:\COMPLETE PROJECT\...)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Live GitHub Integration Cached Fields
    github_stars = db.Column(db.Integer, default=0)
    github_forks = db.Column(db.Integer, default=0)
    github_open_issues = db.Column(db.Integer, default=0)
    github_default_branch = db.Column(db.String(50), default='main')
    github_latest_commit_sha = db.Column(db.String(50), nullable=True)
    github_latest_commit_msg = db.Column(db.Text, nullable=True)
    github_latest_commit_date = db.Column(db.DateTime, nullable=True)
    github_latest_commit_author = db.Column(db.String(100), nullable=True)
    github_synced_at = db.Column(db.DateTime, nullable=True)

    # Relationships (Stored in devvault_core.db)
    technologies = db.relationship('Technology', secondary=project_technologies, backref='projects')
    document = db.relationship('ProjectDocument', backref='project', uselist=False, cascade='all, delete-orphan')
    notes = db.relationship('ProjectNote', backref='project', cascade='all, delete-orphan', order_by='ProjectNote.created_at.desc()')
    tasks = db.relationship('ProjectTask', backref='project', cascade='all, delete-orphan', order_by='ProjectTask.id.asc()')

    @property
    def deliverables(self):
        """Cross-Database query to partitioned Storage Engine (devvault_vault.db)."""
        return ProjectDeliverable.query.filter_by(project_id=self.id).order_by(ProjectDeliverable.uploaded_at.desc()).all()

    @property
    def history(self):
        """Cross-Database query to partitioned Audit & CDC Engine (devvault_audit.db)."""
        return ProjectHistory.query.filter_by(project_id=self.id).order_by(ProjectHistory.timestamp.desc()).all()

    def __repr__(self):
        return f"<Project {self.title}>"

    def recalculate_progress(self):
        """Automatically recalculates progress_percentage based on completed tasks."""
        total_tasks = len(self.tasks)
        if total_tasks > 0:
            completed_tasks = sum(1 for t in self.tasks if t.is_completed)
            self.progress_percentage = int(round((completed_tasks / total_tasks) * 100))
        return self.progress_percentage

    @property
    def checklist_status(self):
        """Calculates submission readiness status for mandatory academic deliverables."""
        deliverable_types = {d.deliverable_type for d in self.deliverables}
        
        has_synopsis = "Synopsis/Proposal" in deliverable_types
        has_report = "Project Report" in deliverable_types
        has_ppt = "Presentation PPT" in deliverable_types
        has_code = "Source Code ZIP" in deliverable_types
        
        mandatory_items = [has_synopsis, has_report, has_ppt, has_code]
        completed_count = sum(1 for item in mandatory_items if item)
        
        return {
            'has_synopsis': has_synopsis,
            'has_report': has_report,
            'has_ppt': has_ppt,
            'has_source_code': has_code,
            'completed_count': completed_count,
            'total_mandatory': 4,
            'percentage': int((completed_count / 4) * 100),
            'is_ready': completed_count == 4
        }

    @property
    def task_stats(self):
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks if t.is_completed)
        return {
            'total': total,
            'completed': completed,
            'pending': total - completed,
            'percentage': int(round((completed / total) * 100)) if total > 0 else self.progress_percentage
        }

    @property
    def github_repo_slug(self):
        """Extracts owner/repo from github_url."""
        if not self.github_url:
            return None
        import re
        match = re.search(r'(?:github\.com/|^)([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)', self.github_url)
        if match:
            owner = match.group(1)
            repo = match.group(2)
            if repo.endswith('.git'):
                repo = repo[:-4]
            return f"{owner}/{repo}"
        return None

    @property
    def is_github_linked(self):
        return bool(self.github_repo_slug)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'short_description': self.short_description,
            'category': self.category.name if self.category else None,
            'category_id': self.category_id,
            'status': self.status,
            'progress_percentage': self.progress_percentage,
            'github_url': self.github_url,
            'live_url': self.live_url,
            'local_path': self.local_path,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'technologies': [t.name for t in self.technologies],
            'tasks_count': len(self.tasks),
            'completed_tasks_count': sum(1 for t in self.tasks if t.is_completed),
            'deliverables_count': len(self.deliverables),
            'checklist': self.checklist_status
        }


# 5. Project Documents (Academic Specification & Structured Documentation)
class ProjectDocument(db.Model):
    __tablename__ = 'project_documents'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, unique=True)
    abstract = db.Column(db.Text, nullable=True)
    problem_statement = db.Column(db.Text, nullable=True)
    objectives = db.Column(db.Text, nullable=True)
    system_requirements = db.Column(db.Text, nullable=True)
    architecture_notes = db.Column(db.Text, nullable=True)
    readme_content = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<ProjectDocument for Project ID {self.project_id}>"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'abstract': self.abstract,
            'problem_statement': self.problem_statement,
            'objectives': self.objectives,
            'system_requirements': self.system_requirements,
            'architecture_notes': self.architecture_notes,
            'readme_content': self.readme_content
        }


# 6. Project Deliverables (Partitioned Storage Database: devvault_vault.db)
class ProjectDeliverable(db.Model):
    __tablename__ = 'project_deliverables'
    __bind_key__ = 'vault'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    deliverable_type = db.Column(
        db.String(80), 
        nullable=False
    )  # Project Report, Presentation PPT, Synopsis/Proposal, Research Paper, ER/UML Diagram, Source Code ZIP, Demo Video/Screenshots, Other
    file_path = db.Column(db.String(300), nullable=False)
    file_size = db.Column(db.Integer, default=0)  # in bytes
    file_hash_sha256 = db.Column(db.String(64), nullable=True)  # Cryptographic checksum for file verification
    version = db.Column(db.String(50), default='v1.0')
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<ProjectDeliverable {self.title} ({self.deliverable_type})>"

    @property
    def human_file_size(self):
        if not self.file_size or self.file_size == 0:
            return "0 B"
        bytes_val = float(self.file_size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"

    @property
    def file_extension(self):
        if '.' in self.file_path:
            return self.file_path.rsplit('.', 1)[1].lower()
        return ""

    @property
    def icon_class(self):
        ext = self.file_extension
        dtype = self.deliverable_type.lower()
        if 'report' in dtype or ext == 'pdf':
            return 'bi bi-file-earmark-pdf text-danger'
        elif 'ppt' in dtype or ext in ['pptx', 'ppt']:
            return 'bi bi-file-earmark-slides text-warning'
        elif 'synopsis' in dtype or ext in ['docx', 'doc']:
            return 'bi bi-file-earmark-word text-primary'
        elif 'diagram' in dtype or ext in ['png', 'jpg', 'jpeg', 'svg']:
            return 'bi bi-diagram-3 text-info'
        elif 'source' in dtype or ext in ['zip', 'tar', 'gz', 'rar']:
            return 'bi bi-file-earmark-zip text-success'
        elif 'video' in dtype or 'screenshot' in dtype or ext in ['mp4', 'mov', 'webm']:
            return 'bi bi-camera-video text-secondary'
        return 'bi bi-file-earmark-text text-muted'

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'title': self.title,
            'deliverable_type': self.deliverable_type,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'human_file_size': self.human_file_size,
            'file_hash_sha256': self.file_hash_sha256,
            'version': self.version,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'notes': self.notes
        }


# 7. Project Notes (Chronological Developer Journal)
class ProjectNote(db.Model):
    __tablename__ = 'project_notes'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    note_type = db.Column(db.String(50), default='Dev Log')  # Dev Log, Bug Fix, Idea, Todo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ProjectNote {self.title} ({self.note_type})>"

    @property
    def badge_class(self):
        mapping = {
            'Dev Log': 'bg-primary',
            'Bug Fix': 'bg-danger',
            'Idea': 'bg-warning text-dark',
            'Todo': 'bg-info text-dark'
        }
        return mapping.get(self.note_type, 'bg-secondary')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'title': self.title,
            'content': self.content,
            'note_type': self.note_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 8. Project Tasks (Milestones & Interactive Checklist)
class ProjectTask(db.Model):
    __tablename__ = 'project_tasks'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    task_name = db.Column(db.String(200), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default='Medium')  # Low, Medium, High
    due_date = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f"<ProjectTask {self.task_name} (Done: {self.is_completed})>"

    @property
    def priority_badge_class(self):
        mapping = {
            'High': 'bg-danger',
            'Medium': 'bg-warning text-dark',
            'Low': 'bg-secondary'
        }
        return mapping.get(self.priority, 'bg-info text-dark')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'task_name': self.task_name,
            'is_completed': self.is_completed,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None
        }


# 9. Project History (Partitioned Audit & CDC Database: devvault_audit.db)
class ProjectHistory(db.Model):
    __tablename__ = 'project_history'
    __bind_key__ = 'audit'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, nullable=False, index=True)
    action_type = db.Column(db.String(50), nullable=False)  # Created, Status Updated, File Uploaded, Doc Edited, Task Toggled, Note Added
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='INFO')      # INFO, WARN, CRITICAL
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ProjectHistory {self.action_type} on {self.timestamp}>"

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'action_type': self.action_type,
            'description': self.description,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


# 11. Database Change Log (Change Data Capture / CDC in devvault_audit.db)
class DatabaseChangeLog(db.Model):
    __tablename__ = 'database_change_log'
    __bind_key__ = 'audit'

    id = db.Column(db.Integer, primary_key=True)
    target_database = db.Column(db.String(50), nullable=False)
    table_name = db.Column(db.String(80), nullable=False)
    operation = db.Column(db.String(20), nullable=False)     # INSERT, UPDATE, DELETE
    record_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def icon_class(self):
        mapping = {
            'Created': 'bi bi-plus-circle text-success',
            'Status Updated': 'bi bi-arrow-repeat text-info',
            'File Uploaded': 'bi bi-cloud-arrow-up text-primary',
            'File Deleted': 'bi bi-trash text-danger',
            'Doc Edited': 'bi bi-pencil-square text-warning',
            'Task Toggled': 'bi bi-check2-square text-success',
            'Task Added': 'bi bi-list-task text-primary',
            'Task Deleted': 'bi bi-trash text-muted',
            'Note Added': 'bi bi-journal-text text-secondary',
            'Note Deleted': 'bi bi-trash text-muted'
        }
        return mapping.get(self.action_type, 'bi bi-dot text-secondary')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'action_type': self.action_type,
            'description': self.description,
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


# 10. System & Integration Settings (e.g. GitHub credentials & profile cache)
class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SystemSetting {self.key}>"

    @classmethod
    def get(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting and setting.value else default

    @classmethod
    def set(cls, key, value):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = cls(key=key, value=value, updated_at=datetime.utcnow())
            db.session.add(setting)
        db.session.commit()
        return setting
