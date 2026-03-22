"""
IP Management Tool - Web Edition (Flask)
==========================================
Accessible locally and across LAN: http://localhost:5000
Requires login — default credentials: admin / admin123
"""

import csv
import json
import os
import socket
import tempfile
from datetime import datetime
from functools import wraps
from io import BytesIO, StringIO

from flask import (Flask, jsonify, redirect, render_template,
                   request, send_file, session, url_for)
from flask_cors import CORS

from modules import (
    add_record,
    cleanup_old_backups,
    create_backup,
    detect_import_conflicts,
    get_deleted_records,
    get_summary,
    import_csv,
    import_json,
    load_records,
    log_error,
    log_info,
    save_deleted_record,
    save_records,
    search_records,
    sort_records,
    VALID_STATUSES,
    update_record,
)
from modules.auth import (
    authenticate,
    change_password,
    create_user,
    delete_user,
    ensure_default_admin,
    get_user_role,
    list_users,
)
from modules.backup import clear_deleted_records, DELETED_FILE

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())
CORS(app)

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "data", "settings.json")


# ── AUTH HELPERS ───────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Not authenticated"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "username" not in session:
            return jsonify({"success": False, "error": "Not authenticated"}), 401
        if get_user_role(session["username"]) != "admin":
            return jsonify({"success": False, "error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


# ── AUTH ROUTES ────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET"])
def login_page():
    if "username" in session:
        return redirect(url_for("index"))
    error = request.args.get("error", "")
    return render_template("login.html", error=error)


@app.route("/login", methods=["POST"])
def login_post():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if authenticate(username, password):
        session["username"] = username
        session["role"]     = get_user_role(username)
        log_info(f"Login: {username}")
        return redirect(url_for("index"))
    return redirect(url_for("login_page", error="Invalid username or password"))


@app.route("/logout")
def logout():
    username = session.pop("username", "unknown")
    session.clear()
    log_info(f"Logout: {username}")
    return redirect(url_for("login_page"))


# ── HOME ──────────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html",
                           username=session.get("username"),
                           role=session.get("role"))


# ── RECORDS ───────────────────────────────────────────────────────────────────

@app.route("/api/records", methods=["GET"])
@login_required
def api_get_records():
    records = load_records()
    q      = request.args.get("q", "")
    status = request.args.get("status", "All")
    sort   = request.args.get("sort", "ip")
    rev    = request.args.get("rev", "false").lower() == "true"

    results = search_records(records, q)
    if status != "All":
        results = [r for r in results if r.get("status") == status]
    results = sort_records(results, sort, rev)

    return jsonify({
        "success": True,
        "data":    results,
        "summary": get_summary(records),
        "total":   len(records),
        "shown":   len(results),
    })


@app.route("/api/records", methods=["POST"])
@admin_required
def api_add_record():
    d = request.json or {}
    records = load_records()
    _, err = add_record(
        records,
        d.get("ip", ""),
        d.get("subnet", "24"),
        d.get("hostname", ""),
        d.get("description", ""),
        d.get("status", "Active"),
    )
    if err:
        return jsonify({"success": False, "error": err}), 400
    log_info(f"Added record: {d.get('ip')} (by {session.get('username')})")
    return jsonify({"success": True})


@app.route("/api/records/<int:index>", methods=["PUT"])
@admin_required
def api_update_record(index):
    d = request.json or {}
    records = load_records()
    _, err = update_record(
        records, index,
        d.get("ip", ""),
        d.get("subnet", "24"),
        d.get("hostname", ""),
        d.get("description", ""),
        d.get("status", "Active"),
    )
    if err:
        return jsonify({"success": False, "error": err}), 400
    log_info(f"Updated record {index} (by {session.get('username')})")
    return jsonify({"success": True})


@app.route("/api/records/delete", methods=["POST"])
@admin_required
def api_delete_records():
    indices = (request.json or {}).get("indices", [])
    records = load_records()
    valid   = {i for i in indices if 0 <= i < len(records)}
    for i in valid:
        save_deleted_record(records[i])
    save_records([r for j, r in enumerate(records) if j not in valid])
    log_info(f"Deleted {len(valid)} record(s) (by {session.get('username')})")
    return jsonify({"success": True, "deleted": len(valid)})


# ── SUMMARY ───────────────────────────────────────────────────────────────────

@app.route("/api/summary")
@login_required
def api_summary():
    return jsonify({"success": True, "data": get_summary(load_records())})


# ── IMPORT ────────────────────────────────────────────────────────────────────

@app.route("/api/import", methods=["POST"])
@admin_required
def api_import_preview():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    f   = request.files["file"]
    ext = os.path.splitext(f.filename or "")[1].lower()

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False, mode="wb") as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        if ext == ".csv":
            new_recs, errors = import_csv(tmp_path)
        elif ext == ".json":
            new_recs, errors = import_json(tmp_path)
        else:
            return jsonify({"success": False, "error": "Use .csv or .json"}), 400

        conflicts = detect_import_conflicts(new_recs, load_records())
        return jsonify({
            "success":   True,
            "records":   new_recs,
            "errors":    errors,
            "conflicts": conflicts,
            "count":     len(new_recs),
        })
    except Exception as e:
        log_error("Import preview failed", e)
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.route("/api/import/confirm", methods=["POST"])
@admin_required
def api_import_confirm():
    d        = request.json or {}
    new_recs = d.get("records", [])
    skip     = d.get("skip_conflicts", True)

    existing = load_records()
    if skip:
        ex_ips   = {r["ip"] for r in existing}
        new_recs = [r for r in new_recs if r["ip"] not in ex_ips]

    existing.extend(new_recs)
    save_records(existing)
    log_info(f"Imported {len(new_recs)} records (by {session.get('username')})")
    return jsonify({"success": True, "imported": len(new_recs)})


