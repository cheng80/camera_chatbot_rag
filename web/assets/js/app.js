const form = document.querySelector("#search-form")
const results = document.querySelector("#results")
const viewerPanel = document.querySelector(".viewer-panel")

if (form instanceof HTMLFormElement && results instanceof HTMLElement) {
  form.addEventListener("submit", (event) => {
    event.preventDefault()
    const data = new FormData(form)
    const query = String(data.get("query") ?? "").trim()
    void runSearch(query, results)
  })
}

async function runSearch(query, target) {
  if (query.length === 0) {
    target.textContent = "검색어를 입력하세요."
    return
  }

  target.innerHTML = `<p class="status-line">검색 중...</p>`
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    })
    const payload = await response.json()
    renderResults(payload, target)
    renderViewer(payload)
  } catch {
    target.innerHTML = `<p class="status-line">검색 요청을 처리하지 못했습니다.</p>`
  }
}

function renderResults(payload, target) {
  const cards = Array.isArray(payload.cards) ? payload.cards : []
  if (cards.length === 0) {
    target.innerHTML = `<p class="status-line">검색 상태: ${escapeHtml(
      String(payload.retrieval_status ?? "unknown"),
    )}</p>`
    return
  }
  target.innerHTML = cards.map((card) => renderCard(card)).join("")
}

function renderCard(card) {
  const sources = Array.isArray(card.sources) ? card.sources : []
  const models = Array.isArray(card.supported_models) ? card.supported_models : []
  return `<article class="result-card">
    <div class="card-header">
      <h2>${escapeHtml(String(card.feature_name ?? "기능"))}</h2>
      <span>${escapeHtml(String(card.evidence_status ?? "source_validated"))}</span>
    </div>
    <p>${escapeHtml(String(card.summary ?? ""))}</p>
    <p class="meta-line">${escapeHtml(modelText(models))}</p>
    <ul class="source-list">
      ${sources.map((source) => renderSource(source)).join("")}
    </ul>
  </article>`
}

function renderSource(source) {
  const documentId = String(source.document_id ?? "")
  const modelId = String(source.model_id ?? "")
  const page = String(source.page ?? "")
  const url = String(source.viewer_url ?? "")
  const title = String(source.section_title ?? "")
  return `<li>
    <a href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">
      ${escapeHtml(modelId)} ${escapeHtml(page)}쪽
    </a>
    <span>${escapeHtml(documentId)} · ${escapeHtml(title)}</span>
  </li>`
}

function renderViewer(payload) {
  if (!(viewerPanel instanceof HTMLElement)) {
    return
  }
  const cards = Array.isArray(payload.cards) ? payload.cards : []
  const firstSource = cards[0]?.sources?.[0]
  if (firstSource === undefined) {
    viewerPanel.innerHTML = `<h2>PDF Source</h2><p>출처 페이지 없음</p>`
    return
  }
  const url = String(firstSource.viewer_url ?? "")
  viewerPanel.innerHTML = `<h2>PDF Source</h2>
    <p>${escapeHtml(String(firstSource.document_id ?? ""))}</p>
    <p>${escapeHtml(String(firstSource.model_id ?? ""))} · ${escapeHtml(
      String(firstSource.page ?? ""),
    )}쪽</p>
    <a class="viewer-link" href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">
      PDF 페이지 열기
    </a>`
}

function modelText(models) {
  const ids = models.map((model) => String(model.model_id ?? "")).filter(Boolean)
  if (ids.length === 0) {
    return "모델 정보 없음"
  }
  return `모델: ${ids.join(", ")}`
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function escapeAttribute(value) {
  if (!value.startsWith("/api/viewer/")) {
    return "#"
  }
  return escapeHtml(value)
}
