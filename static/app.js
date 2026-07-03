const data = window.cyberguardData || {};

const palette = {
  "Harassment": "#ff4d8d",
  "Hate Speech": "#a855f7",
  "Threat": "#ff6b35",
  "Insult": "#facc15",
  "Exclusion": "#38bdf8",
  "Safe": "#22c55e",
  "Critical": "#ff2e63",
  "High": "#ff7a18",
  "Medium": "#facc15",
  "Low": "#a3e635"
};

function setupCanvas(canvas) {
  if (!canvas) return null;
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * ratio;
  canvas.height = Number(canvas.getAttribute("height")) * ratio;
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  return { ctx, width: rect.width, height: Number(canvas.getAttribute("height")) };
}

function drawLabel(ctx, text, x, y, color = "#d7e5ff", size = 12) {
  ctx.fillStyle = color;
  ctx.font = `${size}px Arial`;
  ctx.fillText(text, x, y);
}

function drawDonut() {
  const canvas = document.getElementById("categoryChart");
  const setup = setupCanvas(canvas);
  if (!setup) return;
  const { ctx, width, height } = setup;
  const order = ["Harassment", "Hate Speech", "Threat", "Insult", "Exclusion", "Safe"];
  const entries = order.map((label) => [label, (data.categoryCounts || {})[label] || 0]);
  const total = entries.reduce((sum, [, value]) => sum + value, 0);
  const cx = width * 0.31;
  const cy = height * 0.5;
  const radius = Math.min(width, height) * 0.28;
  let start = -Math.PI / 2;

  ctx.clearRect(0, 0, width, height);
  if (!total) {
    drawLabel(ctx, "No data yet", 24, 40, "#8ca3c7", 14);
  } else {
    entries.forEach(([label, value]) => {
      if (!value) return;
      const angle = (value / total) * Math.PI * 2;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, start, start + angle);
      ctx.lineWidth = 24;
      ctx.strokeStyle = palette[label] || "#8b5cf6";
      ctx.shadowColor = ctx.strokeStyle;
      ctx.shadowBlur = 18;
      ctx.stroke();
      start += angle;
    });

    ctx.shadowBlur = 0;
    drawLabel(ctx, `${total}`, cx - 10, cy + 4, "#ffffff", 24);
    drawLabel(ctx, "logs", cx - 12, cy + 24, "#8ca3c7", 12);
  }

  entries.forEach(([label, value], index) => {
    const y = 34 + index * 28;
    ctx.fillStyle = palette[label] || "#8b5cf6";
    ctx.fillRect(width * 0.6, y - 10, 12, 12);
    drawLabel(ctx, `${label} ${value}`, width * 0.6 + 22, y, "#d7e5ff", 13);
  });
}

function drawDangerBars() {
  const canvas = document.getElementById("dangerChart");
  const setup = setupCanvas(canvas);
  if (!setup) return;
  const { ctx, width, height } = setup;
  const levels = ["Critical", "High", "Medium", "Low", "Safe"];
  const counts = data.dangerCounts || {};
  const max = Math.max(1, ...levels.map((level) => counts[level] || 0));
  const left = 24;
  const top = 28;
  const gap = 14;
  const barHeight = 20;

  ctx.clearRect(0, 0, width, height);
  levels.forEach((level, index) => {
    const y = top + index * (barHeight + gap);
    const value = counts[level] || 0;
    const barWidth = ((width - 150) * value) / max;
    drawLabel(ctx, level, left, y + 15, "#d7e5ff", 13);
    ctx.fillStyle = "rgba(255,255,255,0.08)";
    ctx.fillRect(96, y, width - 135, barHeight);
    ctx.fillStyle = palette[level];
    ctx.shadowColor = palette[level];
    ctx.shadowBlur = 12;
    ctx.fillRect(96, y, barWidth, barHeight);
    ctx.shadowBlur = 0;
    drawLabel(ctx, String(value), width - 28, y + 15, "#ffffff", 13);
  });
}

