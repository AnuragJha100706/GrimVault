"""
DevVault: A Personal Project Repository and Information Management System
Flask Backend Application
"""
import os
import io
import re
import csv
import json
import zipfile
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, jsonify, send_file, send_from_directory, abort
)
from werkzeug.utils import secure_filename
import markdown

from models import (
    db, Project, ProjectCategory, Technology, project_technologies,
    ProjectDocument, ProjectDeliverable, ProjectNote, ProjectTask, ProjectHistory,
    SystemSetting, DatabaseChangeLog
)
from github_service import GitHubService
from adbms_service import ADBMSManager
from local_projects_service import LocalProjectsService
from adbms_service import ADBMSManager
from local_projects_service import LocalProjectsService

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devvault-academic-secret-key-2026')

# ADBMS Multi-Database Configuration: Partitioned Architecture
os.makedirs(app.instance_path, exist_ok=True)
core_db_path = os.path.join(app.instance_path, 'devvault_core.db').replace('\\', '/')
vault_db_path = os.path.join(app.instance_path, 'devvault_vault.db').replace('\\', '/')
audit_db_path = os.path.join(app.instance_path, 'devvault_audit.db').replace('\\', '/')

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('CORE_DB_URI', f"sqlite:///{core_db_path}")
app.config['SQLALCHEMY_BINDS'] = {
    'vault': os.environ.get('VAULT_DB_URI', f"sqlite:///{vault_db_path}"),
    'audit': os.environ.get('AUDIT_DB_URI', f"sqlite:///{audit_db_path}")
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64 MB Max Upload

adbms_manager = ADBMSManager(app.instance_path)

# Upload folder configuration
UPLOAD_BASE = os.path.join(app.root_path, 'static', 'uploads')
UPLOAD_FOLDERS = {
    'Project Report': os.path.join(UPLOAD_BASE, 'reports'),
    'Presentation PPT': os.path.join(UPLOAD_BASE, 'ppts'),
    'Synopsis/Proposal': os.path.join(UPLOAD_BASE, 'synopses'),
    'Research Paper': os.path.join(UPLOAD_BASE, 'reports'),
    'ER/UML Diagram': os.path.join(UPLOAD_BASE, 'diagrams'),
    'Source Code ZIP': os.path.join(UPLOAD_BASE, 'archives'),
    'Demo Video/Screenshots': os.path.join(UPLOAD_BASE, 'media'),
    'Other': os.path.join(UPLOAD_BASE, 'media')
}

ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'doc', 'pptx', 'ppt', 'zip', 'tar', 'gz', 
    'png', 'jpg', 'jpeg', 'svg', 'mp4', 'webm', 'txt', 'md'
}

# Ensure upload folders exist
for folder in UPLOAD_FOLDERS.values():
    os.makedirs(folder, exist_ok=True)

db.init_app(app)


# --- Helper Utilities ---

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_slug(title, project_id=None):
    base = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')
    if not base:
        base = 'project'
    slug = base
    counter = 1
    query = Project.query.filter_by(slug=slug)
    if project_id:
        query = query.filter(Project.id != project_id)
    while query.first() is not None:
        slug = f"{base}-{counter}"
        counter += 1
        query = Project.query.filter_by(slug=slug)
        if project_id:
            query = query.filter(Project.id != project_id)
    return slug

def log_history(project_id, action_type, description, severity='INFO'):
    try:
        entry = ProjectHistory(
            project_id=project_id,
            action_type=action_type,
            description=description,
            severity=severity,
            timestamp=datetime.utcnow()
        )
        db.session.add(entry)
    except Exception as e:
        app.logger.error(f"Error logging history to devvault_audit.db: {e}")

@app.template_filter('render_markdown')
def render_markdown_filter(text):
    if not text:
        return ""
    return markdown.markdown(text, extensions=['fenced_code', 'tables', 'nl2br'])

@app.context_processor
def inject_global_context():
    gh_username = SystemSetting.get('github_username')
    gh_avatar = SystemSetting.get('github_avatar_url')
    gh_name = SystemSetting.get('github_name')
    return {
        'github_connected_user': gh_username,
        'github_avatar_url': gh_avatar,
        'github_name': gh_name
    }


# --- 1. Dashboard Route ---

@app.route('/')
@app.route('/dashboard')
def dashboard():
    total_projects = Project.query.count()
    completed_projects = Project.query.filter_by(status='Completed').count()
    inprogress_projects = Project.query.filter_by(status='In Progress').count()
    total_technologies = Technology.query.count()
    total_deliverables = ProjectDeliverable.query.count()
    total_reports_ppts = ProjectDeliverable.query.filter(
        ProjectDeliverable.deliverable_type.in_(['Project Report', 'Presentation PPT', 'Synopsis/Proposal'])
    ).count()
    github_linked_count = Project.query.filter(Project.github_url.isnot(None), Project.github_url != '').count()

    # Status distribution for Chart.js
    statuses = ['Idea', 'In Progress', 'Completed', 'On Hold', 'Archived']
    status_counts = {s: Project.query.filter_by(status=s).count() for s in statuses}

    # Categories distribution for Chart.js
    categories = ProjectCategory.query.all()
    category_labels = [c.name for c in categories]
    category_counts = [len(c.projects) for c in categories]

    # Top Technologies for Chart.js
    all_techs = Technology.query.all()
    # Sort by number of projects
    tech_data = sorted(all_techs, key=lambda t: len(t.projects), reverse=True)[:8]
    tech_labels = [t.name for t in tech_data]
    tech_counts = [len(t.projects) for t in tech_data]

    # Recent Activities (History)
    recent_history = ProjectHistory.query.order_by(ProjectHistory.timestamp.desc()).limit(12).all()

    # Recently Updated Projects
    recent_projects = Project.query.order_by(Project.updated_at.desc()).limit(6).all()

    return render_template(
        'dashboard.html',
        total_projects=total_projects,
        completed_projects=completed_projects,
        inprogress_projects=inprogress_projects,
        total_technologies=total_technologies,
        total_deliverables=total_deliverables,
        total_reports_ppts=total_reports_ppts,
        github_linked_count=github_linked_count,
        status_counts=status_counts,
        category_labels=category_labels,
        category_counts=category_counts,
        tech_labels=tech_labels,
        tech_counts=tech_counts,
        recent_history=recent_history,
        recent_projects=recent_projects
    )


