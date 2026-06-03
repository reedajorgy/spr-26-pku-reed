const LEGACY_LOCALE_KEY = "flashcardLocale";
const STUDY_CARD_LIMIT = 500;

const TRANSLATION_FIELD_LABELS = {
  use_case: "Usage",
  explanation: "Explanation",
  meaning: "Meaning",
  usage_note: "Usage note",
  example_en: "Example translation",
  structure: "Structure",
  note: "Note",
};

const GRADE_LABELS = {
  again: "Again",
  hard: "Hard",
  good: "Good",
  easy: "Easy",
};

let studyPrefsConfig = null;
let studySettings = { mother_locale: "en", auto_reveal_on_answer: true };
let progressStore = { sessions: {} };
let deckLabelById = {};
let cardIndex = 0;
let cardRecords = [];
let showAnswer = false;
let revealed = {
  hanzi: false,
  pinyin: false,
  gloss: false,
  example: false,
};

const localeSelect = document.getElementById("locale-select");
const courseSelect = document.getElementById("course-select");
const aspectSelect = document.getElementById("aspect-select");
const deckSelect = document.getElementById("deck-select");
const chapterSelect = document.getElementById("chapter-select");
const studyCardHost = document.getElementById("study-card-host");
const cardList = document.getElementById("card-list");
const studyPosition = document.getElementById("study-position");
const hierarchyTree = document.getElementById("hierarchy-tree");
const hierarchyTotal = document.getElementById("hierarchy-total");
const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");
const showAnswerBtn = document.getElementById("show-answer-btn");
const autoRevealCheckbox = document.getElementById("auto-reveal-checkbox");
const listModeCheckbox = document.getElementById("list-mode-checkbox");
const listPreviewSection = document.getElementById("list-preview-section");
const progressBarFill = document.getElementById("progress-bar-fill");
const progressStats = document.getElementById("progress-stats");
const gradeBreakdown = document.getElementById("grade-breakdown");
const gradePanel = document.getElementById("grade-panel");
const setupPanel = document.getElementById("setup-panel");
const setupSummaryHint = document.getElementById("setup-summary-hint");
const resetProgressBtn = document.getElementById("reset-progress-btn");

function settingsStorageKey() {
  return studyPrefsConfig?.study_settings_key || "spr26_study_settings";
}

function localeStorageKey() {
  return studyPrefsConfig?.locale_storage_key || "spr26_mother_locale";
}

function progressStorageKey() {
  return studyPrefsConfig?.progress_storage_key || "spr26_study_progress";
}

function aspectLabel(aspectId) {
  const fromConfig = studyPrefsConfig?.aspect_labels?.[aspectId];
  if (fromConfig) {
    return fromConfig;
  }
  return aspectId.replace(/_/g, " ");
}

function loadStudySettings() {
  try {
    const raw = localStorage.getItem(settingsStorageKey());
    if (raw) {
      studySettings = { ...studySettings, ...JSON.parse(raw) };
    }
  } catch {
    /* ignore */
  }
  const legacy = localStorage.getItem(LEGACY_LOCALE_KEY);
  if (legacy && !studySettings.mother_locale) {
    studySettings.mother_locale = legacy;
  }
  const localeOnly = localStorage.getItem(localeStorageKey());
  if (localeOnly) {
    studySettings.mother_locale = localeOnly;
  }
}

function loadProgressStore() {
  try {
    const raw = localStorage.getItem(progressStorageKey());
    if (raw) {
      progressStore = JSON.parse(raw);
    }
  } catch {
    /* ignore */
  }
  if (!progressStore.sessions) {
    progressStore = { sessions: {} };
  }
}

function saveProgressStore() {
  try {
    localStorage.setItem(progressStorageKey(), JSON.stringify(progressStore));
  } catch {
    /* ignore */
  }
}

function sessionKey() {
  return [
    courseSelect.value || "*",
    aspectSelect.value || "*",
    deckSelect.value || "*",
    chapterSelect.value || "*",
    getLocale(),
  ].join("|");
}

function getSessionProgress() {
  const key = sessionKey();
  if (!progressStore.sessions[key]) {
    progressStore.sessions[key] = {
      cardIndex: 0,
      grades: {},
      updatedAt: null,
    };
  }
  return { key, data: progressStore.sessions[key] };
}