function drawWeekly() {
  const canvas = document.getElementById("weeklyChart");
  const setup = setupCanvas(canvas);
  if (!setup) return;
  const { ctx, width, height } = setup;
  const weekly = data.weekly || [];
  const categories = ["Harassment", "Hate Speech", "Threat", "Insult", "Exclusion"];
  const left = 44;
  const bottom = height - 36;
  const chartHeight = height - 72;
  const slot = (width - left - 20) / Math.max(weekly.length, 1);
  const barWidth = Math.min(42, slot * 0.54);
  const max = Math.max(
    1,
    ...weekly.map((day) => categories.reduce((sum, category) => sum + (day[category] || 0), 0))
  );

  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(255,255,255,0.1)";
  ctx.beginPath();
  ctx.moveTo(left, 24);
  ctx.lineTo(left, bottom);
  ctx.lineTo(width - 10, bottom);
  ctx.stroke();

  weekly.forEach((day, index) => {
    let y = bottom;
    const x = left + index * slot + slot * 0.5 - barWidth * 0.5;
    categories.forEach((category) => {
      const value = day[category] || 0;
      const h = (value / max) * chartHeight;
      if (h > 0) {
        ctx.fillStyle = palette[category];
        ctx.fillRect(x, y - h, barWidth, h);
        y -= h;
      }
    });
    drawLabel(ctx, day.day, x + 3, bottom + 22, "#8ca3c7", 12);
  });

  categories.forEach((category, index) => {
    const x = left + index * 130;
    const y = 16;
    ctx.fillStyle = palette[category];
    ctx.fillRect(x, y - 9, 10, 10);
    drawLabel(ctx, category, x + 16, y, "#d7e5ff", 12);
  });
}

function setupWeeklyTooltip() {
  const canvas = document.getElementById("weeklyChart");
  const tooltip = document.getElementById("chartTooltip");
  if (!canvas || !tooltip) return;

  canvas.addEventListener("mousemove", (event) => {
    const weekly = data.weekly || [];
    if (!weekly.length) return;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const slot = (rect.width - 64) / Math.max(weekly.length, 1);
    const index = Math.floor((x - 44) / slot);
    const day = weekly[index];
    if (!day) {
      tooltip.hidden = true;
      return;
    }
    const categories = ["Harassment", "Hate Speech", "Threat", "Insult", "Exclusion"];
    tooltip.innerHTML = `<strong>${day.day}</strong><br>${categories
      .map((category) => `${category}: ${day[category] || 0}`)
      .join("<br>")}`;
    tooltip.style.left = `${Math.min(rect.width - 170, Math.max(8, x + 12))}px`;
    tooltip.style.top = `${Math.max(12, event.clientY - rect.top - 18)}px`;
    tooltip.hidden = false;
  });

  canvas.addEventListener("mouseleave", () => {
    tooltip.hidden = true;
  });
}

