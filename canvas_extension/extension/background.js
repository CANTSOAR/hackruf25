// Background script just injects the content script on Canvas pages

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ lastExport: null });
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url.includes("instructure.com")) {
    chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"]
    });
  }
});
