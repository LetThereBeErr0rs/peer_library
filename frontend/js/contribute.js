// Peer Library - Contribute / Upload Module
(function () {
  "use strict";

  var form, submitBtn, alertBox, fileInput, fileInfo;
  var MAX_BYTES = 25 * 1024 * 1024; // 25 MiB
  var ALLOWED_EXTS = ["pdf", "png", "jpg", "jpeg", "txt", "docx"];

  document.addEventListener("DOMContentLoaded", async function () {
    form = document.getElementById("share-form");
    submitBtn = document.getElementById("submit-btn");
    alertBox = document.getElementById("form-alert");
    fileInput = document.getElementById("file");
    fileInfo = document.getElementById("file-info");

    if (window.PeerLibraryAPI) {
      await PeerLibraryAPI.updateNavbarAuth();
      var user = await PeerLibraryAPI.getCurrentUser();
      if (!user) {
        // Redirect to login if unauthenticated
        window.location.href = "login.html?next=contribute.html";
        return;
      }
      var userTag = document.getElementById("uploader-name-display");
      if (userTag) userTag.textContent = user.display_name;
    }

    if (fileInput) {
      fileInput.addEventListener("change", function () {
        if (!fileInput.files || fileInput.files.length === 0) {
          if (fileInfo) fileInfo.textContent = "";
          return;
        }
        var file = fileInput.files[0];
        var ext = (file.name.split(".").pop() || "").toLowerCase();

        if (!ALLOWED_EXTS.includes(ext)) {
          showError("Unsupported file type ." + ext + ". Allowed formats: " + ALLOWED_EXTS.join(", "));
          fileInput.value = "";
          if (fileInfo) fileInfo.textContent = "";
          return;
        }

        if (file.size > MAX_BYTES) {
          showError("File is too large (" + (file.size / (1024 * 1024)).toFixed(1) + " MiB). Maximum allowed size is 25 MiB.");
          fileInput.value = "";
          if (fileInfo) fileInfo.textContent = "";
          return;
        }

        clearError();
        if (fileInfo) {
          fileInfo.textContent = "Selected: " + file.name + " (" + (file.size / 1024).toFixed(1) + " KB)";
        }
      });
    }

    if (form) {
      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        clearError();

        var title = (document.getElementById("title").value || "").trim();
        var description = (document.getElementById("description").value || "").trim();

        if (!title) {
          showError("Please enter a title for your resource.");
          return;
        }
        if (!description) {
          showError("Please enter a description or paste your notes.");
          return;
        }

        setLoading(true);

        try {
          var formData = new FormData(form);
          var res = await PeerLibraryAPI.apiFetch("/api/resources", {
            method: "POST",
            body: formData,
          });

          var data = await res.json().catch(function () { return {}; });

          if (res.status === 201 && data.resource) {
            PeerLibraryAPI.showToast("Your resource has been published!", "success");
            setTimeout(function () {
              window.location.href = "resource.html?id=" + encodeURIComponent(data.resource.id);
            }, 600);
          } else {
            showError(data.error || "Could not publish your resource. Please try again.");
            setLoading(false);
          }
        } catch (err) {
          console.error("Upload error:", err);
          showError("A network error occurred. Please check your connection and try again.");
          setLoading(false);
        }
      });
    }
  });

  function showError(msg) {
    if (!alertBox) return;
    alertBox.textContent = msg;
    alertBox.style.display = "block";
  }

  function clearError() {
    if (!alertBox) return;
    alertBox.textContent = "";
    alertBox.style.display = "none";
  }

  function setLoading(isLoading) {
    if (!submitBtn) return;
    if (isLoading) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Uploading…';
    } else {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane me-2" aria-hidden="true"></i> Add to Library';
    }
  }
})();
