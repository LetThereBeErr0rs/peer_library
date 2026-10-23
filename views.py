"""Main blueprint: catalogue, search API, resource detail, contribute, download."""
import logging

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    abort,
    flash,
    current_app,
)
from flask_login import login_required, current_user

from extensions import db, limiter
from models import Resource, ResourceFile
from forms import UploadForm
from services import search_resources, create_resource, register_download
from storage import get_storage, StorageError
from validation import FileValidationError

log = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


def _filter_args():
    args = request.args
    return {
        "query": (args.get("q") or "").strip() or None,
        "resource_type": (args.get("type") or "").strip() or None,
        "subject": (args.get("subject") or "").strip() or None,
        "category": (args.get("category") or "").strip() or None,
        "semester": (args.get("semester") or "").strip() or None,
        "sort": (args.get("sort") or "newest").strip(),
    }


@main_bp.route("/")
def index():
    """Catalogue-first homepage. Works fully server-side without JavaScript."""
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config.get("RESOURCES_PER_PAGE", 12)
    filters = _filter_args()
    pagination = search_resources(page=page, per_page=per_page, **filters)
    # Query-string values (arg name -> value) used to preserve filters across
    # pagination links.
    arg_map = {
        "q": filters["query"],
        "type": filters["resource_type"],
        "subject": filters["subject"],
        "category": filters["category"],
        "semester": filters["semester"],
        "sort": filters["sort"],
    }
    filters_qs = {k: v for k, v in arg_map.items() if v}
    return render_template(
        "index.html",
        pagination=pagination,
        resources=pagination.items,
        filters=filters,
        filters_qs=filters_qs,
        resource_types=Resource.RESOURCE_TYPES,
    )


@main_bp.route("/healthz")
@main_bp.route("/api/health")
def healthz():
    """Lightweight health-check endpoint for Render / Docker orchestration."""
    return jsonify({"status": "ok"}), 200