# --- 2. Projects List & Advanced Search Route ---

@app.route('/projects')
def projects_list():
    query = Project.query

    keyword = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    status = request.args.get('status', '').strip()
    tech_id = request.args.get('tech', type=int)
    deliverable_filter = request.args.get('deliverable', '').strip()
    view_mode = request.args.get('view', 'grid')  # grid or table
    sort_by = request.args.get('sort', 'updated_desc')

    if keyword:
        search_pattern = f"%{keyword}%"
        query = query.filter(
            db.or_(
                Project.title.ilike(search_pattern),
                Project.short_description.ilike(search_pattern)
            )
        )

    if category_id:
        query = query.filter(Project.category_id == category_id)

    if status and status != 'All':
        query = query.filter(Project.status == status)

    if tech_id:
        query = query.join(Project.technologies).filter(Technology.id == tech_id)

    # Sorting
    if sort_by == 'created_desc':
        query = query.order_by(Project.created_at.desc())
    elif sort_by == 'title_asc':
        query = query.order_by(Project.title.asc())
    elif sort_by == 'progress_desc':
        query = query.order_by(Project.progress_percentage.desc())
    else:  # updated_desc
        query = query.order_by(Project.updated_at.desc())

    projects = query.all()

    # In-memory deliverable filtering if specified
    if deliverable_filter == 'has_report':
        projects = [p for p in projects if p.checklist_status['has_report']]
    elif deliverable_filter == 'has_ppt':
        projects = [p for p in projects if p.checklist_status['has_ppt']]
    elif deliverable_filter == 'all_complete':
        projects = [p for p in projects if p.checklist_status['is_ready']]
    elif deliverable_filter == 'missing_mandatory':
        projects = [p for p in projects if not p.checklist_status['is_ready']]

    categories = ProjectCategory.query.order_by(ProjectCategory.name).all()
    technologies = Technology.query.order_by(Technology.name).all()

    return render_template(
        'projects.html',
        view_mode=view_mode,
        projects=projects,
        categories=categories,
        technologies=technologies,
        keyword=keyword,
        selected_category=category_id,
        selected_status=status,
        selected_tech=tech_id,
        selected_deliverable=deliverable_filter,
        sort_by=sort_by,
        total_found=len(projects)
    )

@app.route('/search')
def search_redirect():
    return redirect(url_for('projects_list', **request.args))


# --- 3. Project Creation & Edit Routes ---

