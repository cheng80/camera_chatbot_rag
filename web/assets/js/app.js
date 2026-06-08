const form = document.querySelector("#search-form")
const results = document.querySelector("#results")
const pdfPreview = document.querySelector("#pdf-preview")
const modelList = document.querySelector("#model-list")
const clearModels = document.querySelector("#clear-models")
const filterShell = document.querySelector("#filter-shell")
const filterSummary = document.querySelector("#filter-summary")
const contextSearchPanel = document.querySelector("#context-search-panel")
const quickQueryButtons = document.querySelectorAll("[data-query]")
const SEARCH_FETCH_LIMIT = 1000
const CONTEXT_SEARCH_FETCH_LIMIT = 80
const CONTEXT_ADDED_CARD_LIMIT = 24
const MODEL_GROUP_DEFINITIONS = [
  {
    key: "LUMIX S",
    label: "풀프레임 카메라",
  },
  {
    key: "LUMIX G",
    label: "마이크로 포서드 마운트 카메라",
  },
  {
    key: "medium_format",
    label: "중형카메라",
  },
  {
    key: "360_camera",
    label: "360카메라",
  },
  {
    key: "waterproof_camera",
    label: "방수카메라",
  },
  {
    key: "dslr",
    label: "DSLR",
  },
  {
    key: "film_camera",
    label: "필름 카메라",
  },
  {
    key: "compact_camera",
    label: "컴팩트 카메라",
  },
  {
    key: "LUMIX LX",
    label: "컴팩트 카메라",
  },
]
let resultState = null

void loadModels()
syncFilterShellWithViewport()

window.addEventListener("resize", syncFilterShellWithViewport)
window.addEventListener("camera-brand-change", (event) => {
  resultState = null
  renderContextSearchPanel(null)
  if (results instanceof HTMLElement) {
    const initial = event instanceof CustomEvent && event.detail.initial === true
    results.innerHTML = `<p class="status-line">${
      initial ? "검색어를 입력하세요." : "브랜드가 변경되었습니다. 검색어를 입력하세요."
    }</p>`
  }
  renderPdfPreview(null)
  void loadModels()
})

if (clearModels instanceof HTMLButtonElement) {
  clearModels.addEventListener("click", () => {
    modelButtons().forEach((button) => {
      button.setAttribute("aria-pressed", "false")
    })
    updateFilterSummary()
  })
}

if (form instanceof HTMLFormElement && results instanceof HTMLElement) {
  form.addEventListener("submit", (event) => {
    event.preventDefault()
    const data = new FormData(form)
    const query = String(data.get("query") ?? "").trim()
    const pageSize = Number(data.get("top_k") ?? 20)
    void runSearch(query, selectedModelIds(), selectedPageSize(pageSize), results)
  })
}

quickQueryButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (!(form instanceof HTMLFormElement)) {
      return
    }
    const input = form.elements.namedItem("query")
    if (!(input instanceof HTMLInputElement)) {
      return
    }
    input.value = String(button.dataset.query ?? "")
    form.requestSubmit()
  })
})

async function runSearch(query, modelIds, pageSize, target) {
  if (query.length === 0) {
    renderContextSearchPanel(null)
    target.textContent = "검색어를 입력하세요."
    return
  }

  resultState = null
  renderContextSearchPanel(null)
  target.innerHTML = `<p class="status-line">검색 중...</p>`
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(searchPayload(query, modelIds)),
    })
    const payload = await response.json()
    resultState = {
      page: 1,
      pageSize,
      payload,
      selectedIndex: null,
      query,
      modelIds,
      expansion: null,
    }
    renderCurrentPage(target)
  } catch {
    target.innerHTML = `<p class="status-line">검색 요청을 처리하지 못했습니다.</p>`
  }
}

function selectedPageSize(value) {
  if (!Number.isFinite(value)) {
    return 20
  }
  return Math.min(200, Math.max(1, Math.trunc(value)))
}

function selectedModelIds() {
  return modelButtons()
    .filter((button) => button.getAttribute("aria-pressed") === "true")
    .map((button) => String(button.dataset.modelId ?? "").trim())
    .filter(Boolean)
}

function modelButtons() {
  if (!(modelList instanceof HTMLElement)) {
    return []
  }
  return [...modelList.querySelectorAll("[data-model-id]")]
}

async function loadModels() {
  if (!(modelList instanceof HTMLElement)) {
    return
  }
  try {
    const response = await fetch(modelsUrl())
    const models = await response.json()
    renderModelButtons(Array.isArray(models) ? models : [])
  } catch {
    modelList.innerHTML = `<p class="status-line">모델 목록을 불러오지 못했습니다.</p>`
  }
}

