let injected = false
let lastUrl  = ''

const observer = new MutationObserver(() => {
  const url = window.location.href
  if (url !== lastUrl) {
    lastUrl = url
    injected = false
    tryInject()
  }
})

observer.observe(document.body, { childList: true, subtree: true })
tryInject()

function tryInject() {
  if (injected) return
  if (!window.location.href.includes('watch?v=')) return

  const interval = setInterval(() => {
    const target = document.querySelector('#top-level-buttons-computed')
    if (target && !document.getElementById('sf-download-btn')) {
      injectButton(target)
      injected = true
      clearInterval(interval)
    }
  }, 800)
}

function injectButton(target) {
  const btn = document.createElement('button')
  btn.id = 'sf-download-btn'
  btn.textContent = '⬇ StreamForge'
  btn.style.cssText = `
    background:#22c55e;color:#fff;border:none;border-radius:18px;
    padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;
    font-family:'YouTube Sans',sans-serif;margin-left:8px;
  `
  btn.onclick = () => chrome.storage.local.set({ currentVideoUrl: window.location.href })
  target.appendChild(btn)
}