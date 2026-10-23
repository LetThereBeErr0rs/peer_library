// Peer Library Client API module
(function (global) {
  "use strict";

  // When deployed on Vercel with proxy rewrites, API_BASE is empty string (same-origin).
  // If connecting directly to Render cross-origin, set window.PEER_LIBRARY_API_BASE = 'https://YOUR-RENDER-URL.onrender.com'
  var API_BASE = (global.PEER_LIBRARY_API_BASE || "").replace(/\/+$/, "");
  var cachedCsrfToken = null;

  function url(path) {
    if (!path.startsWith("/")) path = "/" + path;
    return API_BASE + path;
  }

  async function getCsrfToken(forceRefresh) {
    if (cachedCsrfToken && !forceRefresh) {
      return cachedCsrfToken;
    }
    try {
      var res = await fetch(url("/api/auth/csrf"), {
        credentials: "include",
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (res.ok) {
        var data = await res.json();
        cachedCsrfToken = data.csrf_token;
        return cachedCsrfToken;
      }
    } catch (e) {
      console.warn("Could not obtain CSRF token:", e);
    }
    return "";
  }

  async function apiFetch(path, options) {
    options = options || {};
    options.credentials = "include"; // Send and receive session cookies
    options.headers = options.headers || {};

    if (!(options.headers instanceof Headers)) {
      options.headers["X-Requested-With"] = "XMLHttpRequest";
    }

    var method = (options.method || "GET").toUpperCase();
    if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
      var token = await getCsrfToken();
      if (token) {
        if (options.headers instanceof Headers) {
          options.headers.set("X-CSRFToken", token);
        } else {
          options.headers["X-CSRFToken"] = token;
        }
      }
    }

    var fullUrl = url(path);
    var response = await fetch(fullUrl, options);

    // If CSRF error occurs (e.g. session expired), refresh token once and retry
    if (response.status === 400 && ["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
      var clone = response.clone();
      var errData = await clone.json().catch(function () { return {}; });
      if (errData.error && errData.error.toLowerCase().includes("csrf")) {
        var newToken = await getCsrfToken(true);
        if (options.headers instanceof Headers) {
          options.headers.set("X-CSRFToken", newToken);
        } else {
          options.headers["X-CSRFToken"] = newToken;
        }
        return await fetch(fullUrl, options);
      }
    }

    return response;
  }

  async function getCurrentUser() {
    try {
      var res = await apiFetch("/api/auth/me");
      if (res.ok) {
        var data = await res.json();
        return data.user || null;
      }
    } catch (e) {
      console.warn("Could not check current user:", e);
    }
    return null;
  }

  function showToast(message, type) {
    type = type || "info"; // success, danger, warning, info
    var container = document.getElementById("toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.style.position = "fixed";
      container.style.top = "1.5rem";
      container.style.right = "1.5rem";
      container.style.zIndex = "9999";
      container.style.maxWidth = "350px";
      document.body.appendChild(container);
    }

    var alert = document.createElement("div");
    alert.className = "alert alert-" + type + " alert-dismissible fade show shadow-sm";
    alert.setAttribute("role", "alert");
    alert.textContent = message;

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-close";
    btn.setAttribute("aria-label", "Close");
    btn.onclick = function () {
      if (alert.parentNode) alert.parentNode.removeChild(alert);
    };

    alert.appendChild(btn);
    container.appendChild(alert);

    setTimeout(function () {
      if (alert.parentNode) {
        alert.classList.remove("show");
        setTimeout(function () {
          if (alert.parentNode) alert.parentNode.removeChild(alert);
        }, 150);
      }
    }, 4000);
  }

  // Update navbar auth state (user menu vs login/register buttons)
  async function updateNavbarAuth() {
    var navContainer = document.getElementById("navAuthContainer");
    if (!navContainer) return;

    var user = await getCurrentUser();
    navContainer.textContent = "";

    if (user) {
      var li = document.createElement("li");
      li.className = "nav-item dropdown";

      var a = document.createElement("a");
      a.className = "nav-link dropdown-toggle";
      a.href = "#";
      a.setAttribute("role", "button");
      a.setAttribute("data-bs-toggle", "dropdown");
      a.setAttribute("aria-expanded", "false");
      a.innerHTML = '<i class="fa-solid fa-circle-user me-1" aria-hidden="true"></i> ' + escapeHtml(user.display_name);

      var ul = document.createElement("ul");
      ul.className = "dropdown-menu dropdown-menu-end";

      if (user.is_admin) {
        var adminLi = document.createElement("li");
        adminLi.innerHTML = '<span class="dropdown-item-text small text-muted">Administrator</span>';
        ul.appendChild(adminLi);
        var divider = document.createElement("li");
        divider.innerHTML = '<hr class="dropdown-divider">';
        ul.appendChild(divider);
      }

      var logoutLi = document.createElement("li");
      var logoutBtn = document.createElement("button");
      logoutBtn.className = "dropdown-item text-danger";
      logoutBtn.innerHTML = '<i class="fa-solid fa-right-from-bracket me-1" aria-hidden="true"></i> Log out';
      logoutBtn.onclick = async function (e) {
        e.preventDefault();
        try {
          var res = await apiFetch("/api/auth/logout", { method: "POST" });
          if (res.ok) {
            showToast("Logged out successfully.", "info");
            setTimeout(function () { window.location.reload(); }, 400);
          }
        } catch (err) {
          showToast("Failed to log out.", "danger");
        }
      };
      logoutLi.appendChild(logoutBtn);
      ul.appendChild(logoutLi);

      li.appendChild(a);
      li.appendChild(ul);
      navContainer.appendChild(li);
    } else {
      var loginLi = document.createElement("li");
      loginLi.className = "nav-item";
      loginLi.innerHTML = '<a class="nav-link" href="login.html">Log in</a>';

      var signupLi = document.createElement("li");
      signupLi.className = "nav-item";
      signupLi.innerHTML = '<a class="btn btn-human btn-sm ms-lg-2" href="register.html">Sign up</a>';

      navContainer.appendChild(loginLi);
      navContainer.appendChild(signupLi);
    }
  }

  function escapeHtml(str) {
    if (!str) return "";
    var div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // Safe linkify function for descriptions
  function linkify(text) {
    if (!text) return "";
    var escaped = escapeHtml(text);
    var urlRegex = /(https?:\/\/[^\s<>"]+)/g;
    return escaped.replace(urlRegex, function (matchedUrl) {
      return '<a href="' + matchedUrl + '" target="_blank" rel="noopener noreferrer">' + matchedUrl + '</a>';
    });
  }

  global.PeerLibraryAPI = {
    url: url,
    apiFetch: apiFetch,
    getCsrfToken: getCsrfToken,
    getCurrentUser: getCurrentUser,
    showToast: showToast,
    updateNavbarAuth: updateNavbarAuth,
    escapeHtml: escapeHtml,
    linkify: linkify,
  };
})(window);
