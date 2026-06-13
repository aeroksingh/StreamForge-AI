const PYTHON = 'http://localhost:8001'

// ── Tab update listener ───────────────────────────────────────────────────────
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url?.includes('youtube.com/watch')) {
    chrome.scripting.executeScript({
      target: { tabId },
      files: ['content/content.js']
    }).catch(() => {})
  }
})

// ── Message listener ──────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'TRACK_JOB') {
    trackJobInBackground(msg.jobId)
  }
  if (msg.type === 'DOWNLOAD_DONE') {
    showNotification('✓ Download complete — file ready!')
    chrome.action.setBadgeText({ text: '✓' })
    chrome.action.setBadgeBackgroundColor({ color: '#22c55e' })
  }
})

// ── Track job — show badge even when popup is closed ─────────────────────────
function trackJobInBackground(jobId) {
  const badges = {
    queued:      { text: 'Q',  color: '#f59e0b' },
    extracting:  { text: 'E',  color: '#f59e0b' },
    downloading: { text: '↓',  color: '#3b82f6' },
    merging:     { text: 'M',  color: '#8b5cf6' },
    completed:   { text: '✓',  color: '#22c55e' },
    failed:      { text: '!',  color: '#ef4444' },
    error:       { text: '!',  color: '#ef4444' },
  }

  // Set initial badge
  chrome.action.setBadgeText({ text: '↓' })
  chrome.action.setBadgeBackgroundColor({ color: '#3b82f6' })

  const t = setInterval(async () => {
    try {
      const r = await fetch(`${PYTHON}/status/${jobId}`)
      const d = await r.json()
      const status = (d.status || '').toLowerCase()

      const badge = badges[status]
      if (badge) {
        chrome.action.setBadgeText({ text: badge.text })
        chrome.action.setBadgeBackgroundColor({ color: badge.color })
      }

      if (status === 'done' || status === 'completed') {
        clearInterval(t)
        showNotification('✓ StreamForge — Download complete! Click to save.')
        // Clear badge after 10s
        setTimeout(() => chrome.action.setBadgeText({ text: '' }), 10000)
      }

      if (status === 'error' || status === 'failed') {
        clearInterval(t)
        showNotification('✗ StreamForge — Download failed: ' + d.message)
        setTimeout(() => chrome.action.setBadgeText({ text: '' }), 10000)
      }

    } catch {}
  }, 3000)
}

// ── Notification helper ───────────────────────────────────────────────────────
function showNotification(message) {
  chrome.notifications.create({
    type:    'basic',
    iconUrl: 'icons/icon48.png',
    title:   'StreamForge AI',
    message: message
  })
}