function renderModelButtons(models) {
  if (!(modelList instanceof HTMLElement)) {
    return
  }
  if (models.length === 0) {
    modelList.innerHTML = `<p class="status-line">등록된 모델 없음</p>`
    return
  }
  modelList.innerHTML = groupedModels(models)
    .map((group, index) => renderModelGroup(group, index))
    .join("")
  modelList.querySelectorAll("[data-model-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const pressed = button.getAttribute("aria-pressed") === "true"
      button.setAttribute("aria-pressed", String(!pressed))
      updateFilterSummary()
    })
  })
  updateFilterSummary()
}

function groupedModels(models) {
  const groups = MODEL_GROUP_DEFINITIONS.map((definition) => ({
    key: definition.key,
    label: definition.label,
    models: [],
  }))
  const fallbackGroup = { key: "other", label: "기타", models: [] }
  models.forEach((model) => {
    const productLine = String(model.product_line ?? "")
    const groupIndex = MODEL_GROUP_DEFINITIONS.findIndex(
      (definition) => definition.key === productLine,
    )
    if (groupIndex >= 0) {
      groups[groupIndex].models.push(model)
      return
    }
    fallbackGroup.models.push(model)
  })
  return [...groups, fallbackGroup].filter((group) => group.models.length > 0)
}

function renderModelGroup(group, index) {
  return `<details class="model-group" ${index === 0 ? "open" : ""}>
    <summary>${escapeHtml(group.label)} <span>${group.models.length}</span></summary>
    <div class="model-group-list">
      ${group.models.map((model) => renderModelButton(model)).join("")}
    </div>
  </details>`
}

function updateFilterSummary() {
  if (!(filterSummary instanceof HTMLElement)) {
    return
  }
  const selected = selectedModelIds()
  filterSummary.textContent =
    selected.length === 0 ? "전체 모델" : `${selected.length}개 선택`
}

function syncFilterShellWithViewport() {
  if (!(filterShell instanceof HTMLDetailsElement)) {
    return
  }
  filterShell.open = window.matchMedia("(min-width: 761px)").matches
}

function renderModelButton(model) {
  const modelId = String(model.model_id ?? "")
  const displayName = String(model.display_name ?? modelId)
  const productLine = String(model.product_line ?? "")
  return `<button type="button" data-model-id="${escapeAttributeValue(
    modelId,
  )}" aria-pressed="false">
    <span>${escapeHtml(modelId)}</span>
    <small>${escapeHtml(
      [displayName, productLine].filter(Boolean).join(" · "),
    )}</small>
  </button>`
}

function searchPayload(query, modelIds) {
  const payload = { query, top_k: SEARCH_FETCH_LIMIT }
  const brandId = activeBrandId()
  const brandPayload = brandId.length === 0 ? payload : { ...payload, brand_id: brandId }
  if (modelIds.length === 0) {
    return brandPayload
  }
  return { ...brandPayload, model_ids: modelIds }
}

function contextSearchPayload(query, modelIds) {
  return {
    ...searchPayload(query, modelIds),
    top_k: CONTEXT_SEARCH_FETCH_LIMIT,
  }
}

function modelsUrl() {
  const brandId = activeBrandId()
  if (brandId.length === 0) {
    return "/api/models"
  }
  return `/api/models?brand_id=${encodeURIComponent(brandId)}`
}

function activeBrandId() {
  return String(window.cameraActiveBrandId ?? "").trim()
}

function renderCurrentPage(target) {
  if (resultState === null) {
    return
  }
  renderResults({
    page: resultState.page,
    pageSize: resultState.pageSize,
    payload: resultState.payload,
    selectedIndex: resultState.selectedIndex,
    target,
  })
  attachPaginationHandlers(target)
  attachCardSelectionHandlers(target)
  attachContextSearchHandler()
}