function setupFilters() {
  const rows = Array.from(document.querySelectorAll(".message-row"));
  const count = document.getElementById("visibleCount");
  const activeFilter = document.getElementById("activeFilter");
  const filteredEmpty = document.getElementById("filteredEmpty");
  if (!rows.length) return;

  const state = {
    quick: "all",
    danger: new Set(),
    category: new Set()
  };

  function applyFilters() {
    let visible = 0;
    rows.forEach((row) => {
      const isSafe = row.dataset.danger === "Safe";
      const quickMatch =
        state.quick === "all" ||
        (state.quick === "bullying" && !isSafe) ||
        (state.quick === "safe" && isSafe) ||
        row.dataset.danger === state.quick;
      const dangerMatch = !state.danger.size || state.danger.has(row.dataset.danger);
      const categoryMatch = !state.category.size || state.category.has(row.dataset.category);
      const show = quickMatch && dangerMatch && categoryMatch;
      row.hidden = !show;
      if (show) visible += 1;
    });

    if (count) count.textContent = visible;
    const activeCount = (state.quick === "all" ? 0 : 1) + state.danger.size + state.category.size;
    if (activeFilter) activeFilter.textContent = `${activeCount} active filter${activeCount === 1 ? "" : "s"}`;
    if (filteredEmpty) filteredEmpty.hidden = visible !== 0;
  }

  document.querySelectorAll(".filter").forEach((button) => {
    button.addEventListener("click", () => {
      const group = button.dataset.filterGroup;
      const value = button.dataset.filterValue;
      if (state[group].has(value)) {
        state[group].delete(value);
        button.classList.remove("active");
      } else {
        state[group].add(value);
        button.classList.add("active");
      }
      applyFilters();
    });
  });

  document.querySelectorAll(".quick-filter").forEach((button) => {
    button.addEventListener("click", () => {
      state.quick = button.dataset.quickFilter;
      document.querySelectorAll(".quick-filter").forEach((item) => {
        item.classList.toggle("active", item === button);
      });
      applyFilters();
    });
  });

  const clear = document.getElementById("clearFilters");
  if (clear) {
    clear.addEventListener("click", () => {
      state.quick = "all";
      state.danger.clear();
      state.category.clear();
      document.querySelectorAll(".filter").forEach((button) => button.classList.remove("active"));
      document.querySelectorAll(".quick-filter").forEach((button) => {
        button.classList.toggle("active", button.dataset.quickFilter === "all");
      });
      applyFilters();
    });
  }

  applyFilters();
}

function exportPdf() {
  const button = document.getElementById("exportPdf");
  if (!button) return;
  button.addEventListener("click", () => {
    if (!(data.logs || []).length) {
      window.alert("No data available to export");
      return;
    }

    const jsPDF = window.jspdf && window.jspdf.jsPDF;
    if (!jsPDF) {
      window.print();
      return;
    }

    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const today = data.reportDate || new Date().toISOString().slice(0, 10);
    let y = 48;
    doc.setFillColor(8, 13, 34);
    doc.rect(0, 0, 595, 842, "F");
    doc.setTextColor(45, 212, 191);
    doc.setFontSize(22);
    doc.text("CyberGuard AI Report", 42, y);
    doc.setFontSize(10);
    doc.setTextColor(215, 229, 255);
    doc.text(`Generated ${today}`, 42, y + 20);

    y += 62;
    const stats = data.stats || {};
    [["Total", stats.total], ["Flagged", stats.flagged], ["Safe", stats.safe], ["Critical", stats.critical]].forEach((item, index) => {
      const x = 42 + index * 128;
      doc.setFillColor(15, 24, 54);
      doc.roundedRect(x, y, 112, 56, 8, 8, "F");
      doc.setTextColor(140, 163, 199);
      doc.setFontSize(9);
      doc.text(item[0], x + 12, y + 19);
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(18);
      doc.text(String(item[1] || 0), x + 12, y + 43);
    });

    y += 88;
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(14);
    doc.text("Category Breakdown", 42, y);
    y += 18;
    Object.entries(data.categoryCounts || {}).forEach(([label, value]) => {
      const width = Math.min(260, Number(value) * 32);
      const color = hexToRgb(palette[label] || "#2dd4bf");
      doc.setTextColor(215, 229, 255);
      doc.setFontSize(10);
      doc.text(`${label}: ${value}`, 42, y);
      doc.setFillColor(color.r, color.g, color.b);
      doc.rect(180, y - 9, Math.max(8, width), 8, "F");
      y += 18;
    });

    y += 22;
    doc.setFontSize(14);
    doc.setTextColor(255, 255, 255);
    doc.text("Complete Messages Table", 42, y);
    y += 20;
    doc.setFontSize(8);
    (data.logs || []).forEach((item) => {
      if (y > 780) {
        doc.addPage();
        doc.setFillColor(8, 13, 34);
        doc.rect(0, 0, 595, 842, "F");
        y = 44;
      }
      const color = hexToRgb(palette[item.danger_level] || "#2dd4bf");
      doc.setFillColor(color.r, color.g, color.b);
      doc.rect(42, y - 8, 8, 28, "F");
      doc.setTextColor(color.r, color.g, color.b);
      doc.text(`${item.danger_level} - ${item.category_label} - ${item.confidence}%`, 58, y);
      doc.setTextColor(215, 229, 255);
      doc.text(doc.splitTextToSize(item.message, 464), 58, y + 12);
      y += 38;
    });

    doc.save(`cyberguard-report-${today}.pdf`);
  });
}