function cardStableId(record) {
  const joinPart = Object.entries(record.join || {})
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([joinKey, joinValue]) => `${joinKey}=${joinValue}`)
    .join("|");
  return `${record.deck}::${joinPart}`;
}

function deckDisplayLabel(deckId) {
  return deckLabelById[deckId] || deckId;
}

function friendlyTranslationKey(key) {
  if (TRANSLATION_FIELD_LABELS[key]) {
    return TRANSLATION_FIELD_LABELS[key];
  }
  const exampleMatch = key.match(/^example_(\d+)_en$/);
  if (exampleMatch) {
    return `Example ${exampleMatch[1]} (translation)`;
  }
  const exampleCnMatch = key.match(/^example_(\d+)$/);
  if (exampleCnMatch) {
    return `Example ${exampleCnMatch[1]}`;
  }
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function saveStudySettings() {
  studySettings.mother_locale = localeSelect.value;
  studySettings.auto_reveal_on_answer = autoRevealCheckbox.checked;
  studySettings.course = courseSelect.value;
  studySettings.aspect = aspectSelect.value;
  studySettings.deck = deckSelect.value;
  studySettings.chapter = chapterSelect.value;
  studySettings.list_mode = listModeCheckbox.checked;
  if (setupPanel) {
    studySettings.setup_open = setupPanel.open;
  }
  try {
    localStorage.setItem(settingsStorageKey(), JSON.stringify(studySettings));
    localStorage.setItem(localeStorageKey(), studySettings.mother_locale);
    localStorage.setItem(LEGACY_LOCALE_KEY, studySettings.mother_locale);
  } catch {
    /* ignore */
  }
}

function setSelectIfValid(selectElement, value) {
  if (!value) {
    return;
  }
  const hasOption = Array.from(selectElement.options).some(
    (option) => option.value === value,
  );
  if (hasOption) {
    selectElement.value = value;
  }
}

function restoreFilterControls() {
  setSelectIfValid(courseSelect, studySettings.course);
  setSelectIfValid(aspectSelect, studySettings.aspect);
  setSelectIfValid(deckSelect, studySettings.deck);
  setSelectIfValid(chapterSelect, studySettings.chapter);
  autoRevealCheckbox.checked = studySettings.auto_reveal_on_answer !== false;
  listModeCheckbox.checked = Boolean(studySettings.list_mode);
  listPreviewSection.classList.toggle("hidden", !listModeCheckbox.checked);
}

function getLocale() {
  return localeSelect.value || studySettings.mother_locale || "en";
}

function motherLanguageLabel() {
  const selected = localeSelect.selectedOptions[0]?.textContent?.trim();
  if (selected) {
    return selected;
  }
  const match = studyPrefsConfig?.locales?.find((item) => item.code === getLocale());
  return match?.label || getLocale();
}

function localeBadgeHtml() {
  if (getLocale() === "en") {
    return "";
  }
  return `<span class="locale-badge">${escapeHtml(motherLanguageLabel())}</span>`;
}

const LATIN_SCRIPT_LOCALES = new Set(["en", "fr", "es"]);

function cardLocaleCode(record) {
  return (record.locale || getLocale() || "en").toLowerCase();
}

function localeScriptFontClass(localeCode) {
  if (LATIN_SCRIPT_LOCALES.has(localeCode)) {
    return "font-latin";
  }
  return `font-script-${localeCode}`;
}

function cardShellOpenTag(record) {
  const localeCode = cardLocaleCode(record);
  const fontClass = localeScriptFontClass(localeCode);
  return `<div class="card-shell ${fontClass}" lang="${escapeHtml(localeCode)}" data-locale="${escapeHtml(localeCode)}">`;
}

function masterExampleLineClass(key) {
  if (/(_en|English)/i.test(key)) {
    return "meta-line text-mother";
  }
  return "meta-line text-zh";
}

const VOCAB_OVERLAY_TO_ANKI = {
  meaning: "English",
  example_en: "ExampleEN",
  usage_note: "UsageNote",
};

function vocabTranslation(record, overlayField) {
  const translations = record.translations || {};
  if (translations[overlayField]) {
    return translations[overlayField];
  }
  const ankiField = VOCAB_OVERLAY_TO_ANKI[overlayField];
  const anki = record.anki || {};
  if (ankiField && anki[ankiField]) {
    return anki[ankiField];
  }
  return "";
}

function resetRevealState() {
  showAnswer = false;
  revealed = { hanzi: false, pinyin: false, gloss: false, example: false };
  showAnswerBtn.textContent = "Answer";
  syncGradePanel();
}

function updateSetupSummary() {
  if (!setupSummaryHint) {
    return;
  }
  const parts = [];
  const courseLabel = courseSelect.selectedOptions[0]?.textContent?.trim();
  const aspectLabelText = aspectSelect.selectedOptions[0]?.textContent?.trim();
  const deckLabel = deckSelect.selectedOptions[0]?.textContent?.trim();
  const chapterLabel = chapterSelect.selectedOptions[0]?.textContent?.trim();
  if (courseSelect.value && courseLabel) {
    parts.push(courseLabel);
  }
  if (aspectSelect.value && aspectLabelText) {
    parts.push(aspectLabelText);
  }
  if (deckSelect.value && deckLabel) {
    parts.push(deckLabel);
  }
  if (chapterSelect.value && chapterLabel) {
    parts.push(chapterLabel);
  }
  const localeLabelText = localeSelect.selectedOptions[0]?.textContent?.trim();
  if (localeLabelText && getLocale() !== "en") {
    parts.push(localeLabelText);
  }
  setupSummaryHint.textContent =
    parts.length > 0 ? parts.join(" · ") : "Tap to configure filters";
}

function applySetupPanelState() {
  if (!setupPanel) {
    return;
  }
  const prefersMobile = window.matchMedia("(max-width: 800px)").matches;
  if (studySettings.setup_open === true || studySettings.setup_open === false) {
    setupPanel.open = studySettings.setup_open;
  } else {
    setupPanel.open = !prefersMobile;
  }
}

function revealKeyForBlock(blockId) {
  const base = blockId.replace("-block", "");
  if (base === "translation") {
    return "gloss";
  }
  if (base === "examples") {
    return "example";
  }
  return base;
}

function toolbarButton(blockId, label) {
  const key = revealKeyForBlock(blockId);
  const active = revealed[key];
  return `<button type="button" class="toggle-btn${active ? " is-revealed" : ""}" data-reveal="${blockId}">${label}</button>`;
}

function bindStudyCardInteractions(container) {
  container.querySelectorAll("[data-reveal]").forEach((button) => {
    button.addEventListener("click", () => {
      const blockId = button.getAttribute("data-reveal");
      const block = container.querySelector(`#${blockId}`);
      if (!block) {
        return;
      }
      const nowHidden = block.classList.toggle("hidden");
      button.classList.toggle("is-revealed", !nowHidden);
      const key = revealKeyForBlock(blockId);
      if (key in revealed) {
        revealed[key] = !nowHidden;
      }
    });
  });
}

function examplesVisible() {
  return revealed.example || (showAnswer && studySettings.auto_reveal_on_answer !== false);
}

function cardContextLabel(record) {
  const chapter = record.join?.Chapter || "";
  const deckLabel = deckDisplayLabel(record.deck);
  if (chapter) {
    return `${chapter} · ${deckLabel}`;
  }
  return deckLabel;
}

function currentCardGrade() {
  if (!cardRecords.length) {
    return null;
  }
  const { data } = getSessionProgress();
  return data.grades[cardStableId(cardRecords[cardIndex])] || null;
}

function updateProgressUi() {
  const { data } = getSessionProgress();
  const grades = data.grades || {};
  const total = cardRecords.length;
  const gradedCount = Object.keys(grades).length;
  const percent = total ? Math.round((gradedCount / total) * 100) : 0;

  progressBarFill.style.width = `${percent}%`;
  const progressTrack = progressBarFill.parentElement;
  if (progressTrack) {
    progressTrack.setAttribute("aria-valuenow", String(percent));
  }

  if (!total) {
    studyPosition.textContent = "No cards loaded";
    progressStats.textContent = "0 graded";
    gradeBreakdown.innerHTML = "";
    return;
  }

  studyPosition.textContent = `Card ${cardIndex + 1} of ${total}`;
  progressStats.textContent = `${gradedCount} of ${total} graded (${percent}%)`;

  const counts = { again: 0, hard: 0, good: 0, easy: 0 };
  for (const grade of Object.values(grades)) {
    if (counts[grade] != null) {
      counts[grade] += 1;
    }
  }
  gradeBreakdown.innerHTML = Object.entries(counts)
    .filter(([, count]) => count > 0)
    .map(
      ([grade, count]) =>
        `<span class="grade-chip grade-chip-${grade}">${GRADE_LABELS[grade]} ${count}</span>`,
    )
    .join("");
}

function syncGradePanel() {
  const canGrade = Boolean(cardRecords.length && showAnswer);
  gradePanel.classList.toggle("is-disabled", !canGrade);
  gradePanel.querySelectorAll(".grade-btn").forEach((button) => {
    const grade = button.getAttribute("data-grade");
    button.disabled = !canGrade;
    button.classList.toggle("is-selected", canGrade && currentCardGrade() === grade);
  });
}

function persistCardIndex() {
  const { data } = getSessionProgress();
  data.cardIndex = cardIndex;
  data.updatedAt = new Date().toISOString();
  saveProgressStore();
}

function applySessionProgress() {
  const { data } = getSessionProgress();
  if (
    typeof data.cardIndex === "number" &&
    data.cardIndex >= 0 &&
    data.cardIndex < cardRecords.length
  ) {
    cardIndex = data.cardIndex;
  } else if (cardIndex >= cardRecords.length) {
    cardIndex = 0;
  }
}

function gradeCurrentCard(grade) {
  if (!cardRecords.length || !showAnswer) {
    return;
  }
  const record = cardRecords[cardIndex];
  const { data } = getSessionProgress();
  data.grades[cardStableId(record)] = grade;
  data.updatedAt = new Date().toISOString();
  saveProgressStore();

  if (cardIndex < cardRecords.length - 1) {
    cardIndex += 1;
    resetRevealState();
  } else {
    showAnswer = true;
    showAnswerBtn.textContent = "Hide";
    syncGradePanel();
  }
  persistCardIndex();
  renderCurrentStudyCard();
}

function resetSessionProgress() {
  const key = sessionKey();
  delete progressStore.sessions[key];
  saveProgressStore();
  cardIndex = 0;
  resetRevealState();
  renderCurrentStudyCard();
}

function renderVocabStudyCard(record) {
  const anki = record.anki || {};
  const definition = vocabTranslation(record, "meaning");
  const exampleTranslation = vocabTranslation(record, "example_en");
  const usageNote = vocabTranslation(record, "usage_note");

  const toolbar = `
<div class="card-toolbar">
  ${toolbarButton("hanzi-block", "汉字")}
  ${toolbarButton("pinyin-block", "拼音")}
  ${toolbarButton("translation-block", "Definition")}
  ${toolbarButton("example-block", "例句")}
</div>
`;

  const hanziBlock = `<div id="hanzi-block" class="reveal-block${revealed.hanzi ? "" : " hidden"}"><div class="hanzi-text text-zh">${escapeHtml(anki.Hanzi || "")}</div></div>`;
  const pinyinBlock = `<div id="pinyin-block" class="reveal-block${revealed.pinyin ? "" : " hidden"}"><div class="pinyin-text text-latin">${escapeHtml(anki.Pinyin || "")}</div></div>`;
  const definitionBlock = `<div id="translation-block" class="reveal-block${revealed.gloss ? "" : " hidden"}"><div class="translation-text text-mother">${escapeHtml(definition)}</div><div class="mandarin-def text-zh">${escapeHtml(anki.MandarinDef || "")}</div></div>`;

  const exampleHidden = examplesVisible() ? "" : " hidden";
  const metaFront = `
<div class="meta-footer">
  <div class="badges">${escapeHtml(anki.POS || "")}${anki.POS && anki.Color ? " · " : ""}${escapeHtml(anki.Color || "")}</div>
  <div class="meta-line text-zh"><span class="meta-label">搭配</span> ${escapeHtml(anki.Collocations || record.master?.搭配 || "")}</div>
</div>
`;

  const exampleSection = `
<div id="example-block" class="example-block${exampleHidden}">
  <div class="meta-line text-zh"><span class="meta-label">例句</span> ${escapeHtml(anki.ExampleCN || "")}</div>
  ${exampleTranslation ? `<div class="meta-line text-mother">${escapeHtml(exampleTranslation)}</div>` : ""}
  ${usageNote ? `<div class="meta-line text-mother"><span class="meta-label">用法</span> ${escapeHtml(usageNote)}</div>` : ""}
  ${anki.CommonErrors ? `<div class="meta-line text-mother"><span class="meta-label">易错</span> ${escapeHtml(anki.CommonErrors)}</div>` : ""}
  ${anki.RelatedWords ? `<div class="meta-line text-zh"><span class="meta-label">相关</span> ${escapeHtml(anki.RelatedWords)}</div>` : ""}
</div>
`;

  let answerExtra = "";
  if (showAnswer) {
    answerExtra = `
<hr class="answer-divider"/>
<div class="answer-panel">
  <div class="hanzi-text text-zh">${escapeHtml(anki.Hanzi || "")}</div>
  <div class="pinyin-text text-latin">${escapeHtml(anki.Pinyin || "")}</div>
</div>
`;
  }

  const savedGrade = currentCardGrade();
  const gradeBadge = savedGrade
    ? `<span class="card-grade-badge grade-chip-${savedGrade}">${GRADE_LABELS[savedGrade]}</span>`
    : "";

  return `
${cardShellOpenTag(record)}
  <div class="chapter-label">${escapeHtml(cardContextLabel(record))} ${localeBadgeHtml()} ${gradeBadge}</div>
  ${toolbar}
  ${hanziBlock}
  ${pinyinBlock}
  ${definitionBlock}
  ${metaFront}
  ${exampleSection}
  ${answerExtra}
</div>
`;
}

function renderGrammarStudyCard(record) {
  const translations = record.translations || {};
  const joinParts = Object.entries(record.join)
    .filter(([key]) => key !== "Chapter")
    .map(([, value]) => value);
  const title = joinParts.join(" · ");
  const bodyFields = Object.entries(translations)
    .filter(([key]) => !key.startsWith("example_"))
    .map(
      ([key, value]) =>
        `<div class="body-text text-mother"><strong>${escapeHtml(friendlyTranslationKey(key))}</strong>: ${escapeHtml(value)}</div>`,
    )
    .join("");

  const exampleLines = Object.entries(translations)
    .filter(([key]) => key.startsWith("example_"))
    .map(
      ([key, value]) =>
        `<div class="meta-line text-mother"><span class="meta-label">${escapeHtml(friendlyTranslationKey(key))}</span> ${escapeHtml(value)}</div>`,
    )
    .join("");

  const masterExamples = [];
  if (record.master) {
    const orderedKeys = [
      "Example1CN",
      "Example2CN",
      "Example3CN",
      "Example1",
      "Example2",
      "Example3",
      "Example4",
      "Example5",
      "Example 1",
      "Example 2",
      "Example 3",
    ];
    for (const key of orderedKeys) {
      const value = record.master[key];
      if (value) {
        masterExamples.push(
          `<div class="${masterExampleLineClass(key)}">${escapeHtml(value)}</div>`,
        );
      }
    }
    for (const [key, value] of Object.entries(record.master)) {
      if (
        /example/i.test(key) &&
        value &&
        !/_en$/i.test(key) &&
        !orderedKeys.includes(key)
      ) {
        masterExamples.push(
          `<div class="${masterExampleLineClass(key)}">${escapeHtml(value)}</div>`,
        );
      }
    }
  }

  const examplesContent = exampleLines || masterExamples.join("");
  const exampleHidden = examplesVisible() ? "" : " hidden";
  const savedGrade = currentCardGrade();
  const gradeBadge = savedGrade
    ? `<span class="card-grade-badge grade-chip-${savedGrade}">${GRADE_LABELS[savedGrade]}</span>`
    : "";

  return `
${cardShellOpenTag(record)}
  <div class="chapter-label">${escapeHtml(cardContextLabel(record))} ${localeBadgeHtml()} ${gradeBadge}</div>
  <div class="grammar-title text-zh">${escapeHtml(title)}</div>
  ${bodyFields}
  <div class="card-toolbar">
    ${toolbarButton("examples-block", "例句")}
  </div>
  <div id="examples-block" class="example-block${exampleHidden}">
    ${examplesContent}
  </div>
  ${showAnswer ? '<hr class="answer-divider"/><div class="answer-panel muted">Answer side — examples above.</div>' : ""}
</div>
`;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderStudyCard(record) {
  if (record.anki) {
    return renderVocabStudyCard(record);
  }
  return renderGrammarStudyCard(record);
}

function renderCurrentStudyCard() {
  if (!cardRecords.length) {
    studyCardHost.innerHTML = '<p class="muted">No cards match these filters. Adjust setup and click Load cards.</p>';
    prevBtn.disabled = true;
    nextBtn.disabled = true;
    updateProgressUi();
    syncGradePanel();
    return;
  }
  const record = cardRecords[cardIndex];
  studyCardHost.innerHTML = renderStudyCard(record);
  bindStudyCardInteractions(studyCardHost);
  prevBtn.disabled = cardIndex <= 0;
  nextBtn.disabled = cardIndex >= cardRecords.length - 1;
  updateProgressUi();
  syncGradePanel();
}

function renderListPreview() {
  cardList.innerHTML = "";
  for (const record of cardRecords) {
    const article = document.createElement("article");
    article.className = `card-item ${localeScriptFontClass(cardLocaleCode(record))}`;
    if (record.anki) {
      const anki = record.anki;
      article.innerHTML = `
        <div class="muted">${escapeHtml(cardContextLabel(record))}</div>
        <div class="hanzi text-zh">${escapeHtml(anki.Hanzi || "")}</div>
        <div class="pinyin text-latin">${escapeHtml(anki.Pinyin || "")}</div>
        <div class="definition-line text-mother"><strong>${escapeHtml(vocabTranslation(record, "meaning"))}</strong> — <span class="text-zh">${escapeHtml(anki.MandarinDef || "")}</span></div>
        <div class="example text-zh">${escapeHtml(anki.ExampleCN || "")}<br/><em class="text-mother">${escapeHtml(vocabTranslation(record, "example_en"))}</em></div>
      `;
    } else {
      const blocks = Object.entries(record.translations || {})
        .map(
          ([key, value]) =>
            `<div class="definition-line text-mother"><strong>${escapeHtml(friendlyTranslationKey(key))}</strong>: ${escapeHtml(value)}</div>`,
        )
        .join("");
      const joinTitle = Object.entries(record.join || {})
        .filter(([key]) => key !== "Chapter")
        .map(([, value]) => value)
        .join(" · ");
      article.innerHTML = `
        <div class="muted">${escapeHtml(cardContextLabel(record))}</div>
        <div>${escapeHtml(joinTitle)}</div>
        ${blocks}
      `;
    }
    cardList.appendChild(article);
  }
}

async function loadStudyPrefs() {
  const response = await fetch("/api/study-prefs");
  studyPrefsConfig = await response.json();
  if (studyPrefsConfig.defaults) {
    studySettings = { ...studyPrefsConfig.defaults, ...studySettings };
  }
}

async function loadLocales() {
  const response = await fetch("/api/locales");
  const data = await response.json();
  localeSelect.innerHTML = "";
  for (const item of data.locales) {
    const option = document.createElement("option");
    option.value = item.code;
    option.textContent = item.label;
    localeSelect.appendChild(option);
  }
  localeSelect.value = studySettings.mother_locale || data.default || "en";
}

async function loadCourses() {
  const response = await fetch("/api/courses");
  const data = await response.json();
  courseSelect.innerHTML = '<option value="">All courses</option>';
  for (const course of data.courses) {
    const option = document.createElement("option");
    option.value = course.id;
    const zh = course.label_zh ? ` (${course.label_zh})` : "";
    option.textContent = `${course.label}${zh}`;
    courseSelect.appendChild(option);
  }
}

async function loadAspects() {
  const response = await fetch("/api/aspects");
  const data = await response.json();
  aspectSelect.innerHTML = '<option value="">All card types</option>';
  for (const aspect of data.aspects) {
    const option = document.createElement("option");
    option.value = aspect.id;
    option.textContent = aspect.label || aspectLabel(aspect.id);
    aspectSelect.appendChild(option);
  }
}

async function loadDecks() {
  const response = await fetch("/api/decks");
  const data = await response.json();
  deckLabelById = {};
  deckSelect.innerHTML = '<option value="">All decks in filter</option>';
  for (const deck of data.decks) {
    deckLabelById[deck.id] = deck.label || deck.id;
    const option = document.createElement("option");
    option.value = deck.id;
    option.textContent = deck.label || deck.id;
    deckSelect.appendChild(option);
  }
}

function filterQueryParams() {
  const params = new URLSearchParams();
  if (deckSelect.value) {
    params.set("deck", deckSelect.value);
  }
  if (courseSelect.value) {
    params.set("course", courseSelect.value);
  }
  if (aspectSelect.value) {
    params.set("aspect", aspectSelect.value);
  }
  return params;
}

async function loadChapters() {
  const params = filterQueryParams();
  const response = await fetch(`/api/chapters?${params}`);
  const data = await response.json();
  const previous = chapterSelect.value;
  chapterSelect.innerHTML = '<option value="">All chapters</option>';
  for (const chapter of data.chapters) {
    const option = document.createElement("option");
    option.value = chapter;
    option.textContent = chapter;
    chapterSelect.appendChild(option);
  }
  if (previous && data.chapters.includes(previous)) {
    chapterSelect.value = previous;
  } else if (studySettings.chapter && data.chapters.includes(studySettings.chapter)) {
    chapterSelect.value = studySettings.chapter;
  }
}

function hierarchyAspectLabel(aspectName) {
  return aspectLabel(aspectName) || aspectName;
}

function renderHierarchyNode(label, count, childrenHtml) {
  const countText = count != null ? ` <span class="count">(${count})</span>` : "";
  if (!childrenHtml) {
    return `<li>${label}${countText}</li>`;
  }
  return `<li>${label}${countText}<ul>${childrenHtml}</ul></li>`;
}

async function loadHierarchy() {
  const response = await fetch("/api/hierarchy");
  if (!response.ok) {
    throw new Error(`Hierarchy request failed (${response.status})`);
  }
  const data = await response.json();
  if (!data.courses) {
    throw new Error("Invalid hierarchy response");
  }
  hierarchyTotal.textContent = `— ${data.total_notes} cards`;

  const courseParts = [];
  for (const course of Object.values(data.courses)) {
    const chapterParts = [];
    for (const [chapterLabel, chapterNode] of Object.entries(course.chapters)) {
      const aspectParts = Object.entries(chapterNode.aspects)
        .map(([aspectName, aspectCount]) =>
          renderHierarchyNode(hierarchyAspectLabel(aspectName), aspectCount, ""),
        )
        .join("");
      chapterParts.push(
        renderHierarchyNode(chapterLabel, chapterNode.note_count, aspectParts),
      );
    }
    const zh = course.label_zh ? ` ${course.label_zh}` : "";
    courseParts.push(
      renderHierarchyNode(`${course.label}${zh}`, course.note_count, chapterParts.join("")),
    );
  }

  hierarchyTree.innerHTML = `<ul>${renderHierarchyNode(data.root, data.total_notes, courseParts.join(""))}</ul>`;
}

async function loadHierarchySafe() {
  try {
    await loadHierarchy();
  } catch (error) {
    console.error("loadHierarchy failed", error);
    hierarchyTree.innerHTML = '<p class="muted">Deck overview unavailable.</p>';
    hierarchyTotal.textContent = "";
  }
}

async function loadCards() {
  saveStudySettings();
  const params = filterQueryParams();
  params.set("locale", getLocale());
  params.set("limit", String(STUDY_CARD_LIMIT));
  params.set("offset", "0");
  if (chapterSelect.value) {
    params.set("chapter", chapterSelect.value);
  }
  const response = await fetch(`/api/cards?${params}`);
  const data = await response.json();
  if (!response.ok) {
    cardRecords = [];
    const detail =
      typeof data.detail === "string" ? data.detail : "Could not load cards.";
    studyCardHost.innerHTML = `<p class="muted">${escapeHtml(detail)} Adjust filters and click Load cards.</p>`;
    syncGradePanel();
    updateProgressUi();
    return;
  }
  cardRecords = Array.isArray(data.cards) ? data.cards : [];
  applySessionProgress();
  resetRevealState();
  renderCurrentStudyCard();
  updateSetupSummary();
  collapseSetupOnMobileAfterLoad();
  if (listModeCheckbox.checked) {
    renderListPreview();
  }
}

function collapseSetupOnMobileAfterLoad() {
  if (!setupPanel || !window.matchMedia("(max-width: 800px)").matches) {
    return;
  }
  if (cardRecords.length > 0) {
    setupPanel.open = false;
    studySettings.setup_open = false;
    saveStudySettings();
  }
}

async function refreshFilters() {
  await loadChapters();
  await loadCards();
  await loadHierarchySafe();
}

localeSelect.addEventListener("change", async () => {
  saveStudySettings();
  updateSetupSummary();
  cardIndex = 0;
  resetRevealState();
  await loadCards();
});

courseSelect.addEventListener("change", () => {
  saveStudySettings();
  refreshFilters();
});
aspectSelect.addEventListener("change", () => {
  saveStudySettings();
  refreshFilters();
});
deckSelect.addEventListener("change", () => {
  saveStudySettings();
  refreshFilters();
});
chapterSelect.addEventListener("change", () => {
  saveStudySettings();
  loadCards();
});

autoRevealCheckbox.addEventListener("change", () => {
  studySettings.auto_reveal_on_answer = autoRevealCheckbox.checked;
  saveStudySettings();
  renderCurrentStudyCard();
});

listModeCheckbox.addEventListener("change", () => {
  const showList = listModeCheckbox.checked;
  listPreviewSection.classList.toggle("hidden", !showList);
  if (showList) {
    listPreviewSection.open = true;
    renderListPreview();
  }
  saveStudySettings();
});

document.getElementById("refresh-btn").addEventListener("click", refreshFilters);

resetProgressBtn.addEventListener("click", () => {
  if (window.confirm("Clear grades and position for this filter set in this browser?")) {
    resetSessionProgress();
  }
});

prevBtn.addEventListener("click", () => {
  if (cardIndex > 0) {
    cardIndex -= 1;
    resetRevealState();
    persistCardIndex();
    renderCurrentStudyCard();
  }
});

nextBtn.addEventListener("click", () => {
  if (cardIndex < cardRecords.length - 1) {
    cardIndex += 1;
    resetRevealState();
    persistCardIndex();
    renderCurrentStudyCard();
  }
});

showAnswerBtn.addEventListener("click", () => {
  showAnswer = !showAnswer;
  showAnswerBtn.textContent = showAnswer ? "Hide" : "Answer";
  if (showAnswer && studySettings.auto_reveal_on_answer !== false) {
    revealed.example = true;
  }
  renderCurrentStudyCard();
});

gradePanel.querySelectorAll(".grade-btn").forEach((button) => {
  button.addEventListener("click", () => {
    const grade = button.getAttribute("data-grade");
    if (grade && showAnswer) {
      gradeCurrentCard(grade);
    }
  });
});

if (setupPanel) {
  setupPanel.addEventListener("toggle", () => {
    studySettings.setup_open = setupPanel.open;
    saveStudySettings();
  });
}

[
  courseSelect,
  aspectSelect,
  deckSelect,
  chapterSelect,
  localeSelect,
].forEach((selectElement) => {
  selectElement.addEventListener("change", updateSetupSummary);
});

(async function init() {
  await loadStudyPrefs();
  loadStudySettings();
  loadProgressStore();
  await loadLocales();
  await loadCourses();
  await loadAspects();
  await loadDecks();
  restoreFilterControls();
  applySetupPanelState();
  updateSetupSummary();
  await loadChapters();
  await loadCards();
  await loadHierarchySafe();
})();
