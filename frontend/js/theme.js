// Theme manager for Peer Library (light/dark mode)
(function () {
  "use strict";

  // Immediate theme application before DOM loads to avoid theme flicker
  var saved = "light";
  try {
    saved = localStorage.getItem("theme") || "light";
  } catch (e) {}
  document.documentElement.setAttribute("data-theme", saved);

  document.addEventListener("DOMContentLoaded", function () {
    var toggle = document.getElementById("themeToggle");
    var icon = document.getElementById("themeIcon");
    var html = document.documentElement;

    function updateIcon(theme) {
      if (!icon) return;
      icon.classList.toggle("fa-sun", theme === "dark");
      icon.classList.toggle("fa-moon", theme !== "dark");
    }

    updateIcon(saved);

    if (toggle) {
      toggle.addEventListener("click", function () {
        var current = html.getAttribute("data-theme") || "light";
        var next = current === "dark" ? "light" : "dark";
        html.setAttribute("data-theme", next);
        try {
          localStorage.setItem("theme", next);
        } catch (e) {}
        updateIcon(next);
      });
    }
  });
})();
