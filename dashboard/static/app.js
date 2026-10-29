// Dashboard interactions: status/notes autosave, Run now with polling, theme toggle.
(function () {
  "use strict";

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : null,
    });
  }

  function jobId(el) {
    var row = el.closest("[data-job]");
    return row ? row.getAttribute("data-job") : null;
  }

  // Status change
  document.addEventListener("change", function (e) {
    var el = e.target;
    if (!el.classList.contains("js-status")) return;
    var id = jobId(el);
    el.disabled = true;
    post("/jobs/" + id, { status: el.value })
      .then(function (r) { if (!r.ok) throw new Error(r.status); })
      .catch(function () { alert("Could not save status. Is the dashboard still running?"); })
      .finally(function () { el.disabled = false; });
  });

  // Notes: save on blur and after a pause in typing
  var timers = {};
  function saveNotes(el) {
    var id = jobId(el);
    var flag = el.parentElement.querySelector(".js-saved");
    post("/jobs/" + id, { notes: el.value })
      .then(function (r) {
        if (!r.ok) throw new Error(r.status);
        if (flag) { flag.textContent = "Saved"; setTimeout(function () { flag.textContent = ""; }, 1500); }
      })
      .catch(function () { if (flag) flag.textContent = "Not saved"; });
  }
  document.addEventListener("input", function (e) {
    var el = e.target;
    if (!el.classList.contains("js-notes")) return;
    var id = jobId(el);
    clearTimeout(timers[id]);
    timers[id] = setTimeout(function () { saveNotes(el); }, 800);
  });
  document.addEventListener("focusout", function (e) {
    var el = e.target;
    if (!el.classList.contains("js-notes")) return;
    clearTimeout(timers[jobId(el)]);
    saveNotes(el);
  });

  // Run now / Rank unranked
  var runBtn = document.getElementById("run-now");
  function poll() {
    fetch("/api/run-status").then(function (r) { return r.json(); }).then(function (s) {
      if (s.running) { setTimeout(poll, 2000); }
      else { window.location.reload(); }
    }).catch(function () { setTimeout(poll, 4000); });
  }
  function start(url) {
    if (runBtn) { runBtn.disabled = true; runBtn.textContent = "Running…"; }
    post(url).then(function (r) {
      if (r.status === 409) { alert("A run is already in progress."); }
      else if (!r.ok) { throw new Error(r.status); }
      setTimeout(poll, 1500);
    }).catch(function () {
      if (runBtn) { runBtn.disabled = false; runBtn.textContent = "Run now"; }
      alert("Could not start the run.");
    });
  }
  if (runBtn) {
    runBtn.addEventListener("click", function () { start("/run"); });
    if (runBtn.disabled) setTimeout(poll, 2000);  // page loaded mid-run
  }
  var rerank = document.getElementById("rerank");
  if (rerank) rerank.addEventListener("click", function () { rerank.disabled = true; start("/rerank"); });

  // Auto-submit filter selects
  var filters = document.getElementById("filters");
  if (filters) {
    filters.querySelectorAll("select").forEach(function (s) {
      s.addEventListener("change", function () { filters.submit(); });
    });
  }

  // Theme toggle (remembered per browser)
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var dark = document.documentElement.classList.toggle("dark");
      try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch (e) {}
    });
  }
})();
