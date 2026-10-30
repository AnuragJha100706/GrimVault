r"""
End-to-End Verification Test for DevVault 4-Page UI Rework
Author: Anurag Jha (@AnuragJha100706)
"""
import io
from app import app, db
from models import Project, ProjectDeliverable, ProjectCategory, Technology

def run_tests():
    print("=" * 60)
    print("STARTING DEVVAULT 4-PAGE UI REWORK VERIFICATION")
    print("=" * 60)

    client = app.test_client()

    # 1. Test Dashboard Page
    print("\n[TEST 1] Testing Page 1: Dashboard ('/' and '/dashboard')...")
    res1 = client.get('/')
    assert res1.status_code == 200, f"Dashboard '/' failed with status {res1.status_code}"
    res2 = client.get('/dashboard')
    assert res2.status_code == 200, f"Dashboard '/dashboard' failed with status {res2.status_code}"
    html = res2.get_data(as_text=True)
    assert "Project Vault Overview" in html
    assert "@AnuragJha100706" in html
    assert "E:\\COMPLETE PROJECT" in html
    print("  -> Dashboard loaded successfully with metrics and charts.")

    # 2. Test Projects Repository Page
    print("\n[TEST 2] Testing Page 2: Projects Repository ('/projects')...")
    res_proj = client.get('/projects')
    assert res_proj.status_code == 200, f"Projects list failed with status {res_proj.status_code}"
    html_proj = res_proj.get_data(as_text=True)
    assert "Projects Repository" in html_proj
    assert "New Project" in html_proj
    assert "The Velvet Fork" in html_proj or "VibeNest AI" in html_proj
    print("  -> Projects repository grid/table loaded successfully.")

    # 3. Test Single Project View
    with app.app_context():
        p = Project.query.first()
        assert p is not None, "No project found in database!"
        p_id = p.id
        p_title = p.title

    print(f"\n[TEST 3] Testing Project Detail View for Project ID {p_id} ('{p_title}')...")
    res_detail = client.get(f'/project/{p_id}')
    assert res_detail.status_code == 200, f"Project detail failed with status {res_detail.status_code}"
    html_detail = res_detail.get_data(as_text=True)
    
    # Verify core requirements:
    # a. Location in system
    assert "Location in System" in html_detail
    assert "Copy Path" in html_detail
    # b. GitHub repo & Live link
    assert "GitHub Repository Link" in html_detail
    assert "Live Project URL" in html_detail
    # c. Option to add project report file and PPT
    assert "Project Reports, PPTs & Documents" in html_detail
    assert "Add / Upload Project Report, PPT or Document" in html_detail
    # d. Option for user to edit info about this project
    assert "Edit Project Information" in html_detail
    # e. Ensure old bloated tabs are REMOVED
    assert 'id="tab-tasks"' not in html_detail
    assert 'id="tab-notes"' not in html_detail
    assert 'id="tab-history"' not in html_detail
    print("  -> Project detail verified: shows location, repo/live link, report/PPT uploader & edit info!")

    # 4. Test Uploading a Document to the Project
    print(f"\n[TEST 4] Testing Document Upload to Project ID {p_id}...")
    sample_file = (io.BytesIO(b"%PDF-1.4 sample project report content"), "Test_Project_Report.pdf")
    upload_res = client.post(
        f'/project/{p_id}/upload-document',
        data={
            'title': 'Test Report v1.0',
            'deliverable_type': 'Project Report',
            'version': 'v1.0',
            'notes': 'Uploaded via automated verification test',
            'file': sample_file
        },
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert upload_res.status_code == 200
    upload_html = upload_res.get_data(as_text=True)
    assert "Test Report v1.0" in upload_html
    print("  -> Document upload succeeded and appears in project deliverables list.")

    # 5. Test Editing Project Information
    print(f"\n[TEST 5] Testing Editing Project Info for Project ID {p_id}...")
    edit_res = client.post(
        f'/project/{p_id}/edit-info',
        data={
            'title': f"{p_title} (Verified Edition)",
            'category_id': p.category_id,
            'status': 'Completed',
            'local_path': r"E:\COMPLETE PROJECT\test_verified_location",
            'github_url': "https://github.com/AnuragJha100706/DevVault",
            'live_url': "https://devvault-preview.vercel.app",
            'short_description': "Updated description with system location and links."
        },
        follow_redirects=True
    )
    assert edit_res.status_code == 200
    edit_html = edit_res.get_data(as_text=True)
    assert "Verified Edition" in edit_html
    assert "test_verified_location" in edit_html
    assert "https://github.com/AnuragJha100706/DevVault" in edit_html
    print("  -> Project edit succeeded: updated title, local path, repo & live links.")

    # 6. Test Page 3: GitHub Profile Preview
    print("\n[TEST 6] Testing Page 3: GitHub Profile Preview ('/github')...")
    res_gh = client.get('/github')
    assert res_gh.status_code == 200, f"GitHub hub failed with status {res_gh.status_code}"
    html_gh = res_gh.get_data(as_text=True)
    assert "GitHub" in html_gh
    assert "AnuragJha100706" in html_gh
    print("  -> GitHub profile preview page loaded successfully.")

    # 7. Test Page 4: Export & Import Hub
    print("\n[TEST 7] Testing Page 4: Export & Import Hub ('/export')...")
    res_exp = client.get('/export')
    assert res_exp.status_code == 200, f"Export hub failed with status {res_exp.status_code}"
    html_exp = res_exp.get_data(as_text=True)
    assert "Export & Import Hub" in html_exp
    assert "Multi-DB" in html_exp
    assert "Import Projects" in html_exp
    assert "E:\\COMPLETE PROJECT" in html_exp
    print("  -> Export & Import hub loaded successfully with local scanning and multi-DB options.")

    # 8. Test Multi-DB Backup Export Endpoint
    print("\n[TEST 8] Testing Multi-DB Backup Export ('/export/multi-db-backup')...")
    res_backup = client.get('/export/multi-db-backup')
    assert res_backup.status_code == 200
    assert res_backup.content_type == 'application/zip'
    assert len(res_backup.data) > 0
    print(f"  -> Multi-DB zip downloaded successfully ({len(res_backup.data)} bytes).")

    # 9. Test JSON Export
    print("\n[TEST 9] Testing Database JSON Export ('/export/json')...")
    res_json = client.get('/export/json')
    assert res_json.status_code == 200
    assert res_json.content_type.startswith('application/json')
    print("  -> JSON export succeeded.")

    print("\n" + "=" * 60)
    print("ALL 9 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
