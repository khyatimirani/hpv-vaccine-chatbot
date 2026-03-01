/* =========================================================
   HPV Vaccine Assistant — Frontend JavaScript
   ========================================================= */

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Tab switching
  // ---------------------------------------------------------------------------

  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");

  tabBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const target = btn.dataset.tab;

      tabBtns.forEach(function (b) { b.classList.remove("active"); });
      tabPanels.forEach(function (p) { p.classList.remove("active"); p.classList.add("hidden"); });

      btn.classList.add("active");
      const panel = document.getElementById("tab-" + target);
      if (panel) {
        panel.classList.remove("hidden");
        panel.classList.add("active");
      }

      // Lazy-load Myth vs Fact content when that tab is first opened
      if (target === "myth" && !panel.dataset.loaded) {
        loadMythVsFact(panel);
      }
    });
  });

  // ---------------------------------------------------------------------------
  // Myth vs Fact loader (converts Markdown to simple HTML)
  // ---------------------------------------------------------------------------

  function loadMythVsFact(panel) {
    fetch("/api/myth-vs-fact")
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        const container = document.getElementById("myth-content");
        container.innerHTML = markdownToHtml(data.content || "No content available.");
        panel.dataset.loaded = "1";
      })
      .catch(function () {
        document.getElementById("myth-content").textContent = "Failed to load content.";
      });
  }

  /** Very simple Markdown → HTML converter for headings, bold, lists, paragraphs. */
  function markdownToHtml(md) {
    const lines = md.split("\n");
    let html = "";
    let inList = false;

    lines.forEach(function (line) {
      if (/^###\s/.test(line)) {
        if (inList) { html += "</ul>"; inList = false; }
        html += "<h3>" + escHtml(line.replace(/^###\s/, "")) + "</h3>";
      } else if (/^##\s/.test(line)) {
        if (inList) { html += "</ul>"; inList = false; }
        html += "<h2>" + escHtml(line.replace(/^##\s/, "")) + "</h2>";
      } else if (/^#\s/.test(line)) {
        if (inList) { html += "</ul>"; inList = false; }
        html += "<h1>" + escHtml(line.replace(/^#\s/, "")) + "</h1>";
      } else if (/^[-*]\s/.test(line)) {
        if (!inList) { html += "<ul>"; inList = true; }
        html += "<li>" + inlineMarkdown(line.replace(/^[-*]\s/, "")) + "</li>";
      } else if (line.trim() === "") {
        if (inList) { html += "</ul>"; inList = false; }
        html += "<br/>";
      } else {
        if (inList) { html += "</ul>"; inList = false; }
        html += "<p>" + inlineMarkdown(line) + "</p>";
      }
    });

    if (inList) html += "</ul>";
    return html;
  }

  function inlineMarkdown(text) {
    return escHtml(text)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/_(.+?)_/g, "<em>$1</em>");
  }

  function escHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // ---------------------------------------------------------------------------
  // Chat
  // ---------------------------------------------------------------------------

  const chatMessages = document.getElementById("chat-messages");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const clearBtn = document.getElementById("clear-btn");

  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = "message " + (role === "user" ? "user-message" : "assistant-message");
    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = text;
    div.appendChild(bubble);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  function appendThinking() {
    const div = document.createElement("div");
    div.className = "message assistant-message";
    const inner = document.createElement("div");
    inner.className = "thinking";
    inner.textContent = "Thinking";
    div.appendChild(inner);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  chatForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    appendMessage("user", text);
    chatInput.value = "";

    const thinkingEl = appendThinking();

    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        thinkingEl.remove();
        if (data.error) {
          appendMessage("assistant", "⚠️ " + data.error);
        } else {
          appendMessage("assistant", data.answer || "No answer returned.");
        }
      })
      .catch(function () {
        thinkingEl.remove();
        appendMessage("assistant", "⚠️ Network error. Please try again.");
      });
  });

  clearBtn.addEventListener("click", function () {
    fetch("/api/clear-history", { method: "POST" })
      .then(function () {
        chatMessages.innerHTML = "";
        appendMessage("assistant", "Conversation cleared. How can I help you today?");
      });
  });

  // ---------------------------------------------------------------------------
  // Eligibility Checker
  // ---------------------------------------------------------------------------

  const eligibilityForm = document.getElementById("eligibility-form");
  const eligibilityResult = document.getElementById("eligibility-result");

  eligibilityForm.addEventListener("submit", function (e) {
    e.preventDefault();

    const age = parseInt(document.getElementById("age").value, 10);
    const gender = document.getElementById("gender").value;
    const alreadyVaccinated =
      document.querySelector("input[name='already_vaccinated']:checked").value === "Yes";
    const isPregnant =
      document.querySelector("input[name='is_pregnant']:checked").value === "Yes";

    fetch("/api/eligibility", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        age: age,
        gender: gender,
        already_vaccinated: alreadyVaccinated,
        is_pregnant: isPregnant,
      }),
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        eligibilityResult.classList.remove("hidden", "eligible", "not-eligible");

        let html = "";
        if (data.eligible) {
          eligibilityResult.classList.add("eligible");
          html += "<strong>✅ Eligible for HPV Vaccination</strong><br/>";
        } else {
          eligibilityResult.classList.add("not-eligible");
          html += "<strong>ℹ️ Not currently recommended</strong><br/>";
        }

        html += "<p>" + escHtml(data.recommendation) + "</p>";
        html += "<p><strong>Dose Schedule:</strong> " + escHtml(data.dose_schedule) + "</p>";

        if (data.notes && data.notes.length > 0) {
          html += "<strong>Additional Notes:</strong><ul>";
          data.notes.forEach(function (note) {
            html += "<li>" + escHtml(note) + "</li>";
          });
          html += "</ul>";
        }

        html += "<p><small>⚕️ Always consult a qualified healthcare provider before making vaccination decisions.</small></p>";

        eligibilityResult.innerHTML = html;
      })
      .catch(function () {
        eligibilityResult.classList.remove("hidden");
        eligibilityResult.textContent = "⚠️ Could not check eligibility. Please try again.";
      });
  });

  // ---------------------------------------------------------------------------
  // Sidebar
  // ---------------------------------------------------------------------------

  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  const sidebarClose = document.getElementById("sidebar-close");

  sidebarToggle.addEventListener("click", function () {
    sidebar.classList.toggle("hidden");
  });

  sidebarClose.addEventListener("click", function () {
    sidebar.classList.add("hidden");
  });

  // ---------------------------------------------------------------------------
  // Document upload
  // ---------------------------------------------------------------------------

  const uploadForm = document.getElementById("upload-form");
  const uploadResult = document.getElementById("upload-result");

  uploadForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const fileInput = document.getElementById("upload-file");
    if (!fileInput.files.length) {
      uploadResult.textContent = "Please select a file first.";
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    uploadResult.textContent = "Uploading…";

    fetch("/api/upload-document", {
      method: "POST",
      body: formData,
    })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        uploadResult.textContent = data.message || data.error || "Done.";
        fileInput.value = "";
      })
      .catch(function () {
        uploadResult.textContent = "⚠️ Upload failed. Please try again.";
      });
  });
})();