function renderResults({ payload, target, page, pageSize, selectedIndex }) {
  const cards = Array.isArray(payload.cards) ? payload.cards : []
  if (cards.length === 0) {
    target.innerHTML = `<p class="status-line">검색 상태: ${escapeHtml(
      String(payload.retrieval_status ?? "unknown"),
    )}</p>`
    renderPdfPreview(null)
    return
  }
  const pageCount = Math.max(1, Math.ceil(cards.length / pageSize))
  const safePage = Math.min(pageCount, Math.max(1, page))
  const start = (safePage - 1) * pageSize
  const safeSelectedIndex = visibleSelectedCardIndex({
    selectedIndex,
    cardCount: cards.length,
    pageStart: start,
    pageSize,
  })
  const pageCards = cards.slice(start, start + pageSize)
  renderPdfPreview(
    safeSelectedIndex === null ? null : (cards[safeSelectedIndex] ?? null),
  )
  target.innerHTML = `${renderPagination({
    page: safePage,
    pageCount,
    pageSize,
    totalCount: cards.length,
  })}
  ${pageCards
    .map((card, offset) =>
      renderCard(
        card,
        start + offset,
        safeSelectedIndex !== null && start + offset === safeSelectedIndex,
      ),
    )
    .join("")}
  ${renderPagination({
    page: safePage,
    pageCount,
    pageSize,
    totalCount: cards.length,
  })}`
  resultState = {
    page: safePage,
    pageSize,
    payload,
    selectedIndex: safeSelectedIndex,
    query: resultState?.query ?? String(payload.query ?? ""),
    modelIds: resultState?.modelIds ?? [],
    expansion: resultState?.expansion ?? null,
  }
  renderContextSearchPanel(resultState)
}

function renderPagination({ page, pageCount, pageSize, totalCount }) {
  const first = Math.min(totalCount, (page - 1) * pageSize + 1)
  const last = Math.min(totalCount, page * pageSize)
  return `<nav class="pagination" aria-label="검색 결과 페이지">
    <div class="pagination-status">
      <div class="pagination-page"><strong>${page} / ${pageCount}쪽</strong></div>
      <small>${totalCount}개 결과 중 ${first}-${last} 표시</small>
    </div>
    <div class="pagination-controls">
      <button type="button" data-page-action="first" ${
        page <= 1 ? "disabled" : ""
      }>처음</button>
      <button type="button" data-page-action="prev" ${
        page <= 1 ? "disabled" : ""
      }>이전</button>
      <label class="page-jump">
        <span>쪽</span>
        <input
          type="number"
          min="1"
          max="${String(pageCount)}"
          value="${String(page)}"
          data-page-jump
          aria-label="이동할 페이지"
        />
      </label>
      <button type="button" data-page-action="jump">이동</button>
      <button type="button" data-page-action="next" ${
        page >= pageCount ? "disabled" : ""
      }>다음</button>
      <button type="button" data-page-action="last" ${
        page >= pageCount ? "disabled" : ""
      }>끝</button>
    </div>
  </nav>`
}

function attachPaginationHandlers(target) {
  target.querySelectorAll("[data-page-action]").forEach((button) => {
    button.addEventListener("click", () => {
      if (resultState === null) {
        return
      }
      const action = String(button.dataset.pageAction ?? "")
      const nextPage = nextPageForAction({
        action,
        currentPage: resultState.page,
        pageCount: pageCountForState(resultState),
        control: button.closest(".pagination"),
      })
      resultState = {
        ...resultState,
        page: nextPage,
        selectedIndex: null,
      }
      renderCurrentPage(target)
    })
  })
  target.querySelectorAll("[data-page-jump]").forEach((input) => {
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || resultState === null) {
        return
      }
      event.preventDefault()
      resultState = {
        ...resultState,
        page: clampedPage({
          value: Number(input.value),
          pageCount: pageCountForState(resultState),
        }),
        selectedIndex: null,
      }
      renderCurrentPage(target)
    })
  })
}

function nextPageForAction({ action, currentPage, pageCount, control }) {
  if (action === "first") {
    return 1
  }
  if (action === "last") {
    return pageCount
  }
  if (action === "prev") {
    return clampedPage({ value: currentPage - 1, pageCount })
  }
  if (action === "next") {
    return clampedPage({ value: currentPage + 1, pageCount })
  }
  const input = control?.querySelector("[data-page-jump]")
  const value = input instanceof HTMLInputElement ? Number(input.value) : currentPage
  return clampedPage({ value, pageCount })
}

function pageCountForState(state) {
  return Math.max(1, Math.ceil(cardCount(state.payload) / state.pageSize))
}

function clampedPage({ value, pageCount }) {
  if (!Number.isFinite(value)) {
    return 1
  }
  return Math.min(pageCount, Math.max(1, Math.trunc(value)))
}

function attachCardSelectionHandlers(target) {
  target.querySelectorAll("[data-card-index]").forEach((cardElement) => {
    cardElement.addEventListener("click", (event) => {
      if (
        event.target instanceof Element &&
        event.target.closest("a") !== null
      ) {
        return
      }
      selectCard(cardElement)
    })
    cardElement.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") {
        return
      }
      event.preventDefault()
      selectCard(cardElement)
    })
  })
}