@app.route('/projects/new', methods=['GET', 'POST'])
def project_create():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        short_description = request.form.get('short_description', '').strip()
        category_id = request.form.get('category_id', type=int)
        status = request.form.get('status', 'In Progress')
        progress_percentage = request.form.get('progress_percentage', type=int) or 0
        github_url = request.form.get('github_url', '').strip()
        live_url = request.form.get('live_url', '').strip()
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        selected_tech_ids = request.form.getlist('technologies', type=int)

        if not title:
            flash('Project title is mandatory.', 'danger')
            return redirect(url_for('project_create'))

        slug = generate_slug(title)

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

        local_path = request.form.get('local_path', '').strip()

        project = Project(
            title=title,
            slug=slug,
            short_description=short_description,
            category_id=category_id,
            status=status,
            progress_percentage=min(max(progress_percentage, 0), 100),
            github_url=github_url,
            live_url=live_url,
            local_path=local_path,
            start_date=start_date,
            end_date=end_date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        if selected_tech_ids:
            techs = Technology.query.filter(Technology.id.in_(selected_tech_ids)).all()
            project.technologies = techs

        db.session.add(project)
        db.session.flush()  # get project.id

        # Create corresponding empty documentation record
        doc = ProjectDocument(
            project_id=project.id,
            abstract="",
            problem_statement="",
            objectives="",
            system_requirements="",
            architecture_notes="",
            readme_content=f"# {project.title}\n\n{project.short_description}\n\n## Getting Started\n- Clone repository\n- Install requirements"
        )
        db.session.add(doc)

        # Log project creation
        log_history(project.id, 'Created', f"Project '{project.title}' was created.")
        db.session.commit()

        flash(f"Project '{project.title}' initialized successfully!", 'success')
        return redirect(url_for('project_detail', project_id=project.id))

    return redirect(url_for('projects_list', open_modal='new'))

@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
def project_edit(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        if not title:
            flash('Project title is required.', 'danger')
            return redirect(url_for('project_edit', project_id=project.id))

        project.title = title
        project.slug = generate_slug(title, project_id=project.id)
        project.short_description = request.form.get('short_description', '').strip()
        project.category_id = request.form.get('category_id', type=int)
        
        old_status = project.status
        new_status = request.form.get('status', project.status)
        project.status = new_status

        # If user overrides progress
        manual_progress = request.form.get('progress_percentage', type=int)
        if manual_progress is not None:
            project.progress_percentage = min(max(manual_progress, 0), 100)

        project.github_url = request.form.get('github_url', '').strip()
        project.live_url = request.form.get('live_url', '').strip()
        project.local_path = request.form.get('local_path', '').strip()
        
        start_date_str = request.form.get('start_date', '').strip()
        end_date_str = request.form.get('end_date', '').strip()
        project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        project.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        project.updated_at = datetime.utcnow()

        selected_tech_ids = request.form.getlist('technologies', type=int)
        project.technologies = Technology.query.filter(Technology.id.in_(selected_tech_ids)).all()

        log_description = f"Project details updated."
        if old_status != new_status:
            log_description += f" Status changed from '{old_status}' to '{new_status}'."
            log_history(project.id, 'Status Updated', log_description)
        else:
            log_history(project.id, 'Doc Edited', log_description)

        db.session.commit()
        flash('Project details updated successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))

    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/project/<int:project_id>/edit-info', methods=['POST'])
def project_edit_info(project_id):
    project = Project.query.get_or_404(project_id)
    title = request.form.get('title', '').strip()
    if title:
        project.title = title
    project.short_description = request.form.get('short_description', '').strip()
    category_id = request.form.get('category_id', type=int)
    if category_id:
        project.category_id = category_id
    project.status = request.form.get('status', project.status)
    project.local_path = request.form.get('local_path', '').strip()
    project.github_url = request.form.get('github_url', '').strip()
    project.live_url = request.form.get('live_url', '').strip()
    project.updated_at = datetime.utcnow()

    log_history(project.id, 'Status Updated', f"Updated project details: '{project.title}'")
    db.session.commit()

    flash(f"Project '{project.title}' info updated successfully!", 'success')
    next_url = request.form.get('next_url')
    if next_url:
        return redirect(next_url)
    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/project/<int:project_id>/delete', methods=['POST'])
def project_delete(project_id):
    project = Project.query.get_or_404(project_id)
    title = project.title

    # Remove deliverables files from filesystem
    for deliverable in project.deliverables:
        abs_path = os.path.join(app.root_path, deliverable.file_path.lstrip('/'))
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except Exception as e:
                app.logger.warning(f"Could not remove file {abs_path}: {e}")

    # Explicit cross-database cleanup across partitioned SQLite engines
    ProjectDeliverable.query.filter_by(project_id=project.id).delete()
    ProjectHistory.query.filter_by(project_id=project.id).delete()

    db.session.delete(project)
    db.session.commit()
    flash(f"Project '{title}' and all associated deliverables have been deleted.", 'info')
    return redirect(url_for('projects_list'))


# --- 4. Single Project Workspace (Tabbed View) ---

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    active_tab = request.args.get('tab', 'overview')

    # Ensure document object exists
    if not project.document:
        doc = ProjectDocument(project_id=project.id, readme_content=f"# {project.title}")
        db.session.add(doc)
        db.session.commit()

    all_categories = ProjectCategory.query.order_by(ProjectCategory.name).all()
    all_technologies = Technology.query.order_by(Technology.category, Technology.name).all()

    return render_template(
        'project_detail.html',
        project=project,
        all_categories=all_categories,
        all_technologies=all_technologies
    )


# --- 5. Project Documentation Routes ---

@app.route('/project/<int:project_id>/docs/update', methods=['POST'])
def project_docs_update(project_id):
    project = Project.query.get_or_404(project_id)
    doc = project.document
    if not doc:
        doc = ProjectDocument(project_id=project.id)
        db.session.add(doc)

    doc.abstract = request.form.get('abstract', '').strip()
    doc.problem_statement = request.form.get('problem_statement', '').strip()
    doc.objectives = request.form.get('objectives', '').strip()
    doc.system_requirements = request.form.get('system_requirements', '').strip()
    doc.architecture_notes = request.form.get('architecture_notes', '').strip()
    doc.readme_content = request.form.get('readme_content', '').strip()

    project.updated_at = datetime.utcnow()
    log_history(project.id, 'Doc Edited', 'Updated project documentation and specifications.')
    db.session.commit()

    flash('Academic documentation saved successfully!', 'success')
    return redirect(url_for('project_detail', project_id=project.id, tab='docs'))


# --- 6. Academic Deliverables & File Vault Routes ---

@app.route('/project/<int:project_id>/deliverables/upload', methods=['POST'])
@app.route('/project/<int:project_id>/upload-document', methods=['POST'], endpoint='project_upload_document')
def deliverable_upload(project_id):
    project = Project.query.get_or_404(project_id)
    next_url = request.form.get('next_url') or url_for('project_detail', project_id=project.id)

    if 'file' not in request.files:
        flash('No file selected for upload.', 'danger')
        return redirect(next_url)

    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(next_url)

    title = request.form.get('title', '').strip()
    deliverable_type = request.form.get('deliverable_type', 'Other')
    version = request.form.get('version', 'v1.0').strip() or 'v1.0'
    notes = request.form.get('notes', '').strip()

    if not title:
        title = file.filename.rsplit('.', 1)[0]

    if file and allowed_file(file.filename):
        original_name = secure_filename(file.filename)
        # Prepend timestamp and project id to guarantee unique filenames
        timestamp_prefix = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        clean_filename = f"{project.id}_{timestamp_prefix}_{original_name}"
        
        target_dir = UPLOAD_FOLDERS.get(deliverable_type, UPLOAD_FOLDERS['Other'])
        os.makedirs(target_dir, exist_ok=True)
        file_save_path = os.path.join(target_dir, clean_filename)
        
        file.save(file_save_path)
        file_size = os.path.getsize(file_save_path)
        sha256_hash = ADBMSManager.calculate_file_sha256(file_save_path)

        # Store relative web path starting from /static/uploads/...
        relative_folder = os.path.basename(target_dir)
        db_file_path = f"/static/uploads/{relative_folder}/{clean_filename}"

        deliverable = ProjectDeliverable(
            project_id=project.id,
            title=title,
            deliverable_type=deliverable_type,
            file_path=db_file_path,
            file_size=file_size,
            file_hash_sha256=sha256_hash,
            version=version,
            notes=notes,
            uploaded_at=datetime.utcnow()
        )
        db.session.add(deliverable)
        project.updated_at = datetime.utcnow()

        log_history(
            project.id, 
            'File Uploaded', 
            f"Attached {deliverable_type}: '{title}' ({version}, {deliverable.human_file_size})"
        )
        db.session.commit()

        flash(f"Document '{title}' ({deliverable_type}) uploaded successfully!", 'success')
    else:
        flash('Invalid file extension. Please upload accepted document, presentation, diagram, or archive formats.', 'danger')

    return redirect(next_url)

@app.route('/deliverable/<int:deliverable_id>/download')
def deliverable_download(deliverable_id):
    deliverable = ProjectDeliverable.query.get_or_404(deliverable_id)
    if os.path.isabs(deliverable.file_path) and os.path.exists(deliverable.file_path):
        system_path = deliverable.file_path
    else:
        rel_path = deliverable.file_path.lstrip('/')
        system_path = os.path.join(app.root_path, rel_path)

    if not os.path.exists(system_path):
        flash('The requested file does not exist on the server storage.', 'danger')
        return redirect(url_for('project_detail', project_id=deliverable.project_id))

    filename = os.path.basename(system_path)
    return send_file(system_path, as_attachment=True, download_name=f"{secure_filename(deliverable.title)}_{filename}")

@app.route('/deliverable/<int:deliverable_id>/view')
def deliverable_view(deliverable_id):
    deliverable = ProjectDeliverable.query.get_or_404(deliverable_id)
    if os.path.isabs(deliverable.file_path) and os.path.exists(deliverable.file_path):
        system_path = deliverable.file_path
    else:
        rel_path = deliverable.file_path.lstrip('/')
        system_path = os.path.join(app.root_path, rel_path)

    if not os.path.exists(system_path):
        flash('File not found.', 'danger')
        return redirect(url_for('project_detail', project_id=deliverable.project_id))

    return send_file(system_path, as_attachment=False)

@app.route('/deliverable/<int:deliverable_id>/delete', methods=['POST'])
def deliverable_delete(deliverable_id):
    deliverable = ProjectDeliverable.query.get_or_404(deliverable_id)
    project_id = deliverable.project_id
    title = deliverable.title
    dtype = deliverable.deliverable_type

    # Delete physical file
    rel_path = deliverable.file_path.lstrip('/')
    system_path = os.path.join(app.root_path, rel_path)
    if os.path.exists(system_path):
        try:
            os.remove(system_path)
        except Exception as e:
            app.logger.warning(f"Could not remove physical file {system_path}: {e}")

    db.session.delete(deliverable)
    log_history(project_id, 'File Deleted', f"Deleted deliverable: '{title}' ({dtype}).")
    db.session.commit()

    flash(f"Deliverable '{title}' was deleted successfully.", 'info')
    return redirect(url_for('project_detail', project_id=project_id))


# --- 7. Interactive Tasks & Milestones Routes (With Dynamic Recalculation) ---

@app.route('/project/<int:project_id>/tasks/add', methods=['POST'])
def task_add(project_id):
    project = Project.query.get_or_404(project_id)
    task_name = request.form.get('task_name', '').strip()
    priority = request.form.get('priority', 'Medium')
    due_date_str = request.form.get('due_date', '').strip()

    if task_name:
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
        task = ProjectTask(
            project_id=project.id,
            task_name=task_name,
            priority=priority,
            due_date=due_date,
            is_completed=False
        )
        db.session.add(task)
        db.session.flush()

        # Recalculate progress
        project.recalculate_progress()
        project.updated_at = datetime.utcnow()
        log_history(project.id, 'Task Added', f"Added task: '{task_name}' [{priority} priority]")
        db.session.commit()

        flash('New milestone task added!', 'success')
    else:
        flash('Task description cannot be blank.', 'danger')

    return redirect(url_for('project_detail', project_id=project.id, tab='tasks'))

@app.route('/task/<int:task_id>/toggle', methods=['POST'])
def task_toggle(task_id):
    task = ProjectTask.query.get_or_404(task_id)
    project = task.project

    task.is_completed = not task.is_completed
    db.session.flush()

    # Recalculate progress
    new_progress = project.recalculate_progress()
    project.updated_at = datetime.utcnow()

    status_label = "completed" if task.is_completed else "marked pending"
    log_history(project.id, 'Task Toggled', f"Task '{task.task_name}' {status_label}. Progress: {new_progress}%.")
    db.session.commit()

    # Supports both AJAX JSON response and standard form post
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'task_id': task.id,
            'is_completed': task.is_completed,
            'progress_percentage': new_progress,
            'task_stats': project.task_stats
        })

    return redirect(url_for('project_detail', project_id=project.id, tab='tasks'))

@app.route('/task/<int:task_id>/delete', methods=['POST'])
def task_delete(task_id):
    task = ProjectTask.query.get_or_404(task_id)
    project = task.project
    name = task.task_name

    db.session.delete(task)
    db.session.flush()

    new_progress = project.recalculate_progress()
    project.updated_at = datetime.utcnow()
    log_history(project.id, 'Task Deleted', f"Removed task: '{name}'.")
    db.session.commit()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'progress_percentage': new_progress,
            'task_stats': project.task_stats
        })

    flash('Task removed.', 'info')
    return redirect(url_for('project_detail', project_id=project.id, tab='tasks'))


