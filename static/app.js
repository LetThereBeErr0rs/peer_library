// Peer Library front-end.
//
// Security note: user-generated content is rendered ONLY via DOM creation and
// textContent / setAttribute — never innerHTML with interpolated data — so a
// stored payload like <script>…</script> shows as inert text.

(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    setupTheme();
    setupPasswordToggles();
    setupLiveSearch();
    setupSubmitGuard();
  });

  // ---------- Theme ----------
  function setupTheme() {
    var toggle = document.getElementById("themeToggle");
    var icon = document.getElementById("themeIcon");
    var html = document.documentElement;

    function updateIcon(theme) {
      if (!icon) return;
      icon.classList.toggle("fa-sun", theme === "dark");
      icon.classList.toggle("fa-moon", theme !== "dark");
    }

    var saved = "light";
    try {
      saved = localStorage.getItem("theme") || "light";
    } catch (e) {}
    updateIcon(saved);

    if (toggle) {
      toggle.addEventListener("click", function () {
        var next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
        html.setAttribute("data-theme", next);
        try {
          localStorage.setItem("theme", next);
        } catch (e) {}
        updateIcon(next);
      });
    }
  }

  // ---------- Password visibility ----------
  function setupPasswordToggles() {
    document.querySelectorAll(".toggle-password").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var input = document.getElementById(btn.getAttribute("data-target"));
        if (!input) return;
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
        var i = btn.querySelector("i");
        if (i) {
          i.classList.toggle("fa-eye-slash", show);
          i.classList.toggle("fa-eye", !show);
        }
      });
    });
  }

  // ---------- Submit guard (prevents double-submit) ----------
  function setupSubmitGuard() {
    var form = document.getElementById("share-form");
    if (!form) return;
    form.addEventListener("submit", function () {
      var btn = document.getElementById("submit-btn");
      if (btn) {
        btn.disabled = true;
        btn.classList.add("disabled");
      }
    });
  }

  // ---------- Live, debounced catalogue search ----------
  function setupLiveSearch() {
    var grid = document.getElementById("results-grid");
    var filterForm = document.getElementById("filterForm");
    if (!grid || !filterForm) return; // only on the catalogue page

    var status = document.getElementById("results-status");
    var timer;

    function currentParams() {
      var fd = new FormData(filterForm);
      var params = new URLSearchParams();
      fd.forEach(function (value, key) {
        if (value) params.set(key, value);
      });
      return params;
    }

    function run() {
      var params = currentParams();
      if (status) status.textContent = "Searching…";
      fetch("/api/resources?" + params.toString(), {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (r) {
          if (!r.ok) throw new Error("Request failed");
          return r.json();
        })
        .then(function (data) {
          render(grid, data.resources);
          updateUrl(params);
          hidePagination();
          if (status) {
            status.textContent =
              data.total + (data.total === 1 ? " resource found" : " resources found");
          }
        })
        .catch(function () {
          if (status) status.textContent = "Search failed. Showing the full page instead.";
          // On failure, fall back to a normal server-rendered navigation.
          filterForm.submit();
        });
    }

    function schedule() {
      clearTimeout(timer);
      timer = setTimeout(run, 300);
    }

    // Live updates: typing in text fields (debounced), immediate on selects.
    filterForm.querySelectorAll("input[type='search'], input[type='text']").forEach(
      function (el) {
        el.addEventListener("input", schedule);
      }
    );
    filterForm.querySelectorAll("select").forEach(function (el) {
      el.addEventListener("change", run);
    });
    // Intercept the Apply button so it updates in place (still works without JS).
    filterForm.addEventListener("submit", function (e) {
      e.preventDefault();
      run();
    });
  }

  function updateUrl(params) {
    try {
      var qs = params.toString();
      history.replaceState(null, "", qs ? "/?" + qs : "/");
    } catch (e) {}
  }

  function hidePagination() {
    // Live search replaces the grid with the first page of results; hide the
    // server-rendered pager to avoid a stale page count.
    var nav = document.getElementById("pagination-nav");
    if (nav) nav.style.display = "none";
  }

  // Build a resource card entirely with DOM APIs (XSS-safe).
  function render(grid, resources) {
    grid.textContent = "";

    if (!resources || resources.length === 0) {
      grid.appendChild(emptyState());
      return;
    }

    resources.forEach(function (r) {
      var col = el("div", "col-sm-6 col-lg-4");
      var card = el("article", "card-snippet h-100 d-flex flex-column");

      var top = el("div", "d-flex justify-content-between align-items-start gap-2 mb-2");
      top.appendChild(textBadge(r.resource_type));
      if (r.file) {
        var fileTag = el("span", "small text-muted");
        fileTag.appendChild(icon("fa-solid fa-paperclip me-1"));
        var ext = (r.file.mime_type || "file").split("/").pop();
        fileTag.appendChild(document.createTextNode(ext.toUpperCase()));
        top.appendChild(fileTag);
      }
      card.appendChild(top);

      var h = el("h2", "h5 mb-1");
      var link = el("a", "stretched-link resource-title");
      link.setAttribute("href", "/resource/" + encodeURIComponent(r.id));
      link.textContent = r.title;
      h.appendChild(link);
      card.appendChild(h);

      var meta = el("p", "mb-2 text-muted small");
      meta.appendChild(icon("fa-solid fa-user-graduate me-1"));
      meta.appendChild(document.createTextNode(r.uploader_name || "Unknown"));
      if (r.subject) {
        meta.appendChild(document.createTextNode(" · "));
        meta.appendChild(icon("fa-solid fa-book me-1"));
        meta.appendChild(document.createTextNode(r.subject));
      }
      card.appendChild(meta);

      var desc = el("p", "card-text flex-grow-1");
      var text = r.description || "";
      desc.textContent = text.length > 160 ? text.slice(0, 160) + "…" : text;
      card.appendChild(desc);

      var foot = el("div", "d-flex justify-content-between align-items-center mt-2 small text-muted");
      var date = el("span");
      date.textContent = formatDate(r.created_at);
      foot.appendChild(date);
      if (r.download_count) {
        var dl = el("span");
        dl.appendChild(icon("fa-solid fa-download me-1"));
        dl.appendChild(document.createTextNode(String(r.download_count)));
        foot.appendChild(dl);
      }
      card.appendChild(foot);

      col.appendChild(card);
      grid.appendChild(col);
    });
  }

  function emptyState() {
    var col = el("div", "col-12");
    var panel = el("div", "text-center py-5 glass-panel");
    var h = el("h2", "h4");
    h.textContent = "No resources found";
    var p = el("p", "text-muted");
    p.textContent = "Try a different search or clear your filters.";
    panel.appendChild(h);
    panel.appendChild(p);
    col.appendChild(panel);
    return col;
  }

  function textBadge(type) {
    var b = el("span", "badge badge-type text-uppercase");
    b.textContent = type || "resource";
    return b;
  }

  function icon(cls) {
    var i = document.createElement("i");
    i.className = cls;
    i.setAttribute("aria-hidden", "true");
    return i;
  }

  function el(tag, cls) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    return node;
  }

  function formatDate(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d)) return "";
    return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
  }
})();
