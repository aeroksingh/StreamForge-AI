const SPRING = 'http://localhost:8080'
const PYTHON  = 'http://localhost:8001'

let vItag = null, aItag = null, url = ''

document.addEventListener('DOMContentLoaded', async () => {
  await getUrl()
  await checkHealth()
  document.getElementById('btn-ex').onclick = doExtract
  document.getElementById('btn-dl').onclick = doDownload
})

async function getUrl() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  if (tab?.url?.includes('watch?v=')) {
    url = tab.url
    document.getElementById('url').textContent = url
  } else if (tab?.url?.includes('playlist?list=')) {
    url = tab.url
    document.getElementById('url').textContent = '📋 ' + tab.url
    document.getElementById('btn-ex').textContent = 'Get Playlist Info'
  } else {
    document.getElementById('url').textContent = 'open a youtube video first'
    document.getElementById('btn-ex').disabled = true
  }
}

async function checkHealth() {
  let pythonOk = false
  let springOk = false
  try {
    const r = await fetch(`${PYTHON}/health`)
    const d = await r.json()
    pythonOk = d.status === 'ok'
  } catch {}
  try {
    const r = await fetch(`${SPRING}/api/health`)
    springOk = r.ok
  } catch {}
  const dot = document.getElementById('dot')
  dot.className = 'dot ' + (pythonOk && springOk ? 'up' : pythonOk ? 'warn' : 'down')
  dot.title = `Python: ${pythonOk ? '✓' : '✗'}  Spring: ${springOk ? '✓' : '✗'}`
}

async function doExtract() {
  btn('btn-ex', 'Loading...', true)
  hideErr()
  try {
    const r = await fetch(`${PYTHON}/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })
    const d = await r.json()
    if (!r.ok) return showErr(d.detail || 'Extract failed')
    renderFormats(d)
    show('s2'); hide('s1')
  } catch (e) {
    showErr('Python service offline: ' + e.message)
    btn('btn-ex', 'Get Qualities', false)
  }
}

function renderFormats(d) {
  const qlist = document.getElementById('qlist')
  const asel  = document.getElementById('asel')
  qlist.innerHTML = ''
  asel.innerHTML  = ''

  const order = ['2160p','1440p','1080p','720p','480p','360p','240p','144p']
  const seen  = {}
  d.formats.filter(f => f.type === 'video').forEach(f => {
    if (!seen[f.quality] || f.ext === 'mp4') seen[f.quality] = f
  })
  const sorted = order.map(q => seen[q]).filter(Boolean)
  d.formats.filter(f => f.type === 'combined').forEach(f => sorted.push(f))

  sorted.forEach(f => {
    const el = document.createElement('div')
    el.className = 'qi'
    el.dataset.itag    = f.itag
    el.dataset.quality = f.quality || f.resolution || f.itag
    el.innerHTML = `
      <span class="qi-q">${f.quality || f.resolution || f.itag}</span>
      <span class="qi-m">${f.ext} · ${f.filesize_mb || '?'} mb</span>
    `
    el.onclick = () => {
      document.querySelectorAll('.qi').forEach(x => x.classList.remove('sel'))
      el.classList.add('sel')
      vItag = f.itag
    }
    qlist.appendChild(el)
  })

  d.formats.filter(f => f.type === 'audio').forEach(f => {
    const o = document.createElement('option')
    o.value = f.itag
    o.textContent = `${f.quality || 'audio'} · ${f.ext} · ${f.filesize_mb || '?'} mb`
    asel.appendChild(o)
  })

  const best = d.formats.find(f => f.itag === '140')
  if (best) asel.value = '140'
  aItag = asel.value
  asel.onchange = () => { aItag = asel.value }
}

async function doDownload() {
  if (!vItag) return showErr('Select a video quality first')
  if (!aItag) return showErr('Select an audio track')

  const qualityLabel = document.querySelector('.qi.sel')?.dataset.quality || vItag
  show('s3'); hide('s2'); hideErr()
  updateProgress('downloading', '0%', 'sending to backend...', '', 0)

  try {
    const r = await fetch(`${SPRING}/api/download/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        youtubeUrl: url,
        videoItag:  vItag,
        audioItag:  aItag,
        quality:    qualityLabel,
        format:     'mp4'
      })
    })

    if (!r.ok) {
      const d = await r.json()
      return showErr(d.message || d.errorMessage || 'Spring Boot error')
    }

    const d = await r.json()
    const jobId = d.jobId
    chrome.storage.local.set({ activeJob: jobId })
    chrome.runtime.sendMessage({ type: 'TRACK_JOB', jobId })
    pollSpring(jobId)

  } catch (e) {
    showErr('Spring Boot offline — ' + e.message)
  }
}

