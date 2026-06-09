const API = 'http://localhost:8001'
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
  try {
    const r = await fetch(`${API}/health`)
    const d = await r.json()
    document.getElementById('dot').className = 'dot ' + (d.status === 'ok' ? 'up' : 'down')
  } catch {
    document.getElementById('dot').className = 'dot down'
  }
}

async function doExtract() {
  btn('btn-ex', 'Loading...', true)
  hideErr()
  try {
    const r = await fetch(`${API}/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    })
    const d = await r.json()
    if (!r.ok) return showErr(d.detail)

    if (d.url_type === 'playlist') {
      renderPlaylist(d)
    } else {
      renderFormats(d)
      show('s2'); hide('s1')
    }
  } catch (e) {
    showErr('Backend offline — is Python service running?')
    btn('btn-ex', 'Get Qualities', false)
  }
}

// ── Playlist ──────────────────────────────────────────────────────────────────
function renderPlaylist(d) {
  const body = document.getElementById('s1')
  body.innerHTML = `
    <div class="lbl">Playlist — ${d.count} videos</div>
    <div style="font-size:13px;font-weight:600;margin-bottom:10px;color:#111">${d.playlist_title}</div>
    <div class="lbl">Select Quality for All</div>
    <select id="pl-quality" style="width:100%;background:#f9f9f9;border:1.5px solid #eee;border-radius:6px;color:#111;padding:8px 10px;font-family:inherit;font-size:12px;margin-bottom:10px;outline:none;">
      <option value="137+140">1080p (MP4)</option>
      <option value="136+140">720p (MP4)</option>
      <option value="135+140">480p (MP4)</option>
      <option value="18">360p (Combined)</option>
    </select>
    <button class="btn" onclick="downloadPlaylist('${d.playlist_title}')">Download All ${d.count} Videos</button>
    <div style="font-size:10px;color:#bbb;margin-top:8px;text-align:center">Each video = separate job</div>
  `
}

async function downloadPlaylist(title) {
  showErr('Playlist download — coming in next version. Download videos individually for now.')
}

// ── Single Video ──────────────────────────────────────────────────────────────
function renderFormats(d) {
  const qlist = document.getElementById('qlist')
  const asel  = document.getElementById('asel')
  qlist.innerHTML = ''
  asel.innerHTML  = ''

  const order = ['2160p','1440p','1080p','720p','480p','360p','240p','144p']
  const seen = {}
  d.formats.filter(f => f.type === 'video').forEach(f => {
    if (!seen[f.quality] || f.ext === 'mp4') seen[f.quality] = f
  })

  const sorted = order.map(q => seen[q]).filter(Boolean)
  d.formats.filter(f => f.type === 'combined').forEach(f => sorted.push(f))

  sorted.forEach(f => {
    const el = document.createElement('div')
    el.className = 'qi'
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
  const jobId = 'job_' + Math.random().toString(36).slice(2, 9)
  show('s3'); hide('s2'); hideErr()
  updateProgress('downloading', '0%', 'starting...', '', 0)

  try {
    const r = await fetch(`${API}/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, video_itag: vItag, audio_itag: aItag, job_id: jobId })
    })
    if (!r.ok) { const d = await r.json(); return showErr(d.detail) }
    chrome.storage.local.set({ activeJob: jobId })
    poll(jobId)
  } catch (e) { showErr('Failed: ' + e.message) }
}

function poll(jobId) {
  const t = setInterval(async () => {
    try {
      const r = await fetch(`${API}/status/${jobId}`)
      const d = await r.json()

      if (d.status === 'downloading') {
        const msg   = d.message || ''
        const pct   = (msg.match(/(\d+\.\d+)%/) || [])[1]
        const speed = (msg.match(/at\s+([^\s]+)/) || [])[1]
        const eta   = (msg.match(/ETA\s+([^\s]+)/) || [])[1]
        const label = msg.startsWith('Video') ? 'Video stream' : 'Audio stream'
        updateProgress('downloading', pct ? pct+'%' : '...', eta||'...', speed||'', pct ? parseFloat(pct) : 0, label)

      } else if (d.status === 'merging') {
        updateProgress('merging', '99%', 'almost done', '', 99, 'Merging streams')

      } else if (d.status === 'done') {
        clearInterval(t)
        chrome.runtime.sendMessage({ type: 'DOWNLOAD_DONE' })
        chrome.storage.local.remove('activeJob')
        updateProgress('done', '100%', 'complete!', '', 100, 'Done')

        // ── Use chrome.downloads API — opens native Save As dialog ──
        const fileUrl = `${API}/files/${jobId}_final.mp4`
        chrome.downloads.download({
          url: fileUrl,
          filename: `streamforge_${jobId}.mp4`,
          saveAs: true        // ← opens "Save As" dialog so user picks location
        })

        document.getElementById('dlwrap').innerHTML = `
          <div class="msg-done">✓ Download complete — save dialog opened</div>
          <button class="dl" onclick="reDownload('${fileUrl}', '${jobId}')">↓ Save Again</button>`

      } else if (d.status === 'error') {
        clearInterval(t)
        showErr(d.message)
      }
    } catch {}
  }, 1500)
}

function reDownload(fileUrl, jobId) {
  chrome.downloads.download({
    url: fileUrl,
    filename: `streamforge_${jobId}.mp4`,
    saveAs: true
  })
}

function updateProgress(status, pct, eta, speed, pctNum, stream = '') {
  document.getElementById('prog-label').textContent =
    status === 'merging' ? 'Merging' : status === 'done' ? 'Complete' : 'Downloading'
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
function showErr(m) { const e = document.getElementById('err'); e.textContent = m; e.classList.remove('hidden') }
function hideErr()  { document.getElementById('err').classList.add('hidden') }