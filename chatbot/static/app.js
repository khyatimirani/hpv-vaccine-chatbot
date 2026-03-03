/* =========================================================
   HPV Vaccine Saathi — Frontend JavaScript
   ========================================================= */

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Utility helpers
  // ---------------------------------------------------------------------------

  function escHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /** Fade out the current screen, then show the next one with a fade-in. */
  function transitionTo(fromEl, toEl, callback) {
    fromEl.style.transition = "opacity 0.3s ease";
    fromEl.style.opacity = "0";
    setTimeout(function () {
      fromEl.classList.add("fade-hidden");
      fromEl.style.opacity = "";
      fromEl.style.transition = "";
      toEl.classList.remove("fade-hidden");
      toEl.classList.add("fade-in");
      if (callback) callback();
    }, 300);
  }

  // ---------------------------------------------------------------------------
  // Onboarding state (persisted in sessionStorage)
  // ---------------------------------------------------------------------------

  var USER_KEY = "hpv_user_name";
  var EMAIL_KEY = "hpv_user_email";

  function getStoredName() { return sessionStorage.getItem(USER_KEY) || ""; }
  function getStoredEmail() { return sessionStorage.getItem(EMAIL_KEY) || ""; }

  // ---------------------------------------------------------------------------
  // Screen elements
  // ---------------------------------------------------------------------------

  var screenLanding    = document.getElementById("screen-landing");
  var screenOnboarding = document.getElementById("screen-onboarding");
  var screenTransition = document.getElementById("screen-transition");
  var screenApp        = document.getElementById("screen-app");

  // ---------------------------------------------------------------------------
  // SCREEN 1 — Landing
  // ---------------------------------------------------------------------------

  // If the user has already completed onboarding (session still active), skip
  // straight to the chat interface.
  if (getStoredName()) {
    screenLanding.classList.add("fade-hidden");
    screenApp.classList.remove("fade-hidden");
    initChatApp(getStoredName());
  }

  var getStartedBtn = document.getElementById("get-started-btn");
  if (getStartedBtn) {
    getStartedBtn.addEventListener("click", function () {
      transitionTo(screenLanding, screenOnboarding);
    });
  }

  // ---------------------------------------------------------------------------
  // SCREEN 2 — Onboarding Form
  // ---------------------------------------------------------------------------

  var onboardingForm   = document.getElementById("onboarding-form");
  var nameInput        = document.getElementById("user-name");
  var emailInput       = document.getElementById("user-email");
  var disclaimerCheck  = document.getElementById("disclaimer-check");
  var onboardingError  = document.getElementById("onboarding-error");

  function showError(msg) {
    onboardingError.textContent = msg;
    onboardingError.classList.remove("fade-hidden");
  }

  function hideError() {
    onboardingError.classList.add("fade-hidden");
  }

  if (onboardingForm) {
    onboardingForm.addEventListener("submit", function (e) {
      e.preventDefault();
      hideError();

      var name = nameInput.value.trim();
      var email = emailInput.value.trim();

      if (!name) {
        showError("Please enter your name to continue.");
        nameInput.focus();
        return;
      }
      if (!disclaimerCheck.checked) {
        showError("Please acknowledge the disclaimer to continue.");
        return;
      }

      // Store in session
      sessionStorage.setItem(USER_KEY, name);
      if (email) sessionStorage.setItem(EMAIL_KEY, email);

      // Move to transition screen
      var thankYouMsg = document.getElementById("thank-you-msg");
      if (thankYouMsg) {
        thankYouMsg.textContent = "Thank you, " + name + " \uD83C\uDF38";
      }

      transitionTo(screenOnboarding, screenTransition, function () {
        var video = document.getElementById("intro-video");
        if (video) {
          video.play().catch(function () { /* autoplay may be blocked */ });
          video.addEventListener("ended", function () {
            launchApp(name);
          });
        }
      });
    });
  }

  // ---------------------------------------------------------------------------
  // SCREEN 3 — Transition + Video
  // ---------------------------------------------------------------------------

  var startChattingBtn = document.getElementById("start-chatting-btn");
  if (startChattingBtn) {
    startChattingBtn.addEventListener("click", function () {
      var name = getStoredName();
      launchApp(name);
    });
  }

  function launchApp(name) {
    transitionTo(screenTransition, screenApp, function () {
      initChatApp(name);
    });
  }

  // ---------------------------------------------------------------------------
  // SCREEN 4 — Main App initialisation
  // ---------------------------------------------------------------------------

  function initChatApp(name) {
    // Update header greeting
    var greetingEl = document.getElementById("header-greeting");
    if (greetingEl) {
      greetingEl.textContent = "Hi, " + name + " \uD83D\uDC4B";
    }

    // Auto-send welcome message (local only, not via API)
    var chatMessages = document.getElementById("chat-messages");
    if (chatMessages && chatMessages.children.length === 0) {
      var welcomeText = "Namaste " + name + " \uD83C\uDF38\n" +
        "I\u2019m here to answer your questions about HPV vaccination in India.\n" +
        "You can ask about safety, eligibility, side effects, or common myths.";
      appendMessage("assistant", welcomeText);
      renderPromptChips();
    }
  }

  var PROMPT_CHIPS = [
    "Is HPV vaccine safe?",
    "Who should take Hpv vaccine?",
    "Cervical cancer kya hai?",
    "Is HPV Vaccine free in India?",
    "Does HPV Vaccine it affect fertility?"
  ];

  function renderPromptChips() {
    var chipsContainer = document.getElementById("prompt-chips");
    if (!chipsContainer) return;
    chipsContainer.innerHTML = "";
    PROMPT_CHIPS.forEach(function (label) {
      var btn = document.createElement("button");
      btn.className = "prompt-chip";
      btn.type = "button";
      btn.textContent = label;
      btn.addEventListener("click", function () {
        var chatInput = document.getElementById("chat-input");
        if (chatInput) {
          chatInput.value = label;
          chatInput.focus();
          // Remove chips after selection
          chipsContainer.innerHTML = "";
        }
      });
      chipsContainer.appendChild(btn);
    });
  }

  // ---------------------------------------------------------------------------
  // Tab switching
  // ---------------------------------------------------------------------------

  var tabBtns = document.querySelectorAll(".tab-btn");
  var tabPanels = document.querySelectorAll(".tab-panel");

  tabBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = btn.dataset.tab;

      tabBtns.forEach(function (b) { b.classList.remove("active"); });
      tabPanels.forEach(function (p) { p.classList.remove("active"); p.classList.add("hidden"); });

      btn.classList.add("active");
      var panel = document.getElementById("tab-" + target);
      if (panel) {
        panel.classList.remove("hidden");
        panel.classList.add("active");
      }

      // Lazy-load Myth vs Fact content when that tab is first opened
      if (target === "myth" && panel && !panel.dataset.loaded) {
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
        var container = document.getElementById("myth-content");
        container.innerHTML = markdownToHtml(data.content || "No content available.");
        panel.dataset.loaded = "1";
      })
      .catch(function () {
        document.getElementById("myth-content").textContent = "Failed to load content.";
      });
  }

  /** Very simple Markdown → HTML converter for headings, bold, lists, paragraphs. */
  function markdownToHtml(md) {
    var lines = md.split("\n");
    var html = "";
    var inList = false;

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

  // ---------------------------------------------------------------------------
  // Chat
  // ---------------------------------------------------------------------------

  var chatMessages = document.getElementById("chat-messages");
  var chatForm = document.getElementById("chat-form");
  var chatInput = document.getElementById("chat-input");
  var clearBtn = document.getElementById("clear-btn");

  function appendMessage(role, text) {
    var div = document.createElement("div");
    div.className = "message " + (role === "user" ? "user-message" : "assistant-message");
    var bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = text;
    div.appendChild(bubble);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  function appendThinking() {
    var div = document.createElement("div");
    div.className = "message assistant-message";
    var inner = document.createElement("div");
    inner.className = "thinking";
    inner.textContent = "Thinking";
    div.appendChild(inner);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  if (chatForm) {
    chatForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = chatInput.value.trim();
      if (!text) return;

      // Hide prompt chips on first user message
      var chipsContainer = document.getElementById("prompt-chips");
      if (chipsContainer) chipsContainer.innerHTML = "";

      appendMessage("user", text);
      chatInput.value = "";

      var thinkingEl = appendThinking();

      fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      })
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          thinkingEl.remove();
          if (data.error) {
            appendMessage("assistant", "\u26A0\uFE0F " + data.error);
          } else {
            appendMessage("assistant", data.answer || "No answer returned.");
          }
        })
        .catch(function () {
          thinkingEl.remove();
          appendMessage("assistant", "\u26A0\uFE0F Network error. Please try again.");
        });
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener("click", function () {
      fetch("/api/clear-history", { method: "POST" })
        .then(function () {
          chatMessages.innerHTML = "";
          var name = getStoredName();
          if (name) {
            var welcomeText = "Namaste " + name + " \uD83C\uDF38\n" +
              "I\u2019m here to answer your questions about HPV vaccination in India.\n" +
              "You can ask about safety, eligibility, side effects, or common myths.";
            appendMessage("assistant", welcomeText);
            renderPromptChips();
          } else {
            appendMessage("assistant", "Conversation cleared. How can I help you today?");
          }
        });
    });
  }

  // ---------------------------------------------------------------------------
  // Eligibility Checker
  // ---------------------------------------------------------------------------

  var eligibilityForm = document.getElementById("eligibility-form");
  var eligibilityResult = document.getElementById("eligibility-result");

  if (eligibilityForm) {
    eligibilityForm.addEventListener("submit", function (e) {
      e.preventDefault();

      var age = parseInt(document.getElementById("age").value, 10);
      var gender = document.getElementById("gender").value;
      var alreadyVaccinated =
        document.querySelector("input[name='already_vaccinated']:checked").value === "Yes";
      var isPregnant =
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

          var html = "";
          if (data.eligible) {
            eligibilityResult.classList.add("eligible");
            html += "<strong>\u2705 Eligible for HPV Vaccination</strong><br/>";
          } else {
            eligibilityResult.classList.add("not-eligible");
            html += "<strong>\u2139\uFE0F Not currently recommended</strong><br/>";
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

          html += "<p><small>\u2695\uFE0F Always consult a qualified healthcare provider before making vaccination decisions.</small></p>";

          eligibilityResult.innerHTML = html;
        })
        .catch(function () {
          eligibilityResult.classList.remove("hidden");
          eligibilityResult.textContent = "\u26A0\uFE0F Could not check eligibility. Please try again.";
        });
    });
  }

  // ---------------------------------------------------------------------------
  // Sidebar
  // ---------------------------------------------------------------------------

  var sidebarToggle = document.getElementById("sidebar-toggle");
  var sidebar = document.getElementById("sidebar");
  var sidebarClose = document.getElementById("sidebar-close");

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function () {
      sidebar.classList.toggle("hidden");
    });
  }

  if (sidebarClose) {
    sidebarClose.addEventListener("click", function () {
      sidebar.classList.add("hidden");
    });
  }

  // ---------------------------------------------------------------------------
  // Document upload
  // ---------------------------------------------------------------------------

  var uploadForm = document.getElementById("upload-form");
  var uploadResult = document.getElementById("upload-result");

  if (uploadForm) {
    uploadForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var fileInput = document.getElementById("upload-file");
      if (!fileInput.files.length) {
        uploadResult.textContent = "Please select a file first.";
        return;
      }

      var formData = new FormData();
      formData.append("file", fileInput.files[0]);

      uploadResult.textContent = "Uploading\u2026";

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
          uploadResult.textContent = "\u26A0\uFE0F Upload failed. Please try again.";
        });
    });
  }
})();
