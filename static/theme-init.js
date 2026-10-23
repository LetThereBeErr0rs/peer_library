// Applies the saved theme before paint to avoid a flash of the wrong theme.
// Kept as an external file so the Content-Security-Policy need not allow
// inline scripts.
(function () {
  try {
    var saved = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", saved);
  } catch (e) {
    document.documentElement.setAttribute("data-theme", "light");
  }
})();
