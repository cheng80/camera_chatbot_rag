const appConfigTargets = {
  brandMark: document.querySelector("[data-app-brand-mark]"),
  brandName: document.querySelector("[data-app-brand-name]"),
  appName: document.querySelector("[data-app-name]"),
  brandSelect: document.querySelector("[data-brand-select]"),
}
const BRAND_STORAGE_KEY = "camera.activeBrandId"

window.cameraActiveBrandId = ""

void loadAppConfig()

async function loadAppConfig() {
  try {
    const response = await fetch("/api/app-config")
    if (!response.ok) {
      return
    }
    const config = await response.json()
    const brands = Array.isArray(config.brands) ? config.brands : []
    const activeBrandId = selectedBrandId(
      String(config.active_brand_id ?? ""),
      brands,
    )
    applyAppConfig({
      appName: String(config.app_name ?? ""),
      activeBrandId,
      brandName: String(config.brand_name ?? ""),
      brandMark: String(config.brand_mark ?? ""),
      brands,
    })
  } catch {
    return
  }
}

function applyAppConfig(config) {
  renderBrandOptions(config.brands, config.activeBrandId)
  updateActiveBrand(config.activeBrandId, config.brands, { initial: true })
  if (config.brandMark && appConfigTargets.brandMark instanceof HTMLElement) {
    appConfigTargets.brandMark.textContent = config.brandMark
  }
  if (config.brandName && appConfigTargets.brandName instanceof HTMLElement) {
    appConfigTargets.brandName.textContent = config.brandName
  }
  if (config.appName && appConfigTargets.appName instanceof HTMLElement) {
    appConfigTargets.appName.textContent = config.appName
  }
  if (config.brandName && config.appName) {
    document.title = `${config.brandName} | ${config.appName}`
  }
}

function selectedBrandId(activeBrandId, brands) {
  const stored = window.localStorage.getItem(BRAND_STORAGE_KEY) ?? ""
  const brandIds = brands.map((brand) => String(brand.brand_id ?? ""))
  if (brandIds.includes(stored)) {
    return stored
  }
  if (brandIds.includes(activeBrandId)) {
    return activeBrandId
  }
  return brandIds[0] ?? ""
}

function renderBrandOptions(brands, activeBrandId) {
  const select = appConfigTargets.brandSelect
  if (!(select instanceof HTMLSelectElement)) {
    return
  }
  select.innerHTML = brands
    .map((brand) => {
      const brandId = String(brand.brand_id ?? "")
      const brandName = String(brand.brand_name ?? brandId)
      return `<option value="${escapeAttributeValue(brandId)}">${escapeHtml(
        brandName,
      )}</option>`
    })
    .join("")
  select.value = activeBrandId
  select.addEventListener("change", () => {
    updateActiveBrand(select.value, brands, { initial: false })
  })
}

function updateActiveBrand(activeBrandId, brands, options) {
  const activeBrand = brands.find(
    (brand) => String(brand.brand_id ?? "") === activeBrandId,
  )
  if (activeBrand === undefined) {
    return
  }
  window.localStorage.setItem(BRAND_STORAGE_KEY, activeBrandId)
  window.cameraActiveBrandId = activeBrandId
  applyBrandText({
    brandName: String(activeBrand.brand_name ?? ""),
    brandMark: String(activeBrand.brand_mark ?? ""),
  })
  window.dispatchEvent(
    new CustomEvent("camera-brand-change", {
      detail: { brandId: activeBrandId, initial: options.initial === true },
    }),
  )
}

function applyBrandText(config) {
  if (config.brandMark && appConfigTargets.brandMark instanceof HTMLElement) {
    appConfigTargets.brandMark.textContent = config.brandMark
  }
  if (config.brandName && appConfigTargets.brandName instanceof HTMLElement) {
    appConfigTargets.brandName.textContent = config.brandName
  }
  if (config.brandName && appConfigTargets.appName instanceof HTMLElement) {
    document.title = `${config.brandName} | ${appConfigTargets.appName.textContent}`
  }
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;")
}

function escapeAttributeValue(value) {
  return escapeHtml(value)
}
