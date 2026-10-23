// Peer Library - Catalogue & Live Search for Static Frontend
(function () {
  "use strict";

  var grid, filterForm, statusEl, paginationNav, prevBtn, nextBtn, pageInfo;
  var currentPage = 1;
  var timer = null;

  document.addEventListener("DOMContentLoaded", function () {
    grid = document.getElementById("results-grid");
    filterForm = document.getElementById("filterForm");
    statusEl = document.getElementById("results-status");
    paginationNav = document.getElementById("pagination-nav");
    prevBtn = document.getElementById("prevPageBtn");
    nextBtn = document.getElementById("nextPageBtn");
    pageInfo = document.getElementById("pageInfoText");

    if (window.PeerLibraryAPI) {
      PeerLibraryAPI.updateNavbarAuth();
    }

    if (!grid || !filterForm) return;

    // Read initial filters from URL query parameters if present
    var urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("q")) {
      var qInput = document.getElementById("q");
      if (qInput) qInput.value = urlParams.get("q");
      var navQ = document.getElementById("navSearchInput");
      if (navQ) navQ.value = urlParams.get("q");
    }
    if (urlParams.get("type")) {
      var typeSelect = document.getElementById("type");
      if (typeSelect) typeSelect.value = urlParams.get("type");
    }
    if (urlParams.get("subject")) {
      var subjInput = document.getElementById("subject");
      if (subjInput) subjInput.value = urlParams.get("subject");
    }
    if (urlParams.get("sort")) {
      var sortSelect = document.getElementById("sort");
      if (sortSelect) sortSelect.value = urlParams.get("sort");
    }
    if (urlParams.get("page")) {
      var p = parseInt(urlParams.get("page"), 10);
      if (!isNaN(p) && p > 0) currentPage = p;
    }

    setupEventListeners();
    fetchCatalogue(currentPage);
  });

  function setupEventListeners() {
    filterForm.querySelectorAll("input[type='search'], input[type='text']").forEach(function (el) {
      el.addEventListener("input", function () {
        clearTimeout(timer);
        timer = setTimeout(function () {
          currentPage = 1;
          fetchCatalogue(1);
        }, 300);
      });
    });

    filterForm.querySelectorAll("select").forEach(function (el) {
      el.addEventListener("change", function () {
        currentPage = 1;
        fetchCatalogue(1);
      });
    });

    filterForm.addEventListener("submit", function (e) {
      e.preventDefault();
      currentPage = 1;
      fetchCatalogue(1);
    });

    // Synchronize navbar search input with main search input
    var navSearch = document.getElementById("navSearchForm");
    if (navSearch) {
      navSearch.addEventListener("submit", function (e) {
        e.preventDefault();
        var navQ = document.getElementById("navSearchInput");
        var mainQ = document.getElementById("q");
        if (navQ && mainQ) {
          mainQ.value = navQ.value;
          currentPage = 1;
          fetchCatalogue(1);
        }
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener("click", function (e) {
        e.preventDefault();
        if (currentPage > 1) {
          fetchCatalogue(currentPage - 1);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", function (e) {
        e.preventDefault();
        fetchCatalogue(currentPage + 1);
      });
    }
  }

  function getFilterParams(page) {
    var fd = new FormData(filterForm);
    var params = new URLSearchParams();
    fd.forEach(function (value, key) {
      if (value) params.set(key, value.trim());
    });
    params.set("page", page || 1);
    return params;
  }

  async function fetchCatalogue(page) {
    if (!grid) return;
    currentPage = page || 1;
    var params = getFilterParams(currentPage);

    // Show loading state
    showLoading();
    if (statusEl) statusEl.textContent = "Loading resources…";

    try {
      var res = await PeerLibraryAPI.apiFetch("/api/resources?" + params.toString());
      if (!res.ok) throw new Error("HTTP error " + res.status);
      var data = await res.json();

      renderGrid(data.resources);
      updatePagination(data);
      updateBrowserUrl(params);

      if (statusEl) {
        statusEl.textContent = data.total + (data.total === 1 ? " resource found" : " resources found");
      }
    } catch (err) {
      console.error("Failed to load catalogue:", err);
      showError("Could not load study resources. Please verify that the backend service is running.");
      if (statusEl) statusEl.textContent = "Failed to load resources.";
    }
  }

  function showLoading() {
    grid.innerHTML =
      '<div class="col-12 text-center py-5">' +
      '  <div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading…</span></div>' +
      '  <p class="text-muted mt-2 small">Fetching study materials…</p>' +
      '</div>';
  }

  function showError(msg) {
    grid.innerHTML =
      '<div class="col-12">' +
      '  <div class="glass-panel text-center py-5">' +
      '    <i class="fa-solid fa-triangle-exclamation text-danger display-5 mb-3" aria-hidden="true"></i>' +
      '    <h2 class="h4">Connection problem</h2>' +
      '    <p class="text-muted mb-3">' + PeerLibraryAPI.escapeHtml(msg) + '</p>' +
      '    <button class="btn btn-human btn-sm" onclick="window.location.reload()"><i class="fa-solid fa-rotate-right me-1"></i> Retry</button>' +
      '  </div>' +
      '</div>';
    if (paginationNav) paginationNav.style.display = "none";
  }

  function renderGrid(resources) {
    grid.textContent = "";

    if (!resources || resources.length === 0) {
      grid.innerHTML =
        '<div class="col-12">' +
        '  <div class="text-center py-5 glass-panel">' +
        '    <div class="mb-3 text-muted display-5"><i class="fa-regular fa-folder-open" aria-hidden="true"></i></div>' +
        '    <h2 class="h4">No resources found</h2>' +
        '    <p class="text-muted mb-3">Try a different search term or clear your filters.</p>' +
        '    <a href="contribute.html" class="btn btn-human">' +
        '      <i class="fa-solid fa-upload me-1" aria-hidden="true"></i> Contribute a resource' +
        '    </a>' +
        '  </div>' +
        '</div>';
      return;
    }

    resources.forEach(function (r) {
      var col = document.createElement("div");
      col.className = "col-sm-6 col-lg-4";

      var article = document.createElement("article");
      article.className = "card-snippet h-100 d-flex flex-column";

      // Top row (Type Badge + Attachment tag)
      var topRow = document.createElement("div");
      topRow.className = "d-flex justify-content-between align-items-start gap-2 mb-2";

      var badge = document.createElement("span");
      badge.className = "badge badge-type text-uppercase";
      badge.textContent = r.resource_type || "resource";
      topRow.appendChild(badge);

      if (r.file) {
        var fileTag = document.createElement("span");
        fileTag.className = "small text-muted";
        fileTag.title = "Attachment";
        var ext = (r.file.mime_type || "file").split("/").pop().toUpperCase();
        fileTag.innerHTML = '<i class="fa-solid fa-paperclip me-1" aria-hidden="true"></i> ' + PeerLibraryAPI.escapeHtml(ext);
        topRow.appendChild(fileTag);
      }
      article.appendChild(topRow);

      // Title link
      var h2 = document.createElement("h2");
      h2.className = "h5 mb-1";
      var a = document.createElement("a");
      a.className = "stretched-link resource-title";
      a.href = "resource.html?id=" + encodeURIComponent(r.id);
      a.textContent = r.title;
      h2.appendChild(a);
      article.appendChild(h2);

      // Meta: Author & Subject
      var meta = document.createElement("p");
      meta.className = "mb-2 text-muted small";
      meta.innerHTML = '<i class="fa-solid fa-user-graduate me-1" aria-hidden="true"></i>' +
        PeerLibraryAPI.escapeHtml(r.uploader_name || "Unknown") +
        (r.subject ? ' · <i class="fa-solid fa-book me-1" aria-hidden="true"></i>' + PeerLibraryAPI.escapeHtml(r.subject) : "");
      article.appendChild(meta);

      // Description excerpt
      var desc = document.createElement("p");
      desc.className = "card-text flex-grow-1";
      var text = r.description || "";
      desc.textContent = text.length > 160 ? text.slice(0, 160) + "…" : text;
      article.appendChild(desc);

      // Footer: Date & Downloads
      var foot = document.createElement("div");
      foot.className = "d-flex justify-content-between align-items-center mt-2 small text-muted";

      var dateSpan = document.createElement("span");
      dateSpan.innerHTML = '<i class="fa-regular fa-clock me-1" aria-hidden="true"></i> ' + formatDate(r.created_at);
      foot.appendChild(dateSpan);

      if (r.download_count) {
        var dlSpan = document.createElement("span");
        dlSpan.innerHTML = '<i class="fa-solid fa-download me-1" aria-hidden="true"></i> ' + r.download_count;
        foot.appendChild(dlSpan);
      }
      article.appendChild(foot);

      col.appendChild(article);
      grid.appendChild(col);
    });
  }

  function updatePagination(data) {
    if (!paginationNav) return;
    if (!data.pages || data.pages <= 1) {
      paginationNav.style.display = "none";
      return;
    }

    paginationNav.style.display = "block";
    if (pageInfo) pageInfo.textContent = "Page " + data.page + " of " + data.pages;

    if (prevBtn) {
      if (data.has_prev) {
        prevBtn.classList.remove("disabled");
      } else {
        prevBtn.classList.add("disabled");
      }
    }

    if (nextBtn) {
      if (data.has_next) {
        nextBtn.classList.remove("disabled");
      } else {
        nextBtn.classList.add("disabled");
      }
    }
  }

  function updateBrowserUrl(params) {
    try {
      var qs = params.toString();
      history.replaceState(null, "", qs ? "index.html?" + qs : "index.html");
    } catch (e) {}
  }

  function formatDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d)) return "";
    return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
  }
})();
