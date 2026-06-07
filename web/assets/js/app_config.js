const appConfigTargets = {
  brandMark: document.querySelector("[data-app-brand-mark]"),
  brandName: document.querySelector("[data-app-brand-name]"),
  appName: document.querySelector("[data-app-name]"),
}

void loadAppConfig()

async function loadAppConfig() {
  try {
    const response = await fetch("/api/app-config")
    if (!response.ok) {
      return
    }
    const config = await response.json()
    applyAppConfig({
      appName: String(config.app_name ?? ""),
      brandName: String(config.brand_name ?? ""),
      brandMark: String(config.brand_mark ?? ""),
    })
  } catch {
    return
  }
}

function applyAppConfig(config) {
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
