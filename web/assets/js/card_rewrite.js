const rewriteCache = new Map()

document.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) {
    return
  }
  if (event.target.closest("a") !== null) {
    return
  }
  if (event.target.closest(".result-card") === null) {
    return
  }
  queueSelectedCardRewrite()
})

document.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") {
    return
  }
  if (!(event.target instanceof Element)) {
    return
  }
  if (event.target.closest(".result-card") === null) {
    return
  }
  queueSelectedCardRewrite()
})

function queueSelectedCardRewrite() {
  window.setTimeout(() => {
    void rewriteSelectedCard()
  }, 0)
}

async function rewriteSelectedCard() {
  const card = document.querySelector('.result-card[aria-pressed="true"]')
  if (!(card instanceof HTMLElement)) {
    return
  }
  const payload = rewritePayload(card)
  if (payload === null) {
    renderAiSummary(card, "error", "AI 요약에 필요한 출처 정보를 읽지 못했습니다.")
    return
  }
  const cacheKey = JSON.stringify(payload)
  const cached = rewriteCache.get(cacheKey)
  if (cached !== undefined) {
    renderAiSummary(card, cached.status, cached.summary)
    return
  }

  renderAiSummary(card, "loading", "AI 요약 생성 중...")
  try {
    const response = await fetch("/api/search/rewrite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    const result = await response.json()
    const status = result.status === "ok" ? "ready" : "error"
    const summary = String(result.summary ?? payload.summary)
    rewriteCache.set(cacheKey, { status, summary })
    renderAiSummary(card, status, summary)
  } catch {
    const fallback = "AI 요약 생성에 실패했습니다. 카드의 원문 요약과 PDF 출처를 확인하세요."
    rewriteCache.set(cacheKey, { status: "error", summary: fallback })
    renderAiSummary(card, "error", fallback)
  }
}

function rewritePayload(card) {
  const query = currentQuery()
  const heading = card.querySelector(".card-header h2")
  const summary = card.querySelector(":scope > p:not(.meta-line)")
  const sources = sourcePayloads(card)
  if (
    !(heading instanceof HTMLElement) ||
    !(summary instanceof HTMLElement) ||
    query.length === 0 ||
    sources.length === 0
  ) {
    return null
  }
  return {
    query,
    feature_name: heading.textContent?.trim() ?? "",
    summary: summary.textContent?.trim() ?? "",
    sources: sources.slice(0, 5),
  }
}

function currentQuery() {
  const input = document.querySelector("#query")
  if (!(input instanceof HTMLInputElement)) {
    return ""
  }
  return input.value.trim()
}

function sourcePayloads(card) {
  return [...card.querySelectorAll(".source-list li")]
    .map(sourcePayload)
    .filter((source) => source !== null)
}

function sourcePayload(item) {
  const link = item.querySelector("a")
  const label = item.querySelector("span")
  if (!(link instanceof HTMLAnchorElement) || !(label instanceof HTMLElement)) {
    return null
  }
  const match = new URL(link.href, window.location.origin).pathname.match(
    /^\/api\/viewer\/([^/]+)\/pages\/(\d+)$/,
  )
  if (match === null) {
    return null
  }
  const labelParts = label.textContent?.split(" · ") ?? []
  const sectionTitle = labelParts.slice(1).join(" · ").trim()
  const linkTextParts = link.textContent?.trim().split(/\s+/) ?? []
  return {
    document_id: decodeURIComponent(match[1]),
    model_id: linkTextParts[0] ?? "",
    page: Number(match[2]),
    section_title: sectionTitle,
    viewer_url: new URL(link.href, window.location.origin).pathname,
  }
}

function renderAiSummary(card, status, summary) {
  const section = aiSummarySection(card)
  section.className = `ai-summary is-${status}`
  section.innerHTML = ""
  const heading = document.createElement("h3")
  heading.textContent = "AI 요약"
  const body = document.createElement("p")
  body.textContent = summary
  section.append(heading, body)
}

function aiSummarySection(card) {
  const existing = card.querySelector("[data-ai-summary]")
  if (existing instanceof HTMLElement) {
    return existing
  }
  const section = document.createElement("section")
  section.dataset.aiSummary = "true"
  const sources = card.querySelector(".source-list")
  if (sources instanceof HTMLElement) {
    sources.before(section)
    return section
  }
  card.append(section)
  return section
}