function selectCard(cardElement) {
  if (resultState === null || !(results instanceof HTMLElement)) {
    return
  }
  const index = Number(cardElement.dataset.cardIndex ?? 0)
  if (!Number.isFinite(index)) {
    return
  }
  resultState = { ...resultState, selectedIndex: Math.trunc(index) }
  renderCurrentPage(results)
}

function renderContextSearchPanel(state) {
  if (!(contextSearchPanel instanceof HTMLElement)) {
    return
  }
  if (state === null || String(state.query ?? "").trim().length === 0) {
    contextSearchPanel.hidden = true
    contextSearchPanel.innerHTML = ""
    return
  }
  const expansion = state.expansion
  const expandedQueries =
    expansion && Array.isArray(expansion.expanded_queries)
      ? expansion.expanded_queries
      : []
  const expansionSummary = expansion?.loading === true
    ? renderExpansionSummary({
        beforeCount: cardCount(state.payload),
        afterCount: null,
        addedCount: null,
      })
    : renderExpansionSummary(expansion)
  contextSearchPanel.hidden = false
  contextSearchPanel.innerHTML = `<div>
      <strong>문맥 기반 추가 검색</strong>
      <p>LLM으로 한국어 질문 의도를 해석해 관련 검색어를 더 찾아볼 수 있습니다. 기본 검색보다 몇 초 더 걸릴 수 있습니다.</p>
      ${expansionSummary}
      ${expandedQueries.length > 0 ? renderExpandedQueries(expandedQueries) : ""}
    </div>
    <button type="button" data-context-search ${
      expansion?.loading === true ? "disabled" : ""
    }>${expansion?.loading === true ? "추가 검색 중..." : "문맥 기반 추가 검색"}</button>`
}

function renderExpansionSummary(expansion) {
  if (expansion === null || expansion === undefined) {
    return ""
  }
  const beforeText = countText(expansion.beforeCount)
  const afterText = countText(expansion.afterCount)
  const addedText = addedCountText(expansion.addedCount)
  return `<div class="context-search-stats" aria-label="문맥 검색 결과 변화">
    <span>기존 ${beforeText}</span>
    <span>확장 후 ${afterText}</span>
    <span>${addedText}</span>
  </div>`
}

function countText(value) {
  if (!Number.isFinite(value)) {
    return "확인 중"
  }
  return `${Math.max(0, Math.trunc(value))}개`
}

function addedCountText(value) {
  if (!Number.isFinite(value)) {
    return "추가 확인 중"
  }
  const count = Math.max(0, Math.trunc(value))
  return count === 0 ? "새 카드 없음" : `+${count}개`
}

function renderExpandedQueries(queries) {
  return `<p class="expanded-query-line">확장 검색어: ${queries
    .map((query) => escapeHtml(String(query)))
    .join(", ")}</p>`
}

function attachContextSearchHandler() {
  if (!(contextSearchPanel instanceof HTMLElement)) {
    return
  }
  const button = contextSearchPanel.querySelector("[data-context-search]")
  if (!(button instanceof HTMLButtonElement)) {
    return
  }
  button.addEventListener("click", () => {
    void runContextSearch()
  })
}

async function runContextSearch() {
  if (resultState === null || !(results instanceof HTMLElement)) {
    return
  }
  const beforeCount = cardCount(resultState.payload)
  const currentState = {
    ...resultState,
    expansion: { loading: true, beforeCount },
  }
  resultState = currentState
  renderContextSearchPanel(currentState)
  try {
    const response = await fetch("/api/search/expand", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(
        contextSearchPayload(currentState.query, currentState.modelIds ?? []),
      ),
    })
    const payload = await response.json()
    const nextPayload = expandedResultPayload({
      basePayload: currentState.payload,
      expandedPayload: payload.response ?? currentState.payload,
    })
    const afterCount = cardCount(nextPayload)
    const addedCount = addedCardCount(nextPayload)
    resultState = {
      ...currentState,
      page: 1,
      selectedIndex: null,
      payload: nextPayload,
      expansion: {
        ...payload,
        beforeCount,
        afterCount,
        addedCount,
      },
    }
    renderCurrentPage(results)
  } catch {
    resultState = {
      ...currentState,
      expansion: {
        status: "unavailable",
        expanded_queries: [],
        notice: "문맥 기반 추가 검색 요청을 처리하지 못했습니다.",
        beforeCount,
        afterCount: beforeCount,
        addedCount: 0,
      },
    }
    renderContextSearchPanel(resultState)
  }
}

function cardCount(payload) {
  const cards = payload && Array.isArray(payload.cards) ? payload.cards : []
  return cards.length
}

