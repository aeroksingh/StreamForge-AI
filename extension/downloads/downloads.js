const PYTHON = 'http://localhost:8001'
const SPRING = 'http://localhost:8080'

// jobs = { jobId: { url, status, message, pct, fileUrl, addedAt } }
let jobs = {}
let pollTimer = null

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  const stored = await chrome.storage.local.get(null)

  // Active job bhi add karo
  if (stored.activeJob) {
    const jobId = stored.activeJob
    if (!jobs[jobId]) {
      jobs[jobId] = {
        url:     stored[jobId]?.url || 'Active download',
        quality: stored[jobId]?.quality || '',
        status:  'downloading',
        message: 'Fetching status...',
        pct:     0,
        fileUrl: null,
        addedAt: stored[jobId]?.addedAt || Date.now()
      }
    }
  }

  // Baaki completed jobs
  Object.keys(stored).forEach(key => {
    if (stored[key]?.url && key !== 'activeJob' && !jobs[key]) {
      jobs[key] = {
        url:     stored[key].url,
        quality: stored[key].quality || '',
        status:  'queued',
        message: 'Fetching status...',
        pct:     0,
        fileUrl: null,
        addedAt: stored[key].addedAt || Date.now()
      }
    }
  })

  document.getElementById('jobs-list').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-action]')
    if (!b) return
    const jobId = b.dataset.job
    if (b.dataset.action === 'remove') removeJob(jobId)
    if (b.dataset.action === 'save')   saveFile(jobId, jobs[jobId]?.fileUrl)
  })

  render()
  startPolling()
}

// ── Polling ───────────────────────────────────────────────────────────────────
function startPolling() {
  pollTimer = setInterval(async () => {
    const jobIds = Object.keys(jobs)
    if (jobIds.length === 0) return

    await Promise.all(jobIds.map(async (jobId) => {
      // Skip already done/error — no need to poll
      if (jobs[jobId].status === 'done' || jobs[jobId].status === 'error') return

      try {
        // Poll Spring Boot first, fallback to Python
        let status, message, pct
        try {
          const r = await fetch(`${SPRING}/api/download/status/${jobId}`)
          const d = await r.json()
          status  = (d.status || '').toLowerCase()
          message = d.message || d.errorMessage || ''
          pct     = d.progressPercent || 0

          // Map Spring status to our status
          if (status === 'completed') status = 'done'
          if (status === 'failed')    status = 'error'

        } catch {
          // Fallback to Python direct
          const r = await fetch(`${PYTHON}/status/${jobId}`)
          const d = await r.json()
          status  = d.status || 'queued'
          message = d.message || ''
          pct     = parsePercent(message)
        }

        jobs[jobId].status  = status
        jobs[jobId].message = message
        jobs[jobId].pct     = pct

        if (status === 'done') {
          jobs[jobId].fileUrl = `${PYTHON}/files/${jobId}_final.mp4`
          jobs[jobId].pct     = 100
        }

      } catch {
        // network error — keep last known status
      }
    }))

    render()
  }, 2000)
}

function parsePercent(msg) {
  const match = msg.match(/(\d+\.\d+)%/)
  return match ? parseFloat(match[1]) : 0
}

// ── Render ────────────────────────────────────────────────────────────────────
function render() {
  const list   = document.getElementById('jobs-list')
  const empty  = document.getElementById('empty')
  const jobIds = Object.keys(jobs).sort((a, b) => (jobs[b].addedAt || 0) - (jobs[a].addedAt || 0))

  // Stats
  const active = jobIds.filter(id => !['done','error'].includes(jobs[id].status)).length
  const done   = jobIds.filter(id => jobs[id].status === 'done').length
  document.getElementById('stat-active').textContent = active
  document.getElementById('stat-done').textContent   = done

  if (jobIds.length === 0) {
    empty.classList.remove('hidden')
    list.innerHTML = ''
    return
  }

  empty.classList.add('hidden')
  list.innerHTML = jobIds.map(id => jobCard(id, jobs[id])).join('')
}

function jobCard(jobId, job) {
  const status  = job.status || 'queued'
  const pct     = job.pct || 0
  const msg     = job.message || ''

  // Parse ETA + speed from message
  const eta   = (msg.match(/ETA\s+([^\s]+)/) || [])[1] || ''
  const speed = (msg.match(/at\s+([^\s]+)/) || [])[1] || ''
  const stream = msg.startsWith('Video') ? 'Video stream' :
                 msg.startsWith('Audio') ? 'Audio stream' :
                 msg.includes('Merging') ? 'Merging' : ''

  const pctDisplay = status === 'done'    ? '100%' :
                     status === 'merging' ? '99%'  :
                     status === 'queued'  ? '0%'   :
                     pct ? pct.toFixed(1) + '%' : '...'

  const actions = status === 'done' ? `
    <button class="btn-save" data-action="save" data-job="${jobId}">↓ Save File</button>
    <button class="btn-remove" data-action="remove" data-job="${jobId}">Remove</button>
  ` : status === 'error' ? `
    <button class="btn-remove" data-action="remove" data-job="${jobId}">Remove</button>
  ` : `
    <button class="btn-remove" style="opacity:.4;cursor:default">Downloading...</button>
  `

  const extraInfo = status === 'done' ? `
    <div class="done-msg">✓ Download complete — click Save File</div>
  ` : status === 'error' ? `
    <div class="error-msg">${msg}</div>
  ` : stream ? `
    <div class="progress-details">
      <div>${stream}</div>
      ${eta   ? `<div>ETA <span>${eta}</span></div>` : ''}
      ${speed ? `<div><span>${speed}</span></div>`   : ''}
    </div>
  ` : ''

  return `
    <div class="job-card ${status}" id="card-${jobId}">
      <div class="job-header">
        <div class="job-url" title="${job.url}">${job.url}</div>
        <div class="job-meta">
          ${job.quality ? `<span style="font-size:11px;color:#aaa">${job.quality}</span>` : ''}
          <span class="badge badge-${status}">${status}</span>
        </div>
      </div>

      <div class="progress-row">
        <div class="pct">${pctDisplay}</div>
        <div class="progress-info">
          <div class="bar-wrap">
            <div class="bar-fill ${status}" style="width:${pctDisplay}"></div>
          </div>
          ${extraInfo}
        </div>
      </div>

      <div class="job-actions">${actions}</div>
    </div>
  `
}

// ── Actions ───────────────────────────────────────────────────────────────────
function saveFile(jobId, fileUrl) {
  chrome.downloads.download({
    url:      fileUrl,
    filename: `streamforge_${jobId}.mp4`,
    saveAs:   true
  })
}

function removeJob(jobId) {
  delete jobs[jobId]
  chrome.storage.local.remove(jobId)
  render()
}

async function clearCompleted() {
  const toRemove = Object.keys(jobs).filter(id =>
    jobs[id].status === 'done' || jobs[id].status === 'error'
  )
  toRemove.forEach(id => {
    delete jobs[id]
    chrome.storage.local.remove(id)
  })
  render()
}

// ── Start ──────────────────────────────────────────────────────────────────────
init()