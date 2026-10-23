// Peer Library - Single Resource Detail Page
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (window.PeerLibraryAPI) {
      PeerLibraryAPI.updateNavbarAuth();
    }

    var params = new URLSearchParams(window.location.search);
    var resourceId = params.get("id");

    if (!resourceId) {
      showError("No resource ID specified.");
      return;
    }

    loadResource(resourceId);
  });

  async function loadResource(id) {
    var container = document.getElementById("resource-detail-container");
    if (!container) return;

    try {
      var res = await PeerLibraryAPI.apiFetch("/api/resources/" + encodeURIComponent(id));
      if (res.status === 404) {
        showError("That resource does not exist or has been made private.");
        return;
      }
      if (!res.ok) {
        throw new Error("HTTP error " + res.status);
      }
      var r = await res.json();
      renderResource(r);
    } catch (err) {
      console.error("Error loading resource:", err);
      showError("Could not retrieve resource details. Please try again later.");
    }
  }

  function showError(msg) {
    var container = document.getElementById("resource-detail-container");
    if (!container) return;

    container.innerHTML =
      '<div class="glass-panel text-center py-5">' +
      '  <i class="fa-regular fa-file-excel text-muted display-4 mb-3" aria-hidden="true"></i>' +
      '  <h1 class="h3">Resource not found</h1>' +
      '  <p class="text-muted mb-4">' + PeerLibraryAPI.escapeHtml(msg) + '</p>' +
      '  <a href="index.html" class="btn btn-human btn-sm"><i class="fa-solid fa-arrow-left me-1"></i> Back to catalogue</a>' +
      '</div>';
  }

  function renderResource(r) {
    var container = document.getElementById("resource-detail-container");
    if (!container) return;

    document.title = r.title + " — Peer Library";

    var pf = r.file;
    var fileSection = "";
    if (pf) {
      var downloadUrl = PeerLibraryAPI.url("/download/" + encodeURIComponent(pf.id));
      var kb = (pf.file_size ? (pf.file_size / 1024).toFixed(1) : "0") + " KB";
      var mime = pf.mime_type || "file";
      fileSection =
        '<div class="mt-4">' +
        '  <a href="' + downloadUrl + '" class="btn btn-human" target="_blank" rel="noopener noreferrer">' +
        '    <i class="fa-solid fa-download me-1" aria-hidden="true"></i> Download ' + PeerLibraryAPI.escapeHtml(pf.original_filename) +
        '  </a>' +
        '  <span class="small text-muted ms-2">' + kb + ' · ' + PeerLibraryAPI.escapeHtml(mime) + '</span>' +
        '</div>';
    } else {
      fileSection =
        '<div class="mt-4">' +
        '  <div class="alert alert-secondary mb-0" role="status">' +
        '    <i class="fa-regular fa-file-circle-xmark me-1" aria-hidden="true"></i> No downloadable file is attached to this resource.' +
        '  </div>' +
        '</div>';
    }

    var metaDl = "";
    if (r.subject) metaDl += '<dt class="col-sm-3">Subject</dt><dd class="col-sm-9">' + PeerLibraryAPI.escapeHtml(r.subject) + '</dd>';
    if (r.category) metaDl += '<dt class="col-sm-3">Category</dt><dd class="col-sm-9">' + PeerLibraryAPI.escapeHtml(r.category) + '</dd>';
    if (r.department) metaDl += '<dt class="col-sm-3">Department</dt><dd class="col-sm-9">' + PeerLibraryAPI.escapeHtml(r.department) + '</dd>';
    if (r.semester) metaDl += '<dt class="col-sm-3">Semester</dt><dd class="col-sm-9">' + PeerLibraryAPI.escapeHtml(r.semester) + '</dd>';

    var rollTag = "";
    if (r.roll_number) {
      rollTag = ' · Roll no. ' + PeerLibraryAPI.escapeHtml(r.roll_number) + ' <span class="badge bg-secondary-subtle text-secondary-emphasis">unverified</span>';
    }

    var dateStr = r.created_at ? new Date(r.created_at).toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" }) : "";

    container.innerHTML =
      '<article class="glass-panel">' +
      '  <div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">' +
      '    <div>' +
      '      <span class="badge badge-type text-uppercase mb-2">' + PeerLibraryAPI.escapeHtml(r.resource_type || "resource") + '</span>' +
      '      <h1 class="h3 fw-bold mb-1">' + PeerLibraryAPI.escapeHtml(r.title) + '</h1>' +
      '      <p class="text-muted mb-0">' +
      '        <i class="fa-solid fa-user-graduate me-1" aria-hidden="true"></i>' + PeerLibraryAPI.escapeHtml(r.uploader_name || "Unknown") + rollTag +
      '      </p>' +
      '    </div>' +
      '    <div class="text-md-end small text-muted">' +
      '      <div><i class="fa-regular fa-clock me-1" aria-hidden="true"></i>' + dateStr + '</div>' +
      '      <div><i class="fa-solid fa-download me-1" aria-hidden="true"></i>' + (r.download_count || 0) + ' downloads</div>' +
      '    </div>' +
      '  </div>' +
      (metaDl ? '  <dl class="row small mb-3">' + metaDl + '</dl>' : '') +
      '  <hr class="opacity-10">' +
      '  <h2 class="h6 text-uppercase text-muted">Description</h2>' +
      '  <div class="resource-description">' + PeerLibraryAPI.linkify(r.description) + '</div>' +
      fileSection +
      '</article>';
  }
})();