function pollSpring(jobId) {
  const pctMap = {
    pending: 5, queued: 10, extracting: 15,
    downloading: 55, merging: 85, completed: 100,
    failed: 0, error: 0,
  }

  const t = setInterval(async () => {
    try {
      const r = await fetch(`${SPRING}/api/download/status/${jobId}`)
      const d = await r.json()
      const status  = (d.status || '').toLowerCase()
      const pct     = pctMap[status] ?? 20
      const message = d.message || d.errorMessage || status

      if (status === 'downloading') {
        const p     = (message.match(/(\d+\.\d+)%/) || [])[1]
        const speed = (message.match(/at\s+([^\s]+)/) || [])[1]
        const eta   = (message.match(/ETA\s+([^\s]+)/) || [])[1]
        const label = message.startsWith('Video') ? 'Video stream' : 'Audio stream'
        updateProgress('downloading', p ? p+'%' : '...', eta||'...', speed||'', p ? parseFloat(p) : 20, label)

      } else if (status === 'merging') {
        updateProgress('merging', '90%', 'almost done', '', 90, 'Merging streams')

      } else if (status === 'completed') {
        clearInterval(t)
        chrome.storage.local.remove('activeJob')
        updateProgress('done', '100%', 'complete!', '', 100, 'Done')

        const fileUrl = `${PYTHON}/files/${jobId}_final.mp4`
        chrome.downloads.download({
          url:      fileUrl,
          filename: `streamforge_${jobId}.mp4`,
          saveAs:   true
        })

        document.getElementById('dlwrap').innerHTML = `
          <div class="msg-done">✓ Download complete</div>
          <button class="dl" onclick="chrome.downloads.download({
            url: '${fileUrl}',
            filename: 'streamforge_${jobId}.mp4',
            saveAs: true
          })">↓ Save Again</button>`

      } else if (status === 'failed' || status === 'error') {
        clearInterval(t)
        showErr(message)
      } else {
        updateProgress(status, pct+'%', message, '', pct, status)
      }
    } catch {}
  }, 1500)
}

function updateProgress(status, pct, eta, speed, pctNum, stream = '') {
  document.getElementById('prog-label').textContent =
    status === 'merging'    ? 'Merging'    :
    status === 'done'       ? 'Complete'   :
    status === 'extracting' ? 'Extracting' : 'Downloading'
  document.getElementById('prog-pct').textContent    = pct
  document.getElementById('prog-eta').textContent    = eta ? `ETA ${eta}` : ''
  document.getElementById('prog-stream').textContent = stream
  document.getElementById('prog-speed').textContent  = speed || ''
  document.getElementById('bar').style.width         = pctNum + '%'
}

function btn(id, txt, dis) {
  const el = document.getElementById(id)
  el.textContent = txt
  el.disabled = dis
}

function show(id) { document.getElementById(id).classList.remove('hidden') }
function hide(id) { document.getElementById(id).classList.add('hidden') }
function showErr(m) {
  const e = document.getElementById('err')
  e.textContent = m
  e.classList.remove('hidden')
}
function hideErr() { document.getElementById('err').classList.add('hidden') }