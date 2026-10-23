// Peer Library - Client-side Login and Registration
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    if (window.PeerLibraryAPI) {
      PeerLibraryAPI.updateNavbarAuth();
    }

    setupPasswordToggles();
    setupLoginForm();
    setupRegisterForm();
  });

  function setupPasswordToggles() {
    document.querySelectorAll(".toggle-password").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var inputId = btn.getAttribute("data-target");
        var input = document.getElementById(inputId);
        if (!input) return;
        var isPass = input.type === "password";
        input.type = isPass ? "text" : "password";
        btn.setAttribute("aria-label", isPass ? "Hide password" : "Show password");
        var i = btn.querySelector("i");
        if (i) {
          i.classList.toggle("fa-eye-slash", isPass);
          i.classList.toggle("fa-eye", !isPass);
        }
      });
    });
  }

  function setupLoginForm() {
    var form = document.getElementById("loginForm");
    var alertBox = document.getElementById("loginAlert");
    var submitBtn = document.getElementById("loginSubmitBtn");
    if (!form) return;

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      if (alertBox) alertBox.style.display = "none";

      var email = (document.getElementById("email").value || "").trim();
      var password = document.getElementById("password").value || "";

      if (!email || !password) {
        showError(alertBox, "Please provide both email and password.");
        return;
      }

      setLoading(submitBtn, true, "Logging in…");

      try {
        var res = await PeerLibraryAPI.apiFetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email, password: password }),
        });

        var data = await res.json().catch(function () { return {}; });

        if (res.ok && data.success) {
          PeerLibraryAPI.showToast("Welcome back, " + (data.user.display_name || "student") + "!", "success");
          var params = new URLSearchParams(window.location.search);
          var nextUrl = params.get("next") || "index.html";
          setTimeout(function () {
            window.location.href = nextUrl;
          }, 400);
        } else {
          showError(alertBox, data.error || "Incorrect email or password.");
          setLoading(submitBtn, false, "Log in");
        }
      } catch (err) {
        console.error("Login network error:", err);
        showError(alertBox, "Network error. Please verify the backend service is reachable.");
        setLoading(submitBtn, false, "Log in");
      }
    });
  }

  function setupRegisterForm() {
    var form = document.getElementById("registerForm");
    var alertBox = document.getElementById("registerAlert");
    var submitBtn = document.getElementById("registerSubmitBtn");
    if (!form) return;

    form.addEventListener("submit", async function (e) {
      e.preventDefault();
      if (alertBox) alertBox.style.display = "none";

      var displayName = (document.getElementById("displayName").value || "").trim();
      var email = (document.getElementById("email").value || "").trim();
      var password = document.getElementById("password").value || "";
      var confirm = document.getElementById("confirm").value || "";
      var rollNumber = (document.getElementById("rollNumber").value || "").trim();
      var department = (document.getElementById("department").value || "").trim();

      if (!displayName) {
        showError(alertBox, "Please enter your name or display name.");
        return;
      }
      if (!email || !email.includes("@")) {
        showError(alertBox, "Please enter a valid email address.");
        return;
      }
      if (!password || password.length < 8) {
        showError(alertBox, "Password must be at least 8 characters long.");
        return;
      }
      if (password !== confirm) {
        showError(alertBox, "Passwords do not match.");
        return;
      }

      setLoading(submitBtn, true, "Creating account…");

      try {
        var res = await PeerLibraryAPI.apiFetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            display_name: displayName,
            email: email,
            password: password,
            confirm: confirm,
            roll_number: rollNumber,
            department: department,
          }),
        });

        var data = await res.json().catch(function () { return {}; });

        if (res.status === 201 && data.success) {
          PeerLibraryAPI.showToast("Welcome to Peer Library!", "success");
          setTimeout(function () {
            window.location.href = "index.html";
          }, 400);
        } else {
          showError(alertBox, data.error || "Could not complete registration.");
          setLoading(submitBtn, false, "Sign up");
        }
      } catch (err) {
        console.error("Register network error:", err);
        showError(alertBox, "Network error. Please verify the backend service is reachable.");
        setLoading(submitBtn, false, "Sign up");
      }
    });
  }

  function showError(box, msg) {
    if (!box) return;
    box.textContent = msg;
    box.style.display = "block";
  }

  function setLoading(btn, isLoading, label) {
    if (!btn) return;
    if (isLoading) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> ' + label;
    } else {
      btn.disabled = false;
      btn.textContent = label;
    }
  }
})();