# --- 8. Development Notes Routes ---

@app.route('/project/<int:project_id>/notes/add', methods=['POST'])
def note_add(project_id):
    project = Project.query.get_or_404(project_id)
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    note_type = request.form.get('note_type', 'Dev Log')

    if title and content:
        note = ProjectNote(
            project_id=project.id,
            title=title,
            content=content,
            note_type=note_type,
            created_at=datetime.utcnow()
        )
        db.session.add(note)
        project.updated_at = datetime.utcnow()

        log_history(project.id, 'Note Added', f"Recorded {note_type}: '{title}'")
        db.session.commit()

        flash('Developer note saved.', 'success')
    else:
        flash('Title and note content are required.', 'danger')

    return redirect(url_for('project_detail', project_id=project.id, tab='notes'))

@app.route('/note/<int:note_id>/delete', methods=['POST'])
def note_delete(note_id):
    note = ProjectNote.query.get_or_404(note_id)
    project_id = note.project_id
    title = note.title

    db.session.delete(note)
    log_history(project_id, 'Note Deleted', f"Deleted note: '{title}'")
    db.session.commit()

    flash('Note deleted.', 'info')
    return redirect(url_for('project_detail', project_id=project_id, tab='notes'))


# --- 9. Technology Management Routes ---

@app.route('/technologies', methods=['GET', 'POST'])
def technologies_manager():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'Tool')
        icon_class = request.form.get('icon_class', 'bi bi-code-slash').strip() or 'bi bi-code-slash'
        badge_color = request.form.get('badge_color', '#0d6efd').strip() or '#0d6efd'

        if name:
            existing = Technology.query.filter_by(name=name).first()
            if existing:
                flash(f"Technology '{name}' already exists.", 'warning')
            else:
                tech = Technology(
                    name=name,
                    category=category,
                    icon_class=icon_class,
                    badge_color=badge_color
                )
                db.session.add(tech)
                db.session.commit()
                flash(f"Technology '{name}' registered successfully!", 'success')
        else:
            flash('Technology name cannot be blank.', 'danger')

        return redirect(url_for('technologies_manager'))

    return redirect(url_for('projects_list'))