# ── EXPORT ────────────────────────────────────────────────────────────────────

@app.route("/api/export")
@admin_required
def api_export():
    fmt    = request.args.get("format", "csv")
    q      = request.args.get("q", "")
    status = request.args.get("status", "All")

    records = load_records()
    results = search_records(records, q)
    if status != "All":
        results = [r for r in results if r.get("status") == status]
    clean = [{k: v for k, v in r.items() if k != "_index"} for r in results]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "json":
        buf = BytesIO(json.dumps(clean, indent=2).encode("utf-8"))
        return send_file(buf, mimetype="application/json",
                         as_attachment=True,
                         download_name=f"ip_records_{ts}.json")

    fields = ["ip", "subnet", "hostname", "description", "status", "added_on"]
    sio    = StringIO()
    writer = csv.DictWriter(sio, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(clean)
    buf = BytesIO(sio.getvalue().encode("utf-8"))
    return send_file(buf, mimetype="text/csv",
                     as_attachment=True,
                     download_name=f"ip_records_{ts}.csv")


# ── BACKUP ────────────────────────────────────────────────────────────────────

@app.route("/api/backup", methods=["POST"])
@admin_required
def api_backup():
    ok = create_backup()
    cleanup_old_backups()
    if ok:
        log_info(f"Manual backup (by {session.get('username')})")
        return jsonify({"success": True, "message": "Backup created"})
    return jsonify({"success": False, "error": "No data file to backup"}), 400


# ── DELETED RECORDS ───────────────────────────────────────────────────────────

@app.route("/api/deleted")
@login_required
def api_get_deleted():
    deleted = get_deleted_records()
    return jsonify({"success": True, "data": deleted, "count": len(deleted)})


@app.route("/api/deleted/<int:index>/recover", methods=["POST"])
@admin_required
def api_recover(index):
    deleted = get_deleted_records()
    if not (0 <= index < len(deleted)):
        return jsonify({"success": False, "error": "Invalid index"}), 400

    rec     = deleted[index]
    records = load_records()
    if any(r["ip"] == rec["ip"] for r in records):
        return jsonify({"success": False,
                        "error": f"IP {rec['ip']} already exists"}), 409

    clean = {k: v for k, v in rec.items() if k != "deleted_on"}
    records.append(clean)
    save_records(records)

    deleted.pop(index)
    if deleted:
        with open(DELETED_FILE, "w", encoding="utf-8") as f:
            json.dump(deleted, f, indent=2, ensure_ascii=False)
    else:
        clear_deleted_records()

    log_info(f"Recovered {rec['ip']} (by {session.get('username')})")
    return jsonify({"success": True})


@app.route("/api/deleted", methods=["DELETE"])
@admin_required
def api_clear_deleted():
    clear_deleted_records()
    return jsonify({"success": True})


@app.route("/api/deleted/clear", methods=["POST"])
@admin_required
def api_clear_deleted_post():
    return api_clear_deleted()


@app.route("/api/deleted/recover", methods=["POST"])
@admin_required
def api_recover_by_ip():
    ip      = (request.json or {}).get("ip", "")
    deleted = get_deleted_records()
    idx     = next((i for i, r in enumerate(deleted) if r.get("ip") == ip), None)
    if idx is None:
        return jsonify({"success": False, "error": "Record not found"}), 404
    return api_recover(idx)


# ── SETTINGS ──────────────────────────────────────────────────────────────────

@app.route("/api/settings")
@login_required
def api_get_settings():
    defaults = {
        "warn_conflicts":    True,
        "auto_backup":       True,
        "hostname_required": False,
        "valid_statuses":    sorted(VALID_STATUSES),
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                defaults.update(json.load(f))
        except Exception:
            pass
    return jsonify({"success": True, "data": defaults})


@app.route("/api/settings", methods=["PUT"])
@admin_required
def api_update_settings():
    data = request.json or {}
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return jsonify({"success": True})


# ── USER MANAGEMENT (admin only) ───────────────────────────────────────────────

@app.route("/api/users")
@admin_required
def api_list_users():
    return jsonify({"success": True, "data": list_users()})


@app.route("/api/users", methods=["POST"])
@admin_required
def api_create_user():
    d    = request.json or {}
    ok, err = create_user(d.get("username", ""), d.get("password", ""),
                          d.get("role", "user"))
    if not ok:
        return jsonify({"success": False, "error": err}), 400
    log_info(f"Created user: {d.get('username')} (by {session.get('username')})")
    return jsonify({"success": True})


@app.route("/api/users/<username>", methods=["DELETE"])
@admin_required
def api_delete_user(username):
    if username == session.get("username"):
        return jsonify({"success": False, "error": "Cannot delete yourself"}), 400
    if delete_user(username):
        log_info(f"Deleted user: {username} (by {session.get('username')})")
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "User not found"}), 404


