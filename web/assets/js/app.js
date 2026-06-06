const form = document.querySelector("#search-form")
const results = document.querySelector("#results")

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

  const response = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  })
  const payload = await response.json()
  target.innerHTML = `<article class="result-card">
    <h2>검색 준비 상태</h2>
    <p>상태: ${payload.retrieval_status}</p>
    <p>색인이 만들어지면 기능 카드가 여기에 표시됩니다.</p>
  </article>`
}
