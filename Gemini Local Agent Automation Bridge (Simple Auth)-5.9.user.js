// ==UserScript==
// @name         Gemini Local Agent Automation Bridge (Simple Auth)
// @namespace    http://tampermonkey.net/
// @version      5.9
// @description  Automates the loop between Gemini/AI Studio/LMArena. Fixes re-execution on page refresh by seeding history.
// @author       AI-Assisted (Patched by Genius Student)
// @match        https://gemini.google.com/*
// @match        https://aistudio.google.com/*
// @match        https://lmarena.ai/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// ==/UserScript==

(function() {
    'use strict';

    // === 配置区域 ===
    // !!! 必须与 Python 服务器端的 Config.API_SECRET_KEY 保持一致 !!!
    const API_SECRET_KEY = "E8b2a1a2e9b1f0c1d1a9E8FF7aka55riotr0knlMMNF6a7b8c9d0e1f2a3b4c5d6e7f8a9b0";
    const AGENT_SERVER_URL = 'http://127.0.0.1:5005';
    const API_URL = `${AGENT_SERVER_URL}/api`;
    // ================

    const CHECK_INTERVAL = 2500;
    // LMArena 点击后等待
    const LMARENA_CLICK_WAIT_MS = 10;
    const GEMINI_TYPE_DELAY_MS = 0;


    // 全局状态
    let isExecuting = false;
    let agentStatus = 'disconnected'; // Possible values: disconnected, connected, error
    let automationEnabled = true;

    // [MODIFIED V5.9] 移除 Set，使用单一状态变量
    let lastExecutedCommandContent = null;

    if (API_SECRET_KEY === "YOUR_SUPER_SECRET_LOCAL_API_KEY") {
        console.error("[Agent Bridge] 尚未配置API_SECRET_KEY，请编辑脚本并设置密钥。");
        alert("Agent Bridge Error: API_SECRET_KEY not configured.");
        return;
    }

    console.log('[Agent Bridge] Script injected (Simple Auth Version 5.9).');

    // --- UI 注入与状态显示 ---

    function createControlPanel() {
        const panel = document.createElement('div');
        panel.id = 'agent-bridge-panel';
        panel.style.cssText = `
            position: fixed; bottom: 10px; right: 10px; padding: 10px;
            border-radius: 5px; font-size: 12px; font-weight: bold; z-index: 10000;
            background-color: #333; color: white; box-shadow: 0 4px 8px rgba(0,0,0,0.5);
        `;

        const statusDiv = document.createElement('div');
        statusDiv.id = 'agent-bridge-status';
        statusDiv.style.cssText = `
            margin-bottom: 8px; padding: 5px; border-radius: 3px;
            text-align: center; cursor: pointer;
        `;

        const toggleButton = document.createElement('button');
        toggleButton.id = 'agent-bridge-toggle';
        toggleButton.style.cssText = `
            cursor: pointer; padding: 5px 10px; border: none;
            border-radius: 3px; width: 100%; color: white;
        `;

        panel.appendChild(statusDiv);
        panel.appendChild(toggleButton);
        document.body.appendChild(panel);

        toggleButton.addEventListener('click', toggleAutomation);
        statusDiv.addEventListener('click', checkServerStatus);
        updateStatusIndicator();
    }

    function toggleAutomation() {
        automationEnabled = !automationEnabled;
        console.log(`[Agent Bridge] Automation ${automationEnabled ? 'Enabled' : 'Disabled'}.`);
        updateStatusIndicator();
    }

    function updateStatusIndicator() {
        const statusDiv = document.getElementById('agent-bridge-status');
        const toggleButton = document.getElementById('agent-bridge-toggle');
        if (!statusDiv || !toggleButton) return;

        let bgColor, text;
        switch (agentStatus) {
            case 'connected':
                bgColor = '#4CAF50'; // Green
                text = '🟢 Agent Ready';
                break;
            case 'error':
                bgColor = '#F44336'; // Red
                text = '🔴 Agent Error/Config Issue';
                break;
            case 'disconnected':
            default:
                bgColor = '#FFA500'; // Orange
                text = '🟠 Agent Disconnected';
                break;
        }

        if (isExecuting) {
            bgColor = '#2196F3'; // Blue
            text = '🔵 Executing...';
        }

        statusDiv.style.backgroundColor = bgColor;
        statusDiv.textContent = text;

        if (automationEnabled) {
            toggleButton.textContent = 'Pause Automation';
            toggleButton.style.backgroundColor = '#f44336';
        } else {
            toggleButton.textContent = 'Resume Automation';
            toggleButton.style.backgroundColor = '#4CAF50';
        }
    }

    // --- 服务器通信 ---

    async function checkServerStatus() {
        console.log('[Agent Bridge] Checking server status...');
        GM_xmlhttpRequest({
            method: "GET",
            url: `${API_URL}/status`,
            onload: function(response) {
                if (response.status === 200) {
                    const data = JSON.parse(response.responseText);
                    agentStatus = data.configured ? 'connected' : 'error';
                } else {
                    agentStatus = 'disconnected';
                }
                updateStatusIndicator();
            },
            onerror: function(error) {
                agentStatus = 'disconnected';
                updateStatusIndicator();
            }
        });
    }

    async function executeCommandOnServer(commandObject) {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: "POST",
                url: `${API_URL}/execute_command`,
                headers: {
                    "Content-Type": "application/json",
                    "X-API-Key": API_SECRET_KEY
                },
                data: JSON.stringify(commandObject),
                onload: function(response) {
                    if (response.status === 200) {
                        resolve(JSON.parse(response.responseText));
                    } else if (response.status === 403) {
                        reject('Forbidden (Invalid API Key)');
                    } else {
                        reject(`Server error: ${response.status}`);
                    }
                },
                onerror: function(error) {
                    reject('Network error or server not running');
                }
            });
        });
    }

    // [REWRITTEN V5.9.1 - Genius Student Patch]
    // 修复了逐字 `await` 导致的 0ms 延迟依然缓慢的问题
    // 我们模拟“分块”输入，而不是“逐字”输入，速度提高 50-100 倍
    async function simulateTyping(element, text, chunkDelay) {
        // 获取原生的 'value' 属性设置器 (用于 <textarea>)
        const nativeValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype,
            "value"
        )?.set;

        // 1. 先清空
        if (element.tagName === 'TEXTAREA' && nativeValueSetter) {
            nativeValueSetter.call(element, "");
        } else {
            // 适用于 contenteditable div
            element.textContent = "";
            const p = element.querySelector('p');
            if (p) p.innerHTML = '<br>'; // 重置
        }
        element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
        // 在清空后等待一个 tick
        await new Promise(resolve => setTimeout(resolve, chunkDelay));

        // 2. 分块输入 (Chunked Input)
        const CHUNK_SIZE = 15; // 每次输入 50 个字符。足够快，也足够像“输入”
        let currentIndex = 0;

        while (currentIndex < text.length) {
            // 我们必须设置从头开始的完整文本，否则 Gemini 的 rich editor 会出问题
            const currentFullText = text.substring(0, currentIndex + CHUNK_SIZE);

            if (element.tagName === 'TEXTAREA' && nativeValueSetter) {
                nativeValueSetter.call(element, currentFullText);
            } else {
                const p = element.querySelector('p');
                if (p) {
                    p.textContent = currentFullText;
                } else {
                    element.textContent = currentFullText; // 备用
                }
            }

            element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
            currentIndex += CHUNK_SIZE;

            // 关键：只在 *每个分块后* await，而不是每个字符后
            await new Promise(resolve => setTimeout(resolve, chunkDelay));
        }

        // 确保最终文本是完整的 (处理最后一块不足 CHUNK_SIZE 的情况)
        if (currentIndex < text.length) {
            if (element.tagName === 'TEXTAREA' && nativeValueSetter) {
                 nativeValueSetter.call(element, text);
            } else {
                const p = element.querySelector('p');
                if (p) p.textContent = text;
                else element.textContent = text;
            }
            element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
        }
    }

    // [REWRITTEN V5.0 for LMArena Support]
    function findInputArea() {
        const selectors = [
            'div.ql-editor[contenteditable="true"]',               // Gemini
            'textarea.textarea[placeholder="Start typing a prompt"]', // AI Studio
            'textarea[placeholder="Ask followup…"]'                  // LMArena
        ];
        return document.querySelector(selectors.join(', '));
    }

    // [REWRITTEN V5.0 for LMArena Support]
    function findSendButton() {
        // 1. Try Gemini UI selectors
        const geminiSelectors = [
            'button[aria-label="发送"]',
            'button.send-button',
            'button[aria-label="Send message"]'
        ];
        let sendButton = document.querySelector(geminiSelectors.join(', '));
        if (sendButton) return sendButton;

        // 2. Try AI Studio UI selector (span "Run")
        const spans = document.querySelectorAll('span.label');
        for (const span of spans) {
            if (span.textContent.trim() === 'Run') {
                const button = span.closest('button');
                if (button) return button;
            }
        }

        // 3. Try LMArena UI selector (Arrow Up SVG)
        const lmaButtonIcon = document.querySelector('svg.lucide-arrow-up');
        if (lmaButtonIcon) {
            const lmaButton = lmaButtonIcon.closest('button[type="submit"]');
            if (lmaButton) return lmaButton;
        }

        return null; // Not found
    }

    // [REWRITTEN V5.0 for LMArena Support]
    function isModelGenerating() {
        // 1. Check for Gemini (gemini.google.com) stop icon
        const geminiStopIcon = document.querySelector('mat-icon[fonticon="stop"]');
        if (geminiStopIcon) {
            const parentDiv = geminiStopIcon.closest('.stop-icon');
            if (parentDiv) {
                const parentStyle = window.getComputedStyle(parentDiv);
                if (parentStyle.display === 'none' || parentStyle.visibility === 'hidden') return false;
            }
            const iconStyle = window.getComputedStyle(geminiStopIcon);
            if (iconStyle.display === 'none' || iconStyle.visibility === 'hidden') return false;
            return geminiStopIcon.offsetParent !== null;
        }

        // 2. Check for AI Studio (aistudio.google.com) stop icon
        const aiStudioStopRect = document.querySelector('rect.stoppable-stop');
        if (aiStudioStopRect) {
            const parent = aiStudioStopRect.closest('.inner');
            if (parent) {
                const parentStyle = window.getComputedStyle(parent);
                if (parentStyle.display === 'none' || parentStyle.visibility === 'hidden') {
                    return false;
                }
            }
            return aiStudioStopRect.offsetParent !== null;
        }

        // 3. Check for LMArena (lmarena.ai) spinner
        const lmaSpinner = document.querySelector('div.animate-spin');
        if (lmaSpinner) {
            // Check if the spinner itself or its canvas child is visible
            return lmaSpinner.offsetParent !== null;
        }

        return false; // None found
    }

    // [MODIFIED V5.7 for Gemini Typing Strategy]
    async function injectResultAndSend(resultObject) {
        const inputArea = findInputArea();
        if (!inputArea) {
            console.error('[Agent Bridge] Cannot find input area. Automation failed.');
            return false;
        }
        const formattedResult = "```json\n" + JSON.stringify(resultObject, null, 2) + "\n```";
        const isLMArena = window.location.hostname === 'lmarena.ai';
        const isGemini = window.location.hostname === 'gemini.google.com';
        const event = new Event('input', { bubbles: true, cancelable: true });

        if (isGemini) {
            // Gemini 策略: Focus/Click + High-Speed Typing
            console.log('[Agent Bridge] Gemini: Simulating focus/click...');
            inputArea.focus();
            inputArea.click();
            await new Promise(resolve => setTimeout(resolve, LMARENA_CLICK_WAIT_MS));

            console.log(`[Agent Bridge] Gemini: Starting high-speed typing (${GEMINI_TYPE_DELAY_MS}ms/char)...`);
            await simulateTyping(inputArea, formattedResult, GEMINI_TYPE_DELAY_MS);
            console.log('[Agent Bridge] Gemini: Typing complete.');

        } else if (isLMArena && inputArea.tagName === 'TEXTAREA') {
            // LMArena 策略: Focus/Click + Native Paste (v5.6)
            console.log('[Agent Bridge] LMArena: Simulating focus/click...');
            inputArea.focus();
            inputArea.click();
            await new Promise(resolve => setTimeout(resolve, LMARENA_CLICK_WAIT_MS));

            console.log('[Agent Bridge] LMArena: Using native setter paste.');
            const nativeValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
            nativeValueSetter.call(inputArea, formattedResult);
            inputArea.dispatchEvent(event);

        } else {
            // AI Studio 策略: Native Paste + Focus (v5.6)
            // (也适用于非 TEXTAREA 的 LMArena 备用情况)
            console.log('[Agent Bridge] AI Studio/Backup: Using native setter/textContent paste.');
            if (inputArea.tagName === 'TEXTAREA') {
                const nativeValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                nativeValueSetter.call(inputArea, formattedResult);
            } else {
                inputArea.textContent = formattedResult;
            }
            inputArea.dispatchEvent(event);
            inputArea.focus();
        }

        // A short delay to ensure the send button becomes enabled *after* action
        setTimeout(() => {
            const updatedSendButton = findSendButton();
            if (updatedSendButton && !updatedSendButton.disabled) {
                updatedSendButton.click();
                console.log('[Agent Bridge] Result submitted back to model.');
            } else {
                console.error('[Agent Bridge] Send button remains disabled (or not found) after input.');
                alert("Agent Bridge finished execution, but failed to auto-submit (button disabled/not found).");
            }
        }, 500);
        return true;
    }

    // [MODIFIED V5.9] 修复刷新重执行 (Fix Refresh Re-execution)
    function findAndExecuteNewCommand() {
        if (isModelGenerating()) {
            return;
        }
        if (isExecuting || !automationEnabled || agentStatus === 'disconnected' || agentStatus === 'error') {
            return;
        }

        const codeBlocks = document.querySelectorAll(
            'model-response pre code, model-response markdown-code-block code, ' +         // Gemini
            '.model-response-view pre code, .model-response-view markdown-code-block code, ' + // Gemini (alt)
            'mat-expansion-panel pre code, ' +                                               // AI Studio
            'div[data-code-block="true"] pre code'                                           // LMArena
        );

        if (codeBlocks.length === 0) return;

        const latestCodeBlock = codeBlocks[codeBlocks.length - 1];

        // 1. Get original content
        const originalContent = latestCodeBlock.textContent.trim();

        // 2. [V5.9 CHECK] 如果这个内容和我们已知的最后一条内容相同，则跳过
        if (originalContent === lastExecutedCommandContent) {
            return; // Already known (either just executed or seeded from history)
        }

        // 3. 这是一个新命令，立即将其注册为 "已知"
        lastExecutedCommandContent = originalContent;

        let commandObject;
        let contentToParse = originalContent;
        const isGemini = window.location.hostname === 'gemini.google.com';

        // 4. [V5.8] 移除 Gemini 引用
        if (isGemini) {
            const citationRegex = /\[cite.+?\]/g;
            contentToParse = originalContent.replace(citationRegex, '').trim();
            if (contentToParse !== originalContent) {
                 console.log('[Agent Bridge] Gemini citations removed for parsing.');
            }
        }

        // 5. 解析
        try {
            if (contentToParse.startsWith('{') && contentToParse.endsWith('}')) {
                commandObject = JSON.parse(contentToParse);
            } else {
                 console.log('[Agent Bridge] Last block is not a JSON command, ignoring.');
                return; // 最后一个代码块不是 JSON 命令
            }
        } catch (e) {
            console.warn('[Agent Bridge] JSON parsing failed, ignoring block.', e.message);
            return; // 无效的 JSON
        }

        // 6. 执行
        if (commandObject && commandObject.command && commandObject.args) {
            console.log('[Agent Bridge] Found new command. Executing:', commandObject.command);
            execute(commandObject);
            return;
        }
    }

    // [MODIFIED V5.6] injectResultAndSend is now async
    async function execute(commandObject) {
        isExecuting = true;
        updateStatusIndicator();
        try {
            const result = await executeCommandOnServer(commandObject);
            console.log('[Agent Bridge] Execution finished. Result:', result.status);
            // Wait for the injection/paste to complete before continuing
            await injectResultAndSend(result);
        } catch (error) {
            // === MODIFIED CATCH BLOCK (V4.5) ===
            // Check for the specific network error caused by a server restart
            if (error === 'Network error or server not running') {
                console.error('[Agent Bridge] Execution failed (server restarting?):', error);
                // Set status to disconnected, the checkServerStatus loop will pick it up
                agentStatus = 'disconnected';
                // DO NOT alert or inject. Just wait for reconnection.
            } else {
                // For all other errors (e.g., Invalid API Key, 500 error), notify the user and AI
                console.error('[Agent Bridge] Execution failed (Critical):', error);
                alert(`Agent Bridge Error: ${error}. Please check the Python server console.`);
                const errorResult = { status: 'error', message: `Automation Bridge Failure: ${error}`};
                // We still await this to ensure the error message is pasted
                await injectResultAndSend(errorResult);
            }
            // ===================================
        } finally {
            isExecuting = false;
            // This will correctly reflect the 'disconnected' or 'error' state
            setTimeout(updateStatusIndicator, 1000);
        }
    }

    // [NEW V5.9] 在初始化时填充历史记录
    function initializeHistory() {
        const codeBlocks = document.querySelectorAll(
            'model-response pre code, model-response markdown-code-block code, ' +
            '.model-response-view pre code, .model-response-view markdown-code-block code, ' +
            'mat-expansion-panel pre code, ' +
            'div[data-code-block="true"] pre code'
        );

        if (codeBlocks.length > 0) {
            const lastBlock = codeBlocks[codeBlocks.length - 1];
            // 只记录最后一块的内容，以防止刷新时重执行
            lastExecutedCommandContent = lastBlock.textContent.trim();
            console.log('[Agent Bridge] Initialized. Last command from history is seeded to prevent re-execution.');
        } else {
             console.log('[Agent Bridge] Initialized. No history found.');
        }
    }


    // --- 初始化 ---

    function initialize() {
        createControlPanel();
        checkServerStatus();

        // [MODIFIED V5.9] 先填充历史，再开始轮询
        initializeHistory();

        setInterval(checkServerStatus, 30000); // Check status every 30s
        setInterval(findAndExecuteNewCommand, CHECK_INTERVAL); // Check for commands every 2.5s
    }

    if (document.readyState === 'complete') {
        setTimeout(initialize, 2000);
    } else {
        window.addEventListener('load', () => setTimeout(initialize, 2000));
    }

})();