@main_bp.route("/api/resources")
def api_resources():
    """JSON listing/search used by the debounced search box."""
    page = request.args.get("page", 1, type=int)
    per_page = current_app.config.get("RESOURCES_PER_PAGE", 12)
    filters = _filter_args()
    pagination = search_resources(page=page, per_page=per_page, **filters)
    return jsonify(
        {
            "resources": [r.to_dict() for r in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        }
    )


def _can_view_resource(resource):
    """Authorization for viewing a resource's detail.

    Published resources are public. Any other status (pending, hidden, …) is
    restricted to the resource's owner and administrators. Everyone else is
    treated as if the resource does not exist.
    """
    if resource is None:
        return False
    if resource.status == "published":
        return True
    if not current_user.is_authenticated:
        return False
    return current_user.is_admin or current_user.id == resource.uploader_id


@main_bp.route("/resource/<int:resource_id>")
def resource_detail(resource_id):
    resource = db.session.get(Resource, resource_id)
    if not _can_view_resource(resource):
        # 404 (not 403) so we never disclose the existence of a restricted
        # resource to unauthorized visitors guessing IDs.
        abort(404)
    return render_template("resource_detail.html", resource=resource)


@main_bp.route("/api/resources/<int:resource_id>")
def api_resource_detail(resource_id):
    """JSON resource detail endpoint for the static/decoupled frontend."""
    resource = db.session.get(Resource, resource_id)
    if not _can_view_resource(resource):
        abort(404)
    return jsonify(resource.to_dict(include_file=True))


@main_bp.route("/api/resources", methods=["POST"])
@login_required
@limiter.limit("30 per hour", methods=["POST"])
def api_create_resource():
    """JSON/multipart upload endpoint for the static frontend."""
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    resource_type = (request.form.get("resource_type") or "notes").strip()
    subject = (request.form.get("subject") or "").strip() or None
    category = (request.form.get("category") or "").strip() or None
    semester = (request.form.get("semester") or "").strip() or None
    department = (request.form.get("department") or "").strip() or None
    file_storage = request.files.get("file")

    if not title:
        return jsonify({"error": "Title is required."}), 400
    if len(title) > 200:
        return jsonify({"error": "Title cannot exceed 200 characters."}), 400
    if not description:
        return jsonify({"error": "Description is required."}), 400
    if resource_type not in Resource.RESOURCE_TYPES:
        return jsonify({"error": f"Invalid resource type. Choose from: {', '.join(Resource.RESOURCE_TYPES)}"}), 400

    try:
        resource = create_resource(
            form_data={
                "title": title,
                "description": description,
                "resource_type": resource_type,
                "subject": subject,
                "category": category,
                "semester": semester,
                "department": department,
            },
            uploader=current_user,
            file_storage=file_storage,
        )
    except FileValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except StorageError as exc:
        log.error("Storage error during API upload: %s", exc)
        return jsonify({"error": "The file could not be stored. Please try again."}), 502
    except Exception:
        log.exception("Unexpected error creating resource via API")
        return jsonify({"error": "Something went wrong saving your resource."}), 500

    return jsonify({"success": True, "resource": resource.to_dict(include_file=True)}), 201


@main_bp.route("/contribute", methods=["GET", "POST"])
@login_required
@limiter.limit("30 per hour", methods=["POST"])
def contribute():
    form = UploadForm()
    if form.validate_on_submit():
        try:
            resource = create_resource(
                form_data={
                    "title": form.title.data,
                    "description": form.description.data,
                    "resource_type": form.resource_type.data,
                    "subject": form.subject.data,
                    "category": form.category.data,
                    "semester": form.semester.data,
                    "department": form.department.data,
                },
                uploader=current_user,
                file_storage=form.file.data,
            )
        except FileValidationError as exc:
            flash(str(exc), "danger")
            return render_template("contribute.html", form=form), 400
        except StorageError as exc:
            log.error("Storage error during upload: %s", exc)
            flash("The file could not be stored. Please try again.", "danger")
            return render_template("contribute.html", form=form), 502
        except Exception:
            log.exception("Unexpected error creating resource")
            flash("Something went wrong saving your resource.", "danger")
            return render_template("contribute.html", form=form), 500

        flash("Your resource has been published.", "success")
        return redirect(url_for("main.resource_detail", resource_id=resource.id))

    # A POST that failed validation (bad field or rejected file) is a 400.
    status = 400 if request.method == "POST" else 200
    return render_template("contribute.html", form=form), status


@main_bp.route("/download/<int:file_id>")
@main_bp.route("/api/download/<int:file_id>")
def download(file_id):
    """Authorize by resource/file id, then serve. Never trusts a client path."""
    rf = db.session.get(ResourceFile, file_id)
    if rf is None:
        abort(404)
    resource = rf.resource
    if resource is None:
        abort(404)

    # Access control: published resources download freely; hidden/pending are
    # restricted to the uploader or an admin.
    if resource.status != "published":
        allowed = current_user.is_authenticated and (
            current_user.is_admin or current_user.id == resource.uploader_id
        )
        if not allowed:
            abort(403)

    storage = get_storage()
    if not storage.exists(rf.storage_key):
        # Dangling reference (e.g. a legacy file that no longer exists).
        abort(410)  # Gone

    register_download(resource)
    try:
        return storage.send(
            rf.storage_key,
            download_name=rf.original_filename or f"resource-{resource.id}",
            mime_type=rf.mime_type,
        )
    except StorageError:
        abort(410)


# --- Minimal admin moderation ---
@main_bp.route("/admin/resource/<int:resource_id>/status", methods=["POST"])
@login_required
def admin_set_status(resource_id):
    if not current_user.is_admin:
        abort(403)
    resource = db.session.get(Resource, resource_id)
    if resource is None:
        abort(404)
    new_status = (request.form.get("status") or "").strip()
    if new_status not in Resource.STATUSES:
        abort(400)
    resource.status = new_status
    db.session.commit()
    flash(f"Resource marked {new_status}.", "success")
    return redirect(url_for("main.resource_detail", resource_id=resource.id))