@app.route('/technologies/<int:tech_id>/delete', methods=['POST'])
def technology_delete(tech_id):
    tech = Technology.query.get_or_404(tech_id)
    name = tech.name
    db.session.delete(tech)
    db.session.commit()
    flash(f"Technology '{name}' removed.", 'info')
    return redirect(url_for('projects_list'))


# --- 10. Printable Academic Synopsis / Report Generator ---

@app.route('/project/<int:project_id>/printable-report')
@app.route('/project/<int:project_id>/synopsis')
def printable_report(project_id):
    return redirect(url_for('project_detail', project_id=project_id))


# --- 11. Data Management: Export & Import Hub ---

@app.route('/export')
def export_hub():
    projects = Project.query.order_by(Project.title).all()
    svc = LocalProjectsService()
    local_scan = svc.scan_directory()
    root_dir = svc.get_projects_directory()
    return render_template(
        'export.html',
        projects=projects,
        local_scan=local_scan,
        root_dir=root_dir
    )

@app.route('/project/<int:project_id>/export/json')
def export_single_json(project_id):
    project = Project.query.get_or_404(project_id)
    data = project.to_dict()
    data['documentation'] = project.document.to_dict() if project.document else {}
    data['deliverables'] = [d.to_dict() for d in project.deliverables]
    data['tasks'] = [t.to_dict() for t in project.tasks]
    data['notes'] = [n.to_dict() for n in project.notes]
    data['history'] = [h.to_dict() for h in project.history]

    buffer = io.BytesIO(json.dumps(data, indent=2).encode('utf-8'))
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"devvault_{project.slug}.json",
        mimetype='application/json'
    )

@app.route('/project/<int:project_id>/export/csv')
def export_single_csv(project_id):
    project = Project.query.get_or_404(project_id)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Field", "Value"])
    writer.writerow(["Title", project.title])
    writer.writerow(["Category", project.category.name if project.category else "None"])
    writer.writerow(["Status", project.status])
    writer.writerow(["Progress", f"{project.progress_percentage}%"])
    writer.writerow(["GitHub URL", project.github_url or ""])
    writer.writerow(["Live URL", project.live_url or ""])
    writer.writerow(["Start Date", project.start_date.isoformat() if project.start_date else ""])
    writer.writerow(["End Date", project.end_date.isoformat() if project.end_date else ""])
    writer.writerow(["Technologies", ", ".join([t.name for t in project.technologies])])
    writer.writerow([])
    writer.writerow(["Tasks Checklist"])
    writer.writerow(["Task Name", "Priority", "Status", "Due Date"])
    for t in project.tasks:
        writer.writerow([t.task_name, t.priority, "Completed" if t.is_completed else "Pending", t.due_date or ""])
    writer.writerow([])
    writer.writerow(["Academic Deliverables"])
    writer.writerow(["Title", "Type", "Version", "Size", "File Path"])
    for d in project.deliverables:
        writer.writerow([d.title, d.deliverable_type, d.version, d.human_file_size, d.file_path])

    buffer = io.BytesIO(output.getvalue().encode('utf-8'))
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"devvault_{project.slug}.csv",
        mimetype='text/csv'
    )

@app.route('/export/all/json')
@app.route('/export/json', endpoint='export_projects_json')
def export_all_json():
    projects = Project.query.all()
    all_data = []
    for project in projects:
        p_dict = project.to_dict()
        p_dict['documentation'] = project.document.to_dict() if project.document else {}
        p_dict['deliverables'] = [d.to_dict() for d in project.deliverables]
        p_dict['tasks'] = [t.to_dict() for t in project.tasks]
        p_dict['notes'] = [n.to_dict() for n in project.notes]
        p_dict['history'] = [h.to_dict() for h in project.history]
        all_data.append(p_dict)

    buffer = io.BytesIO(json.dumps(all_data, indent=2).encode('utf-8'))
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"devvault_full_export_{datetime.utcnow().strftime('%Y%m%d')}.json",
        mimetype='application/json'
    )

