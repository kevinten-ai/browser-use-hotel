// hotel-compare/page-agent-version/content.js
/**
 * 酒店比价 — Content Script
 * ===========================
 * Runs inside each hotel-platform tab.
 *
 * Responsibilities:
 *   1. Receive RUN_AGENT from background, inject page-agent IIFE, execute task.
 *   2. Listen for page-agent activity events and forward structured AGENT_STEP
 *      messages to background (platform, stepNum, goal, actions, url).
 *   3. Return AGENT_RESULT when the agent finishes.
 */

/** Counter for agent steps within the current execution */
let stepCounter = 0;

// ---------------------------------------------------------------------------
// Message listener — from background.js
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'RUN_AGENT') {
    stepCounter = 0;
    runPageAgent(msg.task, msg.platform);
    sendResponse({ received: true });
  }
  return true;
});

// ---------------------------------------------------------------------------
// Agent execution
// ---------------------------------------------------------------------------

async function runPageAgent(task, platform) {
  try {
    log(platform, 'page-agent 初始化中...');

    const result = await injectAndRun(task, platform);

    chrome.runtime.sendMessage({
      type: 'AGENT_RESULT',
      result,
    });
  } catch (err) {
    log(platform, `错误: ${err.message}`);
    chrome.runtime.sendMessage({
      type: 'AGENT_RESULT',
      result: { success: false, data: err.message },
    });
  }
}

// ---------------------------------------------------------------------------
// Inject page-agent into the page context and run
// ---------------------------------------------------------------------------

function injectAndRun(task, platform) {
  return new Promise((resolve, reject) => {
    // Listen for messages from the injected page-context script
    window.addEventListener('message', function handler(event) {
      if (event.data?.type === 'PAGE_AGENT_RESULT') {
        window.removeEventListener('message', handler);
        resolve(event.data.result);
      }
      if (event.data?.type === 'PAGE_AGENT_LOG') {
        log(platform, event.data.text);
      }
      if (event.data?.type === 'PAGE_AGENT_STEP') {
        // Structured step data from the page context
        handlePageAgentStep(platform, event.data.step);
      }
    });

    // Inject the page-agent library
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('lib/page-agent.iife.js');
    script.onload = () => {
      const execScript = document.createElement('script');
      execScript.textContent = `
        (async () => {
          try {
            const agent = new window.PageAgent.PageAgentCore({
              provider: 'openai',
              model: 'glm-4-plus',
              apiKey: '${getApiKey()}',
              baseURL: 'https://open.bigmodel.cn/api/paas/v4',
              maxSteps: 25,
              language: 'zh-CN',
            });

            let stepNum = 0;

            // Listen for activity events and post structured step data
            agent.addEventListener('activity', (e) => {
              const a = e.detail;
              if (a.type === 'executing') {
                stepNum++;
                // Post structured step info to the content script
                window.postMessage({
                  type: 'PAGE_AGENT_STEP',
                  step: {
                    stepNum: stepNum,
                    goal: a.tool || '',
                    actions: [a.tool + '(' + JSON.stringify(a.input || {}).substring(0, 200) + ')'],
                    url: window.location.href,
                  },
                }, '*');

                // Also post legacy log for backward compatibility
                window.postMessage({
                  type: 'PAGE_AGENT_LOG',
                  text: 'Step ' + stepNum + ': ' + a.tool + '(' + JSON.stringify(a.input).substring(0, 80) + ')',
                }, '*');
              }
            });

            const result = await agent.execute(${JSON.stringify(task)});
            window.postMessage({
              type: 'PAGE_AGENT_RESULT',
              result: { success: true, data: JSON.stringify(result) },
            }, '*');
            agent.dispose();
          } catch (err) {
            window.postMessage({
              type: 'PAGE_AGENT_RESULT',
              result: { success: false, data: err.message },
            }, '*');
          }
        })();
      `;
      document.head.appendChild(execScript);
    };
    script.onerror = () => reject(new Error('Failed to load page-agent library'));
    document.head.appendChild(script);
  });
}

// ---------------------------------------------------------------------------
// Forward structured step data to background.js
// ---------------------------------------------------------------------------

function handlePageAgentStep(platform, step) {
  stepCounter++;
  chrome.runtime.sendMessage({
    type: 'AGENT_STEP',
    platform,
    stepNum: step.stepNum || stepCounter,
    goal: step.goal || '',
    actions: step.actions || [],
    url: step.url || window.location.href,
  }).catch(() => {});
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getApiKey() {
  // TODO: 从 chrome.storage 读取用户配置的 API Key
  return 'YOUR_ZHIPUAI_API_KEY';
}

function log(platform, text) {
  chrome.runtime.sendMessage({
    type: 'AGENT_LOG',
    platform,
    text,
  }).catch(() => {});
}
