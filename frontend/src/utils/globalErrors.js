const BANNER_ID = "skillmirror-global-error-banner"
const INSTALLED_KEY = "__skillmirror_error_handler_installed__"


function safeErrorMessage(error) {
  let message = "页面发生异常，请刷新后重试。"

  if (error instanceof Error && error.message) {
    message = error.message
  } else if (typeof error === "string" && error) {
    message = error
  }

  message = message
    .replace(
      /(token|secret|signature)\s*[:=]\s*[^\s,;]+/gi,
      "$1=[REDACTED]",
    )
    .slice(0, 300)

  return message
}


function removeExistingBanner() {
  const existing = document.getElementById(BANNER_ID)

  if (existing) {
    existing.remove()
  }
}


function createButton(text, onClick) {
  const button = document.createElement("button")

  button.type = "button"
  button.textContent = text

  Object.assign(button.style, {
    border: "1px solid rgba(255, 255, 255, 0.7)",
    borderRadius: "8px",
    background: "rgba(255, 255, 255, 0.16)",
    color: "#ffffff",
    padding: "7px 13px",
    fontSize: "14px",
    fontWeight: "700",
    cursor: "pointer",
  })

  button.addEventListener("click", onClick)

  return button
}


function showGlobalError(message) {
  removeExistingBanner()

  const banner = document.createElement("div")
  banner.id = BANNER_ID
  banner.setAttribute("role", "alert")
  banner.setAttribute("aria-live", "assertive")

  Object.assign(banner.style, {
    position: "fixed",
    top: "14px",
    left: "50%",
    transform: "translateX(-50%)",
    zIndex: "999999",
    width: "min(920px, calc(100% - 32px))",
    boxSizing: "border-box",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "18px",
    padding: "14px 18px",
    borderRadius: "12px",
    background: "#b42318",
    color: "#ffffff",
    boxShadow: "0 12px 36px rgba(80, 20, 20, 0.28)",
    fontFamily:
      "Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
  })

  const content = document.createElement("div")

  const title = document.createElement("strong")
  title.textContent = "SkillMirror 页面发生异常"

  Object.assign(title.style, {
    display: "block",
    marginBottom: "3px",
    fontSize: "15px",
  })

  const description = document.createElement("span")
  description.textContent =
    message || "页面发生异常，请刷新后重试。"

  Object.assign(description.style, {
    fontSize: "14px",
    lineHeight: "1.45",
    opacity: "0.96",
  })

  content.appendChild(title)
  content.appendChild(description)

  const actions = document.createElement("div")

  Object.assign(actions.style, {
    display: "flex",
    flexShrink: "0",
    gap: "8px",
  })

  const closeButton = createButton(
    "关闭",
    removeExistingBanner,
  )

  const reloadButton = createButton(
    "刷新页面",
    () => {
      window.location.reload()
    },
  )

  actions.appendChild(closeButton)
  actions.appendChild(reloadButton)

  banner.appendChild(content)
  banner.appendChild(actions)

  document.body.appendChild(banner)
}


export function installGlobalErrorHandling(app) {
  if (window[INSTALLED_KEY]) {
    return
  }

  window[INSTALLED_KEY] = true

  app.config.errorHandler = (
    error,
    _instance,
    info,
  ) => {
    const message = safeErrorMessage(error)

    console.error(
      "[SkillMirror Vue Error]",
      info,
      message,
    )

    showGlobalError(message)
  }

  window.addEventListener("error", (event) => {
    const message = safeErrorMessage(
      event.error || event.message,
    )

    console.error(
      "[SkillMirror Window Error]",
      message,
    )

    showGlobalError(message)
  })

  window.addEventListener(
    "unhandledrejection",
    (event) => {
      const message = safeErrorMessage(event.reason)

      console.error(
        "[SkillMirror Promise Error]",
        message,
      )

      showGlobalError(message)
    },
  )
}