@app.route('/export/all/csv')
@app.route('/export/csv', endpoint='export_projects_csv')
def export_all_csv():
    projects = Project.query.all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID", "Title", "Category", "Status", "Progress %", 
        "Technologies", "Tasks Total", "Tasks Done", 
        "Deliverables Total", "Has Report", "Has PPT", "Has Synopsis", "Has Code ZIP",
        "Created At", "Updated At"
    ])

    for p in projects:
        writer.writerow([
            p.id,
            p.title,
            p.category.name if p.category else "",
            p.status,
            p.progress_percentage,
            ", ".join([t.name for t in p.technologies]),
            len(p.tasks),
            sum(1 for t in p.tasks if t.is_completed),
            len(p.deliverables),
            "Yes" if p.checklist_status['has_report'] else "No",
            "Yes" if p.checklist_status['has_ppt'] else "No",
            "Yes" if p.checklist_status['has_synopsis'] else "No",
            "Yes" if p.checklist_status['has_source_code'] else "No",
            p.created_at.strftime('%Y-%m-%d %H:%M') if p.created_at else "",
            p.updated_at.strftime('%Y-%m-%d %H:%M') if p.updated_at else ""
        ])

    buffer = io.BytesIO(output.getvalue().encode('utf-8'))
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"devvault_projects_summary_{datetime.utcnow().strftime('%Y%m%d')}.csv",
        mimetype='text/csv'
    )