@app.route("/api/users/password", methods=["PUT"])
@login_required
def api_change_password():
    d        = request.json or {}
    username = session.get("username")
    old_pw   = d.get("old_password", "")
    new_pw   = d.get("new_password", "")
    if not authenticate(username, old_pw):
        return jsonify({"success": False, "error": "Current password is incorrect"}), 400
    if len(new_pw) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters"}), 400
    change_password(username, new_pw)
    return jsonify({"success": True})


# ── SESSION INFO ──────────────────────────────────────────────────────────────

@app.route("/api/me")
@login_required
def api_me():
    return jsonify({
        "success":  True,
        "username": session.get("username"),
        "role":     session.get("role"),
    })


# ── ERROR HANDLERS ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(_):
    return jsonify({"success": False, "error": "Not found"}), 404


@app.errorhandler(500)
def server_error(_):
    return jsonify({"success": False, "error": "Server error"}), 500


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("data/backups", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    created = ensure_default_admin()

    try:
        create_backup()
        cleanup_old_backups(keep_count=10)
        log_info("Web server starting")
    except Exception as e:
        log_error("Startup error", e)

    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "127.0.0.1"

    print("\n" + "=" * 60)
    print("  IP MANAGEMENT TOOL  v1.0.0  (Web Edition)")
    print("=" * 60)
    print(f"  Local:   http://localhost:5000")
    print(f"  Network: http://{local_ip}:5000")
    if created:
        print("  Default login — username: admin   password: admin123")
        print("  Change your password after first login!")
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)
