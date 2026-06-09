chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url?.includes('youtube.com/watch')) {
    chrome.scripting.executeScript({
      target: { tabId },
      files: ['content/content.js']
    }).catch(() => {})
  }
})

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'DOWNLOAD_DONE') {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'StreamForge AI',
      message: 'Download complete — file ready.'
    })
  }
})