@app.route('/export/database/backup')
@app.route('/export/multi-db-backup')
def export_database_backup():
    memory_zip = io.BytesIO()
    with zipfile.ZipFile(memory_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        db_names = ['devvault_core.db', 'devvault_vault.db', 'devvault_audit.db']
        found = 0
        for db_name in db_names:
            db_path = os.path.join(app.root_path, db_name)
            if os.path.exists(db_path):
                zf.write(db_path, arcname=db_name)
                found += 1
            else:
                inst_path = os.path.join(app.root_path, 'instance', db_name)
                if os.path.exists(inst_path):
                    zf.write(inst_path, arcname=db_name)
                    found += 1
        if found == 0:
            flash('No SQLite database files found to back up.', 'danger')
            return redirect(url_for('export_hub'))

    memory_zip.seek(0)
    return send_file(
        memory_zip,
        as_attachment=True,
        download_name=f"devvault_multi_db_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip",
        mimetype='application/zip'
    )

@app.route('/export/full/zip')
def export_full_backup_zip():
    memory_zip = io.BytesIO()
    with zipfile.ZipFile(memory_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Add all 3 SQLite databases
        db_names = ['devvault_core.db', 'devvault_vault.db', 'devvault_audit.db']
        for db_name in db_names:
            db_path = os.path.join(app.root_path, db_name)
            if os.path.exists(db_path):
                zf.write(db_path, arcname=f"databases/{db_name}")
            else:
                inst_path = os.path.join(app.root_path, 'instance', db_name)
                if os.path.exists(inst_path):
                    zf.write(inst_path, arcname=f"databases/{db_name}")

        # 2. Add uploaded deliverables
        for root, dirs, files in os.walk(UPLOAD_BASE):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, app.root_path)
                zf.write(full_path, arcname=rel_path)

    memory_zip.seek(0)
    return send_file(
        memory_zip,
        as_attachment=True,
        download_name=f"devvault_full_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip",
        mimetype='application/zip'
    )


# --- 11B. Local Projects Vault & Filesystem Scanner (E:\COMPLETE PROJECT) ---

@app.route('/local-projects')
def local_projects_hub():
    return redirect(url_for('export_hub'))

@app.route('/local-projects/import', methods=['POST'])
def local_projects_import_single():
    next_url = request.form.get('next_url') or url_for('export_hub')
    folder_name = request.form.get('folder_name', '').strip()
    if not folder_name:
        flash('Folder name is required.', 'danger')
        return redirect(next_url)

    svc = LocalProjectsService()
    res = svc.import_project(folder_name)
    if res['success']:
        flash(f"Successfully imported '{res['title']}' with {res['deliverables_count']} deliverable attachments!", 'success')
        return redirect(url_for('project_detail', project_id=res['project_id']))
    else:
        flash(f"Error importing project: {res.get('error')}", 'danger')
        return redirect(next_url)

@app.route('/local-projects/import-all', methods=['POST'])
def local_projects_import_all():
    next_url = request.form.get('next_url') or url_for('export_hub')
    svc = LocalProjectsService()
    res = svc.import_all()
    if res['success']:
        flash(f"Batch import completed! Imported {res['imported_count']} new projects from local projects vault.", 'success')
    else:
        flash(f"Error during batch import: {res.get('error')}", 'danger')
    return redirect(next_url)

@app.route('/local-projects/configure', methods=['POST'])
def local_projects_configure():
    next_url = request.form.get('next_url') or url_for('export_hub')
    new_dir = request.form.get('local_projects_dir', '').strip()
    if new_dir:
        SystemSetting.set('local_projects_dir', new_dir)
        flash(f"Local projects directory updated to: {new_dir}", 'success')
    return redirect(next_url)


# --- 12. GitHub Integration Hub & Repositories Sync ---

@app.route('/github')
def github_hub():
    gh_username = SystemSetting.get('github_username', '')
    gh_token = SystemSetting.get('github_token', '')
    
    profile_data = None
    repos_data = []
    error_msg = None

    if gh_username:
        gh = GitHubService(token=gh_token)
        prof_res = gh.get_user_profile(gh_username)
        if prof_res['success']:
            profile_data = prof_res['data']
        else:
            # Graceful fallback to stored settings when offline
            profile_data = {
                'username': gh_username,
                'name': SystemSetting.get('github_name', 'Anurag Jha'),
                'avatar_url': SystemSetting.get('github_avatar_url', f"https://github.com/{gh_username}.png"),
                'bio': SystemSetting.get('github_bio', 'Full-Stack Developer, AI Researcher & ADBMS Architect | GitHub: @AnuragJha100706'),
                'html_url': f"https://github.com/{gh_username}",
                'public_repos': 16,
                'followers': 0,
                'following': 0
            }

        repo_res = gh.get_user_repositories(gh_username)
        if repo_res['success']:
            repos_data = repo_res['repos']
        elif not error_msg:
            error_msg = repo_res.get('error')

    # Get set of all currently linked repo URLs / slugs in DevVault
    existing_projects = Project.query.all()
    linked_slugs = {p.github_repo_slug.lower() for p in existing_projects if p.github_repo_slug}
    linked_project_map = {p.github_repo_slug.lower(): p for p in existing_projects if p.github_repo_slug}

    return render_template(
        'github.html',
        gh_username=gh_username,
        profile=profile_data,
        repos=repos_data,
        linked_slugs=linked_slugs,
        linked_project_map=linked_project_map,
        error_msg=error_msg
    )

@app.route('/github/connect', methods=['POST'])
def github_connect():
    username = request.form.get('username', '').strip()
    token = request.form.get('token', '').strip()

    if not username:
        flash('GitHub username cannot be empty.', 'danger')
        return redirect(url_for('github_hub'))

    gh = GitHubService(token=token if token else None)
    res = gh.get_user_profile(username)

    if res['success']:
        data = res['data']
        SystemSetting.set('github_username', data['username'])
        SystemSetting.set('github_name', data['name'])
        SystemSetting.set('github_avatar_url', data['avatar_url'])
        SystemSetting.set('github_bio', data['bio'])
        if token:
            SystemSetting.set('github_token', token)
        flash(f"Successfully connected to GitHub account @{data['username']}!", 'success')
    else:
        # Save username anyway so user can set it up even if offline
        SystemSetting.set('github_username', username)
        SystemSetting.set('github_name', username)
        if token:
            SystemSetting.set('github_token', token)
        flash(f"GitHub account @{username} registered. Note: {res.get('error')}", 'info')

    return redirect(url_for('github_hub'))

@app.route('/github/disconnect', methods=['POST'])
def github_disconnect():
    SystemSetting.set('github_username', '')
    SystemSetting.set('github_name', '')
    SystemSetting.set('github_avatar_url', '')
    SystemSetting.set('github_bio', '')
    SystemSetting.set('github_token', '')
    flash('GitHub account disconnected.', 'info')
    return redirect(url_for('github_hub'))

@app.route('/github/import', methods=['POST'])
def github_import():
    full_name = request.form.get('full_name', '').strip()  # e.g. "octocat/Hello-World"
    if not full_name:
        flash('Repository name is required for import.', 'danger')
        return redirect(url_for('github_hub'))

    owner, repo = GitHubService.parse_repo_url(full_name)
    if not owner or not repo:
        flash('Invalid repository format. Expected "owner/repo".', 'danger')
        return redirect(url_for('github_hub'))

    # Check if already imported
    existing = Project.query.filter(Project.github_url.ilike(f"%{owner}/{repo}%")).first()
    if existing:
        flash(f"Repository '{owner}/{repo}' is already imported in DevVault!", 'warning')
        return redirect(url_for('project_detail', project_id=existing.id))

    gh_token = SystemSetting.get('github_token')
    gh = GitHubService(token=gh_token)

    # Fetch repo details from GitHub
    repo_res = gh.get_repo_details(owner, repo)
    repo_data = repo_res.get('data', {}) if repo_res['success'] else {}

    clean_title = repo.replace('-', ' ').replace('_', ' ').title()
    short_desc = repo_data.get('description') or f"Imported from GitHub repository {owner}/{repo}."
    slug = generate_slug(clean_title)

    category = ProjectCategory.query.filter_by(name='Web Development').first()
    if not category:
        category = ProjectCategory.query.first()

    project = Project(
        title=clean_title,
        slug=slug,
        short_description=short_desc,
        category_id=category.id if category else None,
        status="In Progress",
        progress_percentage=0,
        github_url=f"https://github.com/{owner}/{repo}",
        github_stars=repo_data.get('stars', 0),
        github_forks=repo_data.get('forks', 0),
        github_open_issues=repo_data.get('open_issues', 0),
        github_default_branch=repo_data.get('default_branch', 'main'),
        start_date=date.today(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        github_synced_at=datetime.utcnow()
    )

    primary_lang = repo_data.get('language')
    if primary_lang:
        matched_tech = Technology.query.filter(Technology.name.ilike(primary_lang)).first()
        if matched_tech:
            project.technologies.append(matched_tech)

    db.session.add(project)
    db.session.flush()

    readme_res = gh.get_repo_readme(owner, repo)
    readme_text = readme_res.get('content') if readme_res['success'] else f"# {clean_title}\n\n{short_desc}\n\nRepository: https://github.com/{owner}/{repo}"

    doc = ProjectDocument(
        project_id=project.id,
        abstract=f"Project imported from GitHub repository {owner}/{repo}.",
        problem_statement="",
        objectives="",
        system_requirements="",
        architecture_notes="",
        readme_content=readme_text
    )
    db.session.add(doc)

    log_history(project.id, 'Created', f"Imported project directly from GitHub repository '{owner}/{repo}'.")
    db.session.commit()

    flash(f"Successfully imported '{owner}/{repo}' into DevVault!", 'success')
    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/project/<int:project_id>/github/sync', methods=['POST'])
def project_github_sync(project_id):
    project = Project.query.get_or_404(project_id)
    if not project.github_url:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'No GitHub repository URL configured.'}), 400
        flash('No GitHub repository URL configured for this project.', 'warning')
        return redirect(url_for('project_detail', project_id=project.id))

    owner, repo = GitHubService.parse_repo_url(project.github_url)
    if not owner or not repo:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Invalid GitHub repository URL format.'}), 400
        flash('Invalid GitHub repository URL.', 'danger')
        return redirect(url_for('project_detail', project_id=project.id))

    gh_token = SystemSetting.get('github_token')
    gh = GitHubService(token=gh_token)

    repo_res = gh.get_repo_details(owner, repo)
    commits_res = gh.get_recent_commits(owner, repo, limit=5)

    if repo_res['success']:
        d = repo_res['data']
        project.github_stars = d['stars']
        project.github_forks = d['forks']
        project.github_open_issues = d['open_issues']
        project.github_default_branch = d['default_branch']
        project.github_synced_at = datetime.utcnow()

    latest_commit = None
    if commits_res['success'] and commits_res['commits']:
        c0 = commits_res['commits'][0]
        project.github_latest_commit_sha = c0['short_sha']
        project.github_latest_commit_msg = c0['message']
        project.github_latest_commit_author = c0['author_name']
        latest_commit = c0

    log_history(project.id, 'Status Updated', f"Synced live GitHub repository stats ({project.github_stars} stars, {project.github_forks} forks).")
    db.session.commit()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'stars': project.github_stars,
            'forks': project.github_forks,
            'open_issues': project.github_open_issues,
            'branch': project.github_default_branch,
            'latest_commit': latest_commit,
            'commits': commits_res.get('commits', []),
            'synced_at': project.github_synced_at.strftime('%b %d, %H:%M') if project.github_synced_at else 'Just now'
        })

    flash(f"Live GitHub data synchronized for {owner}/{repo}!", 'success')
    return redirect(url_for('project_detail', project_id=project.id))

@app.route('/project/<int:project_id>/github/pull-readme', methods=['POST'])
def project_github_pull_readme(project_id):
    project = Project.query.get_or_404(project_id)
    owner, repo = GitHubService.parse_repo_url(project.github_url)
    if not owner or not repo:
        flash('Invalid GitHub repository URL.', 'danger')
        return redirect(url_for('project_detail', project_id=project.id, tab='docs'))

    gh_token = SystemSetting.get('github_token')
    gh = GitHubService(token=gh_token)
    res = gh.get_repo_readme(owner, repo)

    if res['success']:
        if not project.document:
            project.document = ProjectDocument(project_id=project.id)
        project.document.readme_content = res['content']
        log_history(project.id, 'Doc Edited', f"Imported latest README.md from GitHub ({owner}/{repo}).")
        db.session.commit()
        flash('Successfully pulled latest README.md from GitHub!', 'success')
    else:
        flash(f"Could not pull README from GitHub: {res.get('error')}", 'warning')

    return redirect(url_for('project_detail', project_id=project.id, tab='docs'))


# --- 13. ADBMS Database Studio & Query Optimizer Routes ---

@app.route('/database-studio')
def database_studio():
    return redirect(url_for('export_hub'))

@app.route('/database-studio/query', methods=['POST'])
def database_studio_query():
    target_db = request.form.get('target_db', 'federated').strip().lower()
    sql_query = request.form.get('sql_query', '').strip()

    if not sql_query:
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'Query cannot be empty.'}), 400
        flash('SQL query cannot be empty.', 'danger')
        return redirect(url_for('database_studio'))

    result = adbms_manager.execute_query(sql_query, target_db=target_db)

    # If it was an action query (INSERT/UPDATE/DELETE/CREATE/DROP/ALTER) and succeeded, log it in DatabaseChangeLog
    first_word = sql_query.split()[0].upper() if sql_query.split() else ''
    if result['success'] and first_word in ('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'ATTACH'):
        try:
            log_entry = DatabaseChangeLog(
                target_database=target_db,
                operation=first_word,
                table_name='studio_query',
                details=sql_query[:500]
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception:
            db.session.rollback()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(result)

    if not result['success']:
        flash(f"SQL Error: {result.get('error')}", 'danger')
    else:
        flash(f"Query executed in {result.get('latency_ms')} ms ({result.get('affected_count')} rows)", 'success')

    return redirect(url_for('database_studio'))

@app.route('/database-studio/pragma', methods=['POST'])
def database_studio_pragma():
    target_db = request.form.get('target_db', 'core').strip().lower()
    pragma_name = request.form.get('pragma_name', 'integrity_check').strip().lower()

    allowed_pragmas = {
        'integrity_check': 'PRAGMA integrity_check;',
        'foreign_key_check': 'PRAGMA foreign_key_check;',
        'journal_mode': 'PRAGMA journal_mode;',
        'freelist_count': 'PRAGMA freelist_count;',
        'page_count': 'PRAGMA page_count;',
        'page_size': 'PRAGMA page_size;',
        'wal_checkpoint': 'PRAGMA wal_checkpoint(PASSIVE);'
    }

    if pragma_name not in allowed_pragmas:
        return jsonify({'success': False, 'error': f'Unsupported PRAGMA: {pragma_name}'}), 400

    query = allowed_pragmas[pragma_name]
    result = adbms_manager.execute_query(query, target_db=target_db)
    return jsonify(result)


# --- Error Handlers ---

@app.errorhandler(404)
def page_not_found(e):
    flash('Requested page not found. Redirected to Dashboard.', 'info')
    return redirect(url_for('dashboard'))

@app.errorhandler(500)
def internal_server_error(e):
    flash('An internal server error occurred.', 'danger')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        adbms_manager.setup_advanced_triggers_and_views()
    app.run(debug=True, host='127.0.0.1', port=5000)

