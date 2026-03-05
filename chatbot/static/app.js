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
  // Quiz — Test Your Knowledge
  // ---------------------------------------------------------------------------

  var quizState = {
    questions: [],
    current: 0,
    score: 0,
    answered: false
  };

  var startQuizBtn = document.getElementById("start-quiz-btn");
  var quizEntryPanel = document.getElementById("quiz-entry-panel");
  var quizPanel = document.getElementById("quiz-panel");
  var quizProgress = document.getElementById("quiz-progress");
  var quizBody = document.getElementById("quiz-body");

  /** Fisher-Yates shuffle — returns a new shuffled array. */
  function shuffleArray(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  if (startQuizBtn) {
    startQuizBtn.addEventListener("click", function () {
      fetch("/api/quiz")
        .then(function (resp) { return resp.json(); })
        .then(function (data) {
          if (!data.quiz_items || !data.quiz_items.length) {
            quizBody.innerHTML = "<p class='quiz-error'>Quiz data unavailable. Please try again later.</p>";
            quizEntryPanel.classList.add("hidden");
            quizPanel.classList.remove("hidden");
            return;
          }
          quizState.questions = shuffleArray(data.quiz_items);
          quizState.current = 0;
          quizState.score = 0;
          quizState.answered = false;
          quizEntryPanel.classList.add("hidden");
          quizPanel.classList.remove("hidden");
          renderQuizQuestion();
        })
        .catch(function () {
          quizEntryPanel.classList.add("hidden");
          quizPanel.classList.remove("hidden");
          quizBody.innerHTML = "<p class='quiz-error'>\u26A0\uFE0F Could not load quiz. Please try again.</p>";
        });
    });
  }

  function renderQuizQuestion() {
    var total = quizState.questions.length;
    var idx = quizState.current;
    var item = quizState.questions[idx];
    quizState.answered = false;

    // Progress bar
    quizProgress.innerHTML =
      "<span class='quiz-progress-text'>Question " + (idx + 1) + " of " + total + "</span>" +
      "<div class='quiz-progress-bar-wrap'><div class='quiz-progress-bar' style='width:" +
      Math.round(((idx + 1) / total) * 100) + "%'></div></div>" +
      "<span class='quiz-score-text'>Score: " + quizState.score + "</span>";

    var html = "";

    if (item.type === "flashcard") {
      html += "<div class='quiz-question-label'>Statement</div>";
      html += "<div class='quiz-question-text'>" + escHtml(item.statement) + "</div>";
    } else {
      html += "<div class='quiz-question-label'>Question</div>";
      html += "<div class='quiz-question-text'>" + escHtml(item.question) + "</div>";
    }

    html += "<div class='quiz-options' id='quiz-options'>";
    item.options.forEach(function (opt, i) {
      html += "<button class='quiz-option-btn' data-index='" + i + "' data-value='" +
        escHtml(opt) + "'>" + escHtml(opt) + "</button>";
    });
    html += "</div>";
    html += "<div id='quiz-feedback' class='quiz-feedback hidden'></div>";
    html += "<div id='quiz-nav' class='quiz-nav hidden'></div>";

    quizBody.innerHTML = html;

    // Attach option click handlers
    var optionBtns = quizBody.querySelectorAll(".quiz-option-btn");
    optionBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (quizState.answered) return;
        handleQuizAnswer(btn.getAttribute("data-value"), item);
      });
    });
  }

  function handleQuizAnswer(selected, item) {
    quizState.answered = true;
    var isCorrect = selected === item.correct_answer;
    if (isCorrect) quizState.score += 1;

    // Highlight selected and correct options
    var optionBtns = quizBody.querySelectorAll(".quiz-option-btn");
    optionBtns.forEach(function (btn) {
      var val = btn.getAttribute("data-value");
      btn.disabled = true;
      if (val === item.correct_answer) {
        btn.classList.add("quiz-option-correct");
      } else if (val === selected && !isCorrect) {
        btn.classList.add("quiz-option-wrong");
      }
    });

    // Feedback
    var feedbackEl = document.getElementById("quiz-feedback");
    var feedbackHtml = "";

    if (isCorrect) {
      feedbackHtml += "<div class='quiz-result quiz-result-correct'>";
      feedbackHtml += "<span class='quiz-result-icon'>\uD83C\uDF89</span> <strong>Correct!</strong>";
      feedbackHtml += "</div>";
    } else {
      feedbackHtml += "<div class='quiz-result quiz-result-wrong'>";
      feedbackHtml += "<span class='quiz-result-icon'>\uD83D\uDC4F</span> <strong>Not quite — but great attempt!</strong>";
      feedbackHtml += "<div class='quiz-correct-answer'>Correct answer: <em>" + escHtml(item.correct_answer) + "</em></div>";
      feedbackHtml += "</div>";
    }

    if (item.explanation) {
      feedbackHtml += "<div class='quiz-explanation'><strong>Explanation:</strong> " + escHtml(item.explanation) + "</div>";
    }

    if (isCorrect && item.encouragement_message) {
      feedbackHtml += "<div class='quiz-encouragement'>\uD83C\uDF1F " + escHtml(item.encouragement_message) + "</div>";
    }

    feedbackEl.innerHTML = feedbackHtml;
    feedbackEl.classList.remove("hidden");

    // Navigation button
    var navEl = document.getElementById("quiz-nav");
    var isLast = quizState.current >= quizState.questions.length - 1;
    if (isLast) {
      navEl.innerHTML = "<button class='quiz-next-btn' id='quiz-finish-btn'>See My Results \u2192</button>";
      navEl.classList.remove("hidden");
      document.getElementById("quiz-finish-btn").addEventListener("click", showQuizResults);
    } else {
      navEl.innerHTML = "<button class='quiz-next-btn' id='quiz-next-btn'>Next Question \u2192</button>";
      navEl.classList.remove("hidden");
      document.getElementById("quiz-next-btn").addEventListener("click", function () {
        quizState.current += 1;
        renderQuizQuestion();
      });
    }
  }

  function showQuizResults() {
    var total = quizState.questions.length;
    var score = quizState.score;
    var pct = Math.round((score / total) * 100);

    var msg = "";
    if (pct === 100) {
      msg = "\uD83C\uDFC6 Outstanding! You got a perfect score!";
    } else if (pct >= 75) {
      msg = "\uD83C\uDF1F Great work! You\u2019re well-informed about HPV vaccination.";
    } else if (pct >= 50) {
      msg = "\uD83D\uDCAA Nice effort! Keep learning \u2014 every fact you know helps protect your health.";
    } else {
      msg = "\uD83C\uDF31 You\u2019re learning important health facts. Consider exploring the Myths & Facts section to learn more.";
    }

    quizBody.innerHTML =
      "<div class='quiz-results'>" +
      "<div class='quiz-results-score'>" + score + "<span class='quiz-results-total'> / " + total + "</span></div>" +
      "<div class='quiz-results-pct'>" + pct + "% correct</div>" +
      "<div class='quiz-results-msg'>" + msg + "</div>" +
      "<p class='quiz-results-disclaimer'>\u2695\uFE0F This quiz is for educational purposes only and does not constitute medical advice.</p>" +
      "<button class='quiz-next-btn quiz-restart-btn' id='quiz-restart-btn'>\uD83D\uDD04 Try Again</button>" +
      "</div>";

    quizProgress.innerHTML =
      "<span class='quiz-progress-text'>Quiz Complete!</span>" +
      "<div class='quiz-progress-bar-wrap'><div class='quiz-progress-bar' style='width:100%'></div></div>" +
      "<span class='quiz-score-text'>Final Score: " + score + "/" + total + "</span>";

    document.getElementById("quiz-restart-btn").addEventListener("click", function () {
      quizState.questions = shuffleArray(quizState.questions);
      quizState.current = 0;
      quizState.score = 0;
      quizState.answered = false;
      renderQuizQuestion();
    });
  }

})();