function addedCardCount(payload) {
  return cardsFromPayload(payload).filter((card) => card.context_origin === "added")
    .length
}

function expandedResultPayload({ basePayload, expandedPayload }) {
  const baseCards = cardsFromPayload(basePayload).map((card) => ({
    ...card,
    context_origin: "existing",
  }))
  const baseKeys = sourceKeySet(cardsFromPayload(basePayload))
  const addedCards = cardsFromPayload(expandedPayload)
    .filter((card) => !baseKeys.has(sourceKey(card)))
    .map((card) => ({ ...card, context_origin: "added" }))
  return {
    ...expandedPayload,
    cards: [...addedCards.slice(0, CONTEXT_ADDED_CARD_LIMIT), ...baseCards],
  }
}

function cardsFromPayload(payload) {
  return payload && Array.isArray(payload.cards) ? payload.cards : []
}

function sourceKeySet(cards) {
  return new Set(cards.map((card) => sourceKey(card)).filter(Boolean))
}

function sourceKey(card) {
  const sources = Array.isArray(card.sources) ? card.sources : []
  const source = sources[0]
  if (source === undefined) {
    return ""
  }
  return [
    String(source.document_id ?? ""),
    String(source.model_id ?? ""),
    String(source.page ?? ""),
  ].join("|")
}

function renderCard(card, index, selected) {
  const sources = Array.isArray(card.sources) ? card.sources : []
  const models = Array.isArray(card.supported_models) ? card.supported_models : []
  return `<article class="result-card" tabindex="0" role="button" aria-pressed="${String(
    selected,
  )}" data-card-index="${String(index)}">
    <div class="card-header">
      <h2>${escapeHtml(String(card.feature_name ?? "기능"))}</h2>
      <div class="card-badges">
        ${renderContextOriginBadge(card)}
        <span>${escapeHtml(evidenceStatusText(card.evidence_status))}</span>
      </div>
    </div>
    <p>${escapeHtml(String(card.summary ?? ""))}</p>
    <p class="meta-line">${escapeHtml(modelText(models))}</p>
    <ul class="source-list">
      ${sources.map((source) => renderSource(source)).join("")}
    </ul>
  </article>`
}

function renderContextOriginBadge(card) {
  if (card.context_origin !== "added" && card.context_origin !== "existing") {
    return ""
  }
  const label = card.context_origin === "added" ? "추가" : "기존"
  return `<span class="context-origin-badge" data-origin="${escapeAttributeValue(
    card.context_origin,
  )}">${label}</span>`
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

function renderPdfPreview(card) {
  if (!(pdfPreview instanceof HTMLElement)) {
    return
  }
  if (card === null) {
    pdfPreview.innerHTML =
      `<p class="status-line">카드를 선택하면 PDF 페이지가 표시됩니다.</p>`
    return
  }
  const sources = Array.isArray(card.sources) ? card.sources : []
  const source = sources[0]
  if (source === undefined) {
    pdfPreview.innerHTML = `<p class="status-line">출처 페이지 없음</p>`
    return
  }
  const url = String(source.viewer_url ?? "")
  const documentId = String(source.document_id ?? "")
  const modelId = String(source.model_id ?? "")
  const page = String(source.page ?? "")
  pdfPreview.innerHTML = `<div class="preview-meta">
      <strong>${escapeHtml(modelId)} ${escapeHtml(page)}쪽</strong>
      <span>${escapeHtml(documentId)}</span>
    </div>
    <iframe title="선택한 PDF 페이지" src="${escapeAttribute(url)}"></iframe>
    <a href="${escapeAttribute(url)}" target="_blank" rel="noreferrer">크게 열기</a>`
}

function visibleSelectedCardIndex({ selectedIndex, cardCount, pageStart, pageSize }) {
  const index = selectedCardIndex(selectedIndex, cardCount)
  if (index === null) {
    return null
  }
  if (index < pageStart || index >= pageStart + pageSize) {
    return null
  }
  return index
}

function selectedCardIndex(value, cardCount) {
  if (!Number.isFinite(value) || cardCount < 1) {
    return null
  }
  return Math.min(cardCount - 1, Math.max(0, Math.trunc(value)))
}

function modelText(models) {
  const ids = models.map((model) => String(model.model_id ?? "")).filter(Boolean)
  if (ids.length === 0) {
    return "모델 정보 없음"
  }
  return `모델: ${ids.join(", ")}`
}

function evidenceStatusText(value) {
  if (value === "insufficient_evidence") {
    return "근거 부족"
  }
  return "출처 확인"
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

function escapeAttributeValue(value) {
  return escapeHtml(value)
}