function hexToRgb(hex) {
  const value = hex.replace("#", "");
  return {
    r: parseInt(value.slice(0, 2), 16),
    g: parseInt(value.slice(2, 4), 16),
    b: parseInt(value.slice(4, 6), 16)
  };
}

function setupTextCounter() {
  const textarea = document.getElementById("message");
  const counter = document.getElementById("charCount");
  if (!textarea || !counter) return;
  textarea.addEventListener("input", () => {
    counter.textContent = textarea.value.length;
  });
}

function setupSourcePicker() {
  const form = document.querySelector("form.analyzer-card");
  const typeInput = document.getElementById("sourceType");
  const tabs = Array.from(document.querySelectorAll(".source-tab"));
  const panels = Array.from(document.querySelectorAll("[data-source-panel]"));
  const analyzeButton = document.getElementById("analyzeButton");
  const fileInput = document.getElementById("file");
  const fileName = document.getElementById("fileName");
  const extractedText = document.getElementById("extractedText");
  if (!typeInput || !tabs.length) return;

  const labels = { text: "Analyze Text", url: "Analyze Link", file: "Analyze File" };
  function selectSource(source) {
    typeInput.value = source;
    tabs.forEach((tab) => {
      const selected = tab.dataset.source === source;
      tab.classList.toggle("active", selected);
      tab.setAttribute("aria-selected", String(selected));
    });
    panels.forEach((panel) => {
      const selected = panel.dataset.sourcePanel === source;
      panel.hidden = !selected;
      panel.classList.toggle("active", selected);
    });
    if (analyzeButton) analyzeButton.textContent = labels[source] || "Analyze";
  }

  tabs.forEach((tab) => tab.addEventListener("click", () => selectSource(tab.dataset.source)));
  if (fileInput && fileName) {
    fileInput.addEventListener("change", () => {
      fileName.textContent = fileInput.files[0]?.name || "No file selected";
      if (extractedText) extractedText.value = "";
    });
  }

  if (form && fileInput && extractedText && analyzeButton) {
    let submittingAfterOcr = false;
    form.addEventListener("submit", async (event) => {
      const file = fileInput.files[0];
      const isImage = file && /\.(png|jpe?g|webp|bmp)$/i.test(file.name);
      if (submittingAfterOcr || typeInput.value !== "file" || !isImage) return;

      event.preventDefault();
      if (!window.Tesseract) {
        showToast("Image OCR could not load. Check your internet connection.");
        return;
      }

      analyzeButton.disabled = true;
      analyzeButton.textContent = "Reading image...";
      try {
        const result = await window.Tesseract.recognize(file, "eng", {
          logger: ({ status, progress }) => {
            if (status === "recognizing text") {
              analyzeButton.textContent = `Reading image ${Math.round(progress * 100)}%`;
            }
          }
        });
        const text = (result.data.text || "").replace(/\s+/g, " ").trim();
        if (!text) {
          showToast("No readable text was found in this image.");
          analyzeButton.disabled = false;
          analyzeButton.textContent = "Analyze File";
          return;
        }
        extractedText.value = text.slice(0, 5000);
        submittingAfterOcr = true;
        form.submit();
      } catch (error) {
        console.error("Browser image OCR failed", error);
        showToast("The image could not be read. Try a clearer image.");
        analyzeButton.disabled = false;
        analyzeButton.textContent = "Analyze File";
      }
    });
  }
  selectSource(typeInput.value || "text");
}

