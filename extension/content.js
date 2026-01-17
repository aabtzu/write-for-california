// WFC New Reply Notifier - Content Script
// Monitors for "new reply" badges on Substack DBD posts

(function() {
  'use strict';

  const CHECK_INTERVAL = 5000; // Check every 5 seconds
  let lastNotificationTime = 0;
  const NOTIFICATION_COOLDOWN = 30000; // Don't spam notifications - 30 second cooldown

  // Play a notification sound
  function playSound() {
    const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2teleQcAEJ3p+KV1JAANrfD/vYYvAAiy8/+1eTQAEK7t/8F/IgYUsej8zIwcABq28P+2eSsAFqri+9SWEgAktO/9unQgAByt5fu/fB8ADKrq/8WDIgAOsOz/xYEeABSy7f/CgB4AEq7o/8uGFgAWtOr8zpIUABC26v7LixkAErPr/8qIGgAUtOv+y4oVABa17P/JiRgAE7Pr/8yLFgAVtez/yYoYABO06/7MjBQAF7bs/8iKFwAUtOz+zIwWABW17f/IihcAFLTs/syMFgAVte3/yIkYABOz7P7NjRUAFrXt/8iJFwAUtOz+zI0VABW27f/HiRcAE7Ts/syNFQAVtu3/x4kXABO07P7MjRUAFbbt/8eJFwATtOz+zI0VABW27f/HiRcAE7Ts/syNFQA=');
    audio.volume = 0.5;
    audio.play().catch(() => {}); // Ignore errors if audio can't play
  }

  // Show desktop notification
  function showNotification(count) {
    const now = Date.now();
    if (now - lastNotificationTime < NOTIFICATION_COOLDOWN) {
      return; // Still in cooldown
    }
    lastNotificationTime = now;

    // Try to use the Notifications API
    if (Notification.permission === 'granted') {
      new Notification('WFC New Replies!', {
        body: `${count} new ${count === 1 ? 'reply' : 'replies'} detected`,
        icon: 'https://writeforcalifornia.com/favicon.ico',
        requireInteraction: false
      });
      playSound();
    } else if (Notification.permission !== 'denied') {
      Notification.requestPermission().then(permission => {
        if (permission === 'granted') {
          showNotification(count);
        }
      });
    }
  }

  // Find and count "new reply" badges
  function checkForNewReplies() {
    // Look for elements that indicate new replies
    // Substack uses various patterns like "X new reply" or "X new replies"
    const newReplyElements = document.querySelectorAll('[class*="new-repl"], [class*="newRepl"]');

    // Also look for text content matching "new reply/replies"
    const allElements = document.body.querySelectorAll('*');
    let totalNewReplies = 0;

    for (const el of allElements) {
      // Check direct text content only (not children)
      if (el.childNodes.length === 1 && el.childNodes[0].nodeType === Node.TEXT_NODE) {
        const text = el.textContent.trim();
        const match = text.match(/^(\d+)\s+new\s+repl(?:y|ies)$/i);
        if (match) {
          totalNewReplies += parseInt(match[1], 10);
        }
      }
    }

    return totalNewReplies;
  }

  // Main monitoring loop
  let previousCount = 0;

  function monitor() {
    const count = checkForNewReplies();

    if (count > previousCount && count > 0) {
      console.log(`[WFC Notifier] Detected ${count} new replies`);
      showNotification(count);
    }

    previousCount = count;
  }

  // Request notification permission on load
  if (Notification.permission === 'default') {
    Notification.requestPermission();
  }

  // Start monitoring
  console.log('[WFC Notifier] Started monitoring for new replies');
  setInterval(monitor, CHECK_INTERVAL);

  // Also monitor for DOM changes (in case new reply badges are added dynamically)
  const observer = new MutationObserver(() => {
    const count = checkForNewReplies();
    if (count > previousCount && count > 0) {
      console.log(`[WFC Notifier] DOM change detected ${count} new replies`);
      showNotification(count);
      previousCount = count;
    }
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true
  });

})();