function setupExampleChips() {
  const textarea = document.getElementById("message");
  const counter = document.getElementById("charCount");
  if (!textarea) return;

  document.querySelectorAll(".example-chip").forEach((button) => {
    button.addEventListener("click", () => {
      textarea.value = button.dataset.example || "";
      if (counter) counter.textContent = textarea.value.length;
      textarea.focus();
      textarea.dispatchEvent(new Event("input", { bubbles: true }));
      showToast(`${button.querySelector("strong")?.textContent || "Example"} pasted`);
    });
  });
}

function setupCriticalAlert() {
  const banner = document.querySelector("[data-critical-alert='true']");
  if (!banner) return;

  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) return;

  try {
    const context = new AudioContext();
    const now = context.currentTime;
    [0, 0.28, 0.56].forEach((offset) => {
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(620, now + offset);
      oscillator.frequency.exponentialRampToValueAtTime(920, now + offset + 0.12);
      gain.gain.setValueAtTime(0.0001, now + offset);
      gain.gain.exponentialRampToValueAtTime(0.16, now + offset + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + 0.16);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start(now + offset);
      oscillator.stop(now + offset + 0.18);
    });
  } catch (error) {
    // Browsers may block audio if the page was not opened from a user gesture.
  }
}

function setupShareButtons() {
  document.querySelectorAll(".share-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const source = button.closest(".result-actions")?.querySelector(".share-summary-source");
      const summary = source?.value || "";
      try {
        await navigator.clipboard.writeText(summary);
        showToast("Result summary copied");
      } catch (error) {
        const fallback = document.createElement("textarea");
        fallback.value = summary;
        document.body.appendChild(fallback);
        fallback.select();
        document.execCommand("copy");
        fallback.remove();
        showToast("Result summary copied");
      }
    });
  });
}

function setupAwarenessQuiz() {
  const start = document.getElementById("startQuiz");
  const play = document.getElementById("quizPlay");
  const startPanel = document.getElementById("quizStart");
  const resultPanel = document.getElementById("quizResult");
  const questionEl = document.getElementById("quizQuestion");
  const optionsEl = document.getElementById("quizOptions");
  const feedbackEl = document.getElementById("quizFeedback");
  const next = document.getElementById("nextQuiz");
  const counter = document.getElementById("quizCounter");
  const scoreEl = document.getElementById("quizScore");
  const bar = document.getElementById("quizBar");
  const restart = document.getElementById("restartQuiz");
  const finalText = document.getElementById("quizFinalText");
  if (!start || !play) return;

  const questions = [
    {
      question: "What should you do first if someone sends a threatening message?",
      options: ["Reply angrily", "Save evidence and tell a trusted adult", "Delete everything", "Forward it to friends"],
      answer: 1,
      feedback: "Correct. Save screenshots and report the threat to a trusted adult or school authority."
    },
    {
      question: "Which Indian helpline can be used to report cybercrime support issues?",
      options: ["1930", "1008", "4040", "1500"],
      answer: 0,
      feedback: "Correct. 1930 is the cybercrime helpline linked with cybercrime reporting support."
    },
    {
      question: "Which portal is used in India for online cybercrime complaints?",
      options: ["passportindia.gov.in", "cybercrime.gov.in", "uidai.gov.in", "indiaresults.com"],
      answer: 1,
      feedback: "Correct. cybercrime.gov.in is the official National Cyber Crime Reporting Portal."
    },
    {
      question: "What is exclusion in cyberbullying?",
      options: ["Helping someone join a group", "Leaving someone out to isolate them", "Changing a password", "Posting study notes"],
      answer: 1,
      feedback: "Correct. Exclusion means deliberately isolating someone from groups or online spaces."
    },
    {
      question: "What should you avoid doing when bullied online?",
      options: ["Taking screenshots", "Blocking the account", "Sharing private details publicly", "Reporting the message"],
      answer: 2,
      feedback: "Correct. Do not expose private details or escalate the situation publicly."
    },
    {
      question: "Which number is Childline India?",
      options: ["1098", "181", "14416", "112"],
      answer: 0,
      feedback: "Correct. Childline India is 1098."
    },
    {
      question: "Why are screenshots important?",
      options: ["They make the phone faster", "They are evidence for reporting", "They hide the message", "They delete the account"],
      answer: 1,
      feedback: "Correct. Screenshots help teachers, platforms, parents, and police understand what happened."
    },
    {
      question: "Which danger level means no bullying indicators were detected?",
      options: ["Critical", "High", "Low", "Safe"],
      answer: 3,
      feedback: "Correct. Safe means the message does not show harmful bullying indicators."
    },
    {
      question: "Who can a student talk to at school?",
      options: ["Only strangers online", "A teacher or school counselor", "Nobody", "Only the bully"],
      answer: 1,
      feedback: "Correct. A teacher, school counselor, parent, or trusted adult can help."
    },
    {
      question: "What is a healthy bystander action?",
      options: ["Join the bullying", "Ignore the victim forever", "Support the target and report abuse", "Make memes about it"],
      answer: 2,
      feedback: "Correct. Supportive bystanders can reduce harm and help the target get support."
    }
  ];

  let current = 0;
  let score = 0;
  let answered = false;

  function showQuestion() {
    answered = false;
    const item = questions[current];
    counter.textContent = `Question ${current + 1} of ${questions.length}`;
    scoreEl.textContent = `Score: ${score}`;
    bar.style.width = `${(current / questions.length) * 100}%`;
    questionEl.textContent = item.question;
    feedbackEl.hidden = true;
    next.hidden = true;
    optionsEl.innerHTML = "";
    item.options.forEach((option, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "quiz-option";
      button.textContent = option;
      button.addEventListener("click", () => answerQuestion(button, index));
      optionsEl.appendChild(button);
    });
  }

  function answerQuestion(button, index) {
    if (answered) return;
    answered = true;
    const item = questions[current];
    const correct = index === item.answer;
    if (correct) score += 1;
    optionsEl.querySelectorAll(".quiz-option").forEach((option, optionIndex) => {
      option.disabled = true;
      option.classList.toggle("correct", optionIndex === item.answer);
      option.classList.toggle("wrong", option === button && !correct);
    });
    feedbackEl.textContent = correct ? item.feedback : `Not quite. ${item.feedback}`;
    feedbackEl.classList.toggle("good", correct);
    feedbackEl.classList.toggle("bad", !correct);
    feedbackEl.hidden = false;
    next.hidden = false;
    scoreEl.textContent = `Score: ${score}`;
  }

  function finishQuiz() {
    play.hidden = true;
    resultPanel.hidden = false;
    bar.style.width = "100%";
    finalText.textContent = `You scored ${score} out of ${questions.length}. ${score >= 8 ? "Excellent awareness." : "Review the safety sections and try again."}`;
  }

  start.addEventListener("click", () => {
    current = 0;
    score = 0;
    startPanel.hidden = true;
    resultPanel.hidden = true;
    play.hidden = false;
    showQuestion();
  });

  next.addEventListener("click", () => {
    current += 1;
    if (current >= questions.length) {
      finishQuiz();
    } else {
      showQuestion();
    }
  });

  restart.addEventListener("click", () => {
    current = 0;
    score = 0;
    resultPanel.hidden = true;
    play.hidden = false;
    showQuestion();
  });
}

function setupIncidentReport() {
  const printButton = document.getElementById("printIncident");
  if (!printButton) return;
  printButton.addEventListener("click", () => {
    document.body.classList.add("printing-incident");
    window.print();
    window.setTimeout(() => document.body.classList.remove("printing-incident"), 500);
  });
}

function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.hidden = false;
  toast.classList.add("show");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => {
    toast.classList.remove("show");
    toast.hidden = true;
  }, 2200);
}

drawDonut();
drawDangerBars();
drawWeekly();
setupWeeklyTooltip();
setupFilters();
exportPdf();
setupTextCounter();
setupSourcePicker();
setupExampleChips();
setupCriticalAlert();
setupShareButtons();
setupAwarenessQuiz();
setupIncidentReport();

window.addEventListener("resize", () => {
  drawDonut();
  drawDangerBars();
  drawWeekly();
});
