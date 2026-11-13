/**
 * ContextAI – Intelligent Conversational Assistant
 * Frontend Client Architecture & State Controller
 */

document.addEventListener('DOMContentLoaded', () => {
  // Application State
  const state = {
    currentConversationId: null,
    conversations: [],
    isGenerating: false,
    theme: localStorage.getItem('contextai-theme') || 'dark',
    activeModal: null,
    targetConvIdForModal: null,
  };

  // DOM Elements
  const DOM = {
    // Theme
    themeToggleBtn: document.getElementById('themeToggleBtn'),
    headerThemeBtn: document.getElementById('headerThemeBtn'),
    themeToggleText: document.getElementById('themeToggleText'),
    moonIcon: document.querySelector('.moon-icon'),
    sunIcon: document.querySelector('.sun-icon'),
    headerMoon: document.querySelector('.header-moon'),
    headerSun: document.querySelector('.header-sun'),
    hljsDark: document.getElementById('hljs-dark-theme'),
    hljsLight: document.getElementById('hljs-light-theme'),

    // Sidebar
    sidebar: document.getElementById('sidebar'),
    sidebarBackdrop: document.getElementById('sidebarBackdrop'),
    mobileMenuBtn: document.getElementById('mobileMenuBtn'),
    newChatBtn: document.getElementById('newChatBtn'),
    conversationSearchInput: document.getElementById('conversationSearchInput'),
    searchClearBtn: document.getElementById('searchClearBtn'),
    conversationList: document.getElementById('conversationList'),
    historyEmpty: document.getElementById('historyEmpty'),
    settingsBtn: document.getElementById('settingsBtn'),

    // Main Chat
    activeChatTitle: document.getElementById('activeChatTitle'),
    headerRenameBtn: document.getElementById('headerRenameBtn'),
    clearChatBtn: document.getElementById('clearChatBtn'),
    chatViewport: document.getElementById('chatViewport'),
    welcomeScreen: document.getElementById('welcomeScreen'),
    messagesContainer: document.getElementById('messagesContainer'),
    typingIndicator: document.getElementById('typingIndicator'),
    scrollAnchor: document.getElementById('scrollAnchor'),

    // Input Area
    chatForm: document.getElementById('chatForm'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    sendIcon: document.querySelector('.send-icon'),
    sendSpinner: document.querySelector('.send-spinner'),

    // Modals
    renameModal: document.getElementById('renameModal'),
    renameInput: document.getElementById('renameInput'),
    renameSaveBtn: document.getElementById('renameSaveBtn'),
    renameCancelBtn: document.getElementById('renameCancelBtn'),
    renameModalClose: document.getElementById('renameModalClose'),

    deleteModal: document.getElementById('deleteModal'),
    deleteConvTitle: document.getElementById('deleteConvTitle'),
    deleteConfirmBtn: document.getElementById('deleteConfirmBtn'),
    deleteCancelBtn: document.getElementById('deleteCancelBtn'),
    deleteModalClose: document.getElementById('deleteModalClose'),

    clearModal: document.getElementById('clearModal'),
    clearConfirmBtn: document.getElementById('clearConfirmBtn'),
    clearCancelBtn: document.getElementById('clearCancelBtn'),
    clearModalClose: document.getElementById('clearModalClose'),

    settingsModal: document.getElementById('settingsModal'),
    settingsCloseBtn: document.getElementById('settingsCloseBtn'),
    settingsModalClose: document.getElementById('settingsModalClose'),
    settingsApiStatus: document.getElementById('settingsApiStatus'),
    settingsDbStatus: document.getElementById('settingsDbStatus'),

    // Toast Container
    toastContainer: document.getElementById('toastContainer'),
  };

  // Configure marked.js options
  if (typeof marked !== 'undefined') {
    marked.setOptions({
      gfm: true,
      breaks: true,
      highlight: function (code, lang) {
        if (typeof hljs !== 'undefined') {
          const language = hljs.getLanguage(lang) ? lang : 'plaintext';
          return hljs.highlight(code, { language }).value;
        }
        return code;
      },
    });
  }

  /* ==========================================================================
     1. INITIALIZATION & THEME HANDLING
     ========================================================================== */
  function init() {
    applyTheme(state.theme);
    bindEvents();
    autoResizeTextarea();
    fetchConversations();
    checkSystemHealth();
  }

  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('contextai-theme', theme);

    const isDark = theme === 'dark';
    if (DOM.moonIcon && DOM.sunIcon) {
      DOM.moonIcon.style.display = isDark ? 'block' : 'none';
      DOM.sunIcon.style.display = isDark ? 'none' : 'block';
    }
    if (DOM.headerMoon && DOM.headerSun) {
      DOM.headerMoon.style.display = isDark ? 'block' : 'none';
      DOM.headerSun.style.display = isDark ? 'none' : 'block';
    }
    if (DOM.themeToggleText) {
      DOM.themeToggleText.textContent = isDark ? 'Light Mode' : 'Dark Mode';
    }

    // Toggle highlight.js themes
    if (DOM.hljsDark && DOM.hljsLight) {
      DOM.hljsDark.disabled = !isDark;
      DOM.hljsLight.disabled = isDark;
    }
  }

  function toggleTheme() {
    const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
  }

  /* ==========================================================================
     2. EVENT LISTENERS
     ========================================================================== */
  function bindEvents() {
    // Theme Toggles
    DOM.themeToggleBtn.addEventListener('click', toggleTheme);
    DOM.headerThemeBtn.addEventListener('click', toggleTheme);

    // Mobile Sidebar
    DOM.mobileMenuBtn.addEventListener('click', openSidebar);
    DOM.sidebarBackdrop.addEventListener('click', closeSidebar);

    // New Chat Action
    DOM.newChatBtn.addEventListener('click', startNewChat);

    // Search
    let searchDebounceTimer;
    DOM.conversationSearchInput.addEventListener('input', (e) => {
      const term = e.target.value.trim();
      DOM.searchClearBtn.style.display = term ? 'block' : 'none';
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        fetchConversations(term);
      }, 250);
    });

    DOM.searchClearBtn.addEventListener('click', () => {
      DOM.conversationSearchInput.value = '';
      DOM.searchClearBtn.style.display = 'none';
      fetchConversations();
    });

    // Chat Form & Input Handling
    DOM.messageInput.addEventListener('input', () => {
      autoResizeTextarea();
      updateSendButtonState();
    });

    DOM.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!state.isGenerating && DOM.messageInput.value.trim().length > 0) {
          submitUserMessage();
        }
      }
    });

    DOM.chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!state.isGenerating && DOM.messageInput.value.trim().length > 0) {
        submitUserMessage();
      }
    });

    // Suggested Starter Prompts
    document.querySelectorAll('.suggested-card').forEach((card) => {
      card.addEventListener('click', () => {
        const prompt = card.getAttribute('data-prompt');
        if (prompt && !state.isGenerating) {
          DOM.messageInput.value = prompt;
          autoResizeTextarea();
          updateSendButtonState();
          submitUserMessage();
        }
      });
    });

    // Header actions
    DOM.activeChatTitle.addEventListener('click', openRenameForActive);
    DOM.headerRenameBtn.addEventListener('click', openRenameForActive);
    DOM.clearChatBtn.addEventListener('click', openClearModal);

    // Settings Modal
    DOM.settingsBtn.addEventListener('click', openSettingsModal);
    DOM.settingsCloseBtn.addEventListener('click', closeModals);
    DOM.settingsModalClose.addEventListener('click', closeModals);

    // Rename Modal Actions
    DOM.renameModalClose.addEventListener('click', closeModals);
    DOM.renameCancelBtn.addEventListener('click', closeModals);
    DOM.renameSaveBtn.addEventListener('click', handleRenameSubmit);
    DOM.renameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleRenameSubmit();
      }
    });

    // Delete Modal Actions
    DOM.deleteModalClose.addEventListener('click', closeModals);
    DOM.deleteCancelBtn.addEventListener('click', closeModals);
    DOM.deleteConfirmBtn.addEventListener('click', handleDeleteSubmit);

    // Clear Modal Actions
    DOM.clearModalClose.addEventListener('click', closeModals);
    DOM.clearCancelBtn.addEventListener('click', closeModals);
    DOM.clearConfirmBtn.addEventListener('click', handleClearSubmit);

    // Close modal when clicking on overlay backdrop
    document.querySelectorAll('.modal-overlay').forEach((modal) => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          closeModals();
        }
      });
    });

    // Global Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
      // Ctrl+K or Cmd+K -> New Chat
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        startNewChat();
      }
      // Escape -> Close Modals & Mobile Sidebar
      if (e.key === 'Escape') {
        closeModals();
        closeSidebar();
      }
    });
  }

  /* ==========================================================================
     3. SIDEBAR & CONVERSATIONS LIST
     ========================================================================== */
  function openSidebar() {
    DOM.sidebar.classList.add('open');
    DOM.sidebarBackdrop.classList.add('active');
  }

  function closeSidebar() {
    DOM.sidebar.classList.remove('open');
    DOM.sidebarBackdrop.classList.remove('active');
  }

  async function fetchConversations(searchQuery = '') {
    try {
      const url = searchQuery
        ? `/api/conversations?q=${encodeURIComponent(searchQuery)}`
        : '/api/conversations';
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to load conversations');

      const data = await res.json();
      state.conversations = data.conversations || [];
      renderConversationList(state.conversations);
    } catch (err) {
      console.error('Error fetching conversations:', err);
      showToast('Could not load conversation history', 'error');
    }
  }

  function renderConversationList(conversations) {
    DOM.conversationList.innerHTML = '';

    if (!conversations || conversations.length === 0) {
      DOM.historyEmpty.style.display = 'block';
      return;
    }

    DOM.historyEmpty.style.display = 'none';

    conversations.forEach((conv) => {
      const item = document.createElement('div');
      item.className = `conversation-item ${conv.id === state.currentConversationId ? 'active' : ''}`;
      item.setAttribute('data-id', conv.id);

      item.innerHTML = `
        <div class="conversation-item-main" title="${escapeHtml(conv.title)}">
          <svg class="conversation-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          <span class="conversation-item-title">${escapeHtml(conv.title)}</span>
        </div>
        <div class="conversation-item-actions">
          <button class="item-action-btn btn-rename" title="Rename conversation" data-id="${conv.id}">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
          </button>
          <button class="item-action-btn btn-delete" title="Delete conversation" data-id="${conv.id}">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      `;

      // Click to select
      item.querySelector('.conversation-item-main').addEventListener('click', () => {
        loadConversation(conv.id);
        closeSidebar();
      });

      // Rename button
      item.querySelector('.btn-rename').addEventListener('click', (e) => {
        e.stopPropagation();
        openRenameModal(conv.id, conv.title);
      });

      // Delete button
      item.querySelector('.btn-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        openDeleteModal(conv.id, conv.title);
      });

      DOM.conversationList.appendChild(item);
    });
  }

  function startNewChat() {
    if (state.isGenerating) return;
    state.currentConversationId = null;
    DOM.activeChatTitle.textContent = 'New Conversation';
    DOM.messagesContainer.innerHTML = '';
    DOM.welcomeScreen.style.display = 'flex';

    // Deselect any active item in sidebar
    document.querySelectorAll('.conversation-item').forEach((el) => {
      el.classList.remove('active');
    });

    closeSidebar();
    DOM.messageInput.value = '';
    autoResizeTextarea();
    updateSendButtonState();
    DOM.messageInput.focus();
  }

  async function loadConversation(convId) {
    if (state.isGenerating || convId === state.currentConversationId) return;

    try {
      const res = await fetch(`/api/conversations/${convId}`);
      if (!res.ok) throw new Error('Conversation not found');

      const data = await res.json();
      const conv = data.conversation;

      state.currentConversationId = conv.id;
      DOM.activeChatTitle.textContent = conv.title;

      // Update sidebar active indicator
      document.querySelectorAll('.conversation-item').forEach((el) => {
        el.classList.toggle('active', el.getAttribute('data-id') === conv.id);
      });

      // Render messages
      DOM.messagesContainer.innerHTML = '';
      if (conv.messages && conv.messages.length > 0) {
        DOM.welcomeScreen.style.display = 'none';
        conv.messages.forEach((msg) => {
          appendMessageBubble(msg.role, msg.content, msg.created_at, false);
        });
      } else {
        DOM.welcomeScreen.style.display = 'flex';
      }

      scrollToBottom();
      DOM.messageInput.focus();
    } catch (err) {
      console.error('Error loading conversation:', err);
      showToast('Could not load conversation', 'error');
    }
  }

  /* ==========================================================================
     4. CHAT MESSAGING & API INTEGRATION
     ========================================================================== */
  async function submitUserMessage() {
    const text = DOM.messageInput.value.trim();
    if (!text || state.isGenerating) return;

    // Transition to loading state
    setGeneratingState(true);

    // Hide welcome hero on first message
    DOM.welcomeScreen.style.display = 'none';

    // Append user message immediately
    appendMessageBubble('user', text, new Date().toISOString(), true);

    // Clear and reset textarea
    DOM.messageInput.value = '';
    autoResizeTextarea();

    // Show typing indicator
    showTypingIndicator();
    scrollToBottom();

    try {
      const payload = {
        message: text,
      };
      if (state.currentConversationId) {
        payload.conversation_id = state.currentConversationId;
      }

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      hideTypingIndicator();

      if (!res.ok) {
        const errorMsg = data.error || 'Failed to generate response. Please try again.';
        appendErrorMessage(errorMsg);
        showToast(errorMsg, 'error');
        return;
      }

      // If new conversation, update current conversation ID & title
      if (!state.currentConversationId || state.currentConversationId !== data.conversation_id) {
        state.currentConversationId = data.conversation_id;
        DOM.activeChatTitle.textContent = data.conversation_title || 'New Conversation';
        fetchConversations();
      } else if (data.conversation_title && DOM.activeChatTitle.textContent !== data.conversation_title) {
        DOM.activeChatTitle.textContent = data.conversation_title;
        fetchConversations();
      }

      // Append assistant response
      appendMessageBubble('assistant', data.message.content, data.message.created_at, true);
      scrollToBottom();
    } catch (err) {
      console.error('Network or chat error:', err);
      hideTypingIndicator();
      const errText = 'Unable to connect to the ContextAI backend service. Please check your connection and configuration.';
      appendErrorMessage(errText);
      showToast(errText, 'error');
    } finally {
      setGeneratingState(false);
      DOM.messageInput.focus();
    }
  }

  async function handleRegenerateResponse() {
    if (state.isGenerating || !state.currentConversationId) return;

    setGeneratingState(true);
    showTypingIndicator();
    scrollToBottom();

    try {
      const res = await fetch(`/api/conversations/${state.currentConversationId}/regenerate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      const data = await res.json();
      hideTypingIndicator();

      if (!res.ok) {
        showToast(data.error || 'Failed to regenerate response', 'error');
        return;
      }

      // Remove the last assistant message bubble from DOM
      const assistantRows = DOM.messagesContainer.querySelectorAll('.assistant-row:not(#typingIndicator .assistant-row)');
      if (assistantRows.length > 0) {
        assistantRows[assistantRows.length - 1].remove();
      }

      // Append new regenerated assistant message bubble
      appendMessageBubble('assistant', data.message.content, data.message.created_at, true);
      scrollToBottom();
      showToast('Response regenerated', 'success');
    } catch (err) {
      console.error('Regenerate error:', err);
      hideTypingIndicator();
      showToast('Failed to regenerate response', 'error');
    } finally {
      setGeneratingState(false);
    }
  }

  /* ==========================================================================
     5. MESSAGE RENDERING & CODE BLOCKS
     ========================================================================== */
  function appendMessageBubble(role, content, timestamp, shouldAnimate = true) {
    const isUser = role === 'user';
    const row = document.createElement('div');
    row.className = `message-row ${isUser ? 'user-row' : 'assistant-row'}`;
    if (!shouldAnimate) row.style.animation = 'none';

    // Avatar
    const avatar = document.createElement('div');
    avatar.className = `message-avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}`;
    avatar.innerHTML = isUser
      ? '<span>U</span>'
      : `<img src="/static/images/logo.svg" alt="ContextAI" width="22" height="22">`;

    // Content wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';

    // Bubble
    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${isUser ? 'user-bubble' : 'assistant-bubble'}`;

    if (isUser) {
      bubble.textContent = content;
    } else {
      bubble.innerHTML = renderMarkdown(content);
      setupCodeBlocks(bubble);
    }

    wrapper.appendChild(bubble);

    // Timestamp
    if (timestamp) {
      const timeSpan = document.createElement('span');
      timeSpan.className = 'message-timestamp';
      timeSpan.textContent = formatTimestamp(timestamp);
      wrapper.appendChild(timeSpan);
    }

    // Assistant Action Toolbar (Copy & Regenerate)
    if (!isUser) {
      const actionsBar = document.createElement('div');
      actionsBar.className = 'message-actions-bar';

      // Copy response button
      const copyBtn = document.createElement('button');
      copyBtn.className = 'msg-action-btn';
      copyBtn.innerHTML = `
        <svg class="btn-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span>Copy</span>
      `;
      copyBtn.addEventListener('click', () => {
        copyToClipboard(content, copyBtn);
      });

      // Regenerate response button
      const regenBtn = document.createElement('button');
      regenBtn.className = 'msg-action-btn';
      regenBtn.innerHTML = `
        <svg class="btn-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="1 4 1 10 7 10"></polyline>
          <polyline points="23 20 23 14 17 14"></polyline>
          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"></path>
        </svg>
        <span>Regenerate</span>
      `;
      regenBtn.addEventListener('click', handleRegenerateResponse);

      actionsBar.appendChild(copyBtn);
      actionsBar.appendChild(regenBtn);
      wrapper.appendChild(actionsBar);
    }

    row.appendChild(avatar);
    row.appendChild(wrapper);

    DOM.messagesContainer.appendChild(row);
  }

  function appendErrorMessage(errorText) {
    const row = document.createElement('div');
    row.className = 'message-row assistant-row';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar assistant-avatar';
    avatar.innerHTML = `<img src="/static/images/logo.svg" alt="ContextAI" width="22" height="22">`;

    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble assistant-bubble';
    bubble.style.borderColor = 'var(--accent-rose)';
    bubble.innerHTML = `
      <div style="color: var(--accent-rose); font-weight: 500; display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>Error Encountered</span>
      </div>
      <p style="margin: 0; color: var(--text-secondary); font-size: 0.88rem;">${escapeHtml(errorText)}</p>
    `;

    wrapper.appendChild(bubble);
    row.appendChild(avatar);
    row.appendChild(wrapper);

    DOM.messagesContainer.appendChild(row);
  }

  function renderMarkdown(rawText) {
    if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
      const rawHtml = marked.parse(rawText);
      return DOMPurify.sanitize(rawHtml);
    }
    return escapeHtml(rawText);
  }

  function setupCodeBlocks(container) {
    const pres = container.querySelectorAll('pre');
    pres.forEach((pre) => {
      const code = pre.querySelector('code');
      if (!code) return;

      // Extract language if specified in class
      let lang = 'code';
      const classes = code.className.split(' ');
      for (const cls of classes) {
        if (cls.startsWith('language-')) {
          lang = cls.replace('language-', '');
          break;
        }
      }

      // Create code-block-container
      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-container';

      // Header bar with language & copy button
      const header = document.createElement('div');
      header.className = 'code-block-header';
      header.innerHTML = `
        <span>${escapeHtml(lang)}</span>
        <button class="code-copy-btn" title="Copy code snippet">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          <span>Copy code</span>
        </button>
      `;

      const copyBtn = header.querySelector('.code-copy-btn');
      copyBtn.addEventListener('click', () => {
        copyToClipboard(code.innerText, copyBtn);
      });

      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(header);
      wrapper.appendChild(pre);

      // Syntax highlight with highlight.js
      if (typeof hljs !== 'undefined') {
        hljs.highlightElement(code);
      }
    });
  }

  /* ==========================================================================
     6. CONVERSATION MANAGEMENT (RENAME, DELETE, CLEAR)
     ========================================================================== */
  function openRenameForActive() {
    if (!state.currentConversationId) return;
    openRenameModal(state.currentConversationId, DOM.activeChatTitle.textContent);
  }

  function openRenameModal(convId, currentTitle) {
    state.targetConvIdForModal = convId;
    DOM.renameInput.value = currentTitle;
    DOM.renameModal.style.display = 'flex';
    DOM.renameInput.focus();
    DOM.renameInput.select();
  }

  async function handleRenameSubmit() {
    const newTitle = DOM.renameInput.value.trim();
    if (!newTitle || !state.targetConvIdForModal) return;

    try {
      const res = await fetch(`/api/conversations/${state.targetConvIdForModal}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle }),
      });

      if (!res.ok) throw new Error('Rename failed');

      if (state.currentConversationId === state.targetConvIdForModal) {
        DOM.activeChatTitle.textContent = newTitle;
      }

      fetchConversations();
      closeModals();
      showToast('Conversation renamed', 'success');
    } catch (err) {
      console.error('Rename error:', err);
      showToast('Failed to rename conversation', 'error');
    }
  }

  function openDeleteModal(convId, title) {
    state.targetConvIdForModal = convId;
    DOM.deleteConvTitle.textContent = title;
    DOM.deleteModal.style.display = 'flex';
  }

  async function handleDeleteSubmit() {
    if (!state.targetConvIdForModal) return;

    try {
      const res = await fetch(`/api/conversations/${state.targetConvIdForModal}`, {
        method: 'DELETE',
      });

      if (!res.ok) throw new Error('Delete failed');

      const wasActive = state.currentConversationId === state.targetConvIdForModal;
      closeModals();
      fetchConversations();

      if (wasActive) {
        startNewChat();
      }

      showToast('Conversation deleted', 'success');
    } catch (err) {
      console.error('Delete error:', err);
      showToast('Failed to delete conversation', 'error');
    }
  }

  function openClearModal() {
    if (!state.currentConversationId) return;
    DOM.clearModal.style.display = 'flex';
  }

  async function handleClearSubmit() {
    if (!state.currentConversationId) return;

    try {
      const res = await fetch(`/api/conversations/${state.currentConversationId}/clear`, {
        method: 'POST',
      });

      if (!res.ok) throw new Error('Clear failed');

      DOM.messagesContainer.innerHTML = '';
      DOM.welcomeScreen.style.display = 'flex';
      closeModals();
      fetchConversations();
      showToast('Conversation messages cleared', 'success');
    } catch (err) {
      console.error('Clear error:', err);
      showToast('Failed to clear conversation', 'error');
    }
  }

  function openSettingsModal() {
    DOM.settingsModal.style.display = 'flex';
    checkSystemHealth();
  }

  function closeModals() {
    DOM.renameModal.style.display = 'none';
    DOM.deleteModal.style.display = 'none';
    DOM.clearModal.style.display = 'none';
    DOM.settingsModal.style.display = 'none';
    state.targetConvIdForModal = null;
  }

  async function checkSystemHealth() {
    try {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error('Health check error');

      const data = await res.json();
      if (DOM.settingsApiStatus) {
        DOM.settingsApiStatus.textContent = data.openai_configured ? 'Active (API Key Configured)' : 'Missing API Key in .env';
        DOM.settingsApiStatus.style.color = data.openai_configured ? 'var(--accent-emerald)' : 'var(--accent-rose)';
      }
      if (DOM.settingsDbStatus) {
        DOM.settingsDbStatus.textContent = data.database === 'connected' ? 'Connected (SQLite)' : data.database;
        DOM.settingsDbStatus.style.color = data.database === 'connected' ? 'var(--accent-emerald)' : 'var(--accent-rose)';
      }
    } catch (err) {
      if (DOM.settingsApiStatus) DOM.settingsApiStatus.textContent = 'Service Unreachable';
      if (DOM.settingsDbStatus) DOM.settingsDbStatus.textContent = 'Error';
    }
  }

  /* ==========================================================================
     7. UI HELPERS & UTILITIES
     ========================================================================== */
  function autoResizeTextarea() {
    DOM.messageInput.style.height = 'auto';
    DOM.messageInput.style.height = Math.min(DOM.messageInput.scrollHeight, 200) + 'px';
  }

  function updateSendButtonState() {
    const hasText = DOM.messageInput.value.trim().length > 0;
    DOM.sendBtn.disabled = !hasText || state.isGenerating;
  }

  function setGeneratingState(isGenerating) {
    state.isGenerating = isGenerating;
    DOM.sendBtn.disabled = isGenerating;
    DOM.messageInput.disabled = isGenerating;

    if (isGenerating) {
      DOM.sendIcon.style.display = 'none';
      DOM.sendSpinner.style.display = 'block';
    } else {
      DOM.sendIcon.style.display = 'block';
      DOM.sendSpinner.style.display = 'none';
      updateSendButtonState();
    }
  }

  function showTypingIndicator() {
    DOM.typingIndicator.style.display = 'block';
  }

  function hideTypingIndicator() {
    DOM.typingIndicator.style.display = 'none';
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      DOM.scrollAnchor.scrollIntoView({ behavior: 'smooth', block: 'end' });
    });
  }

  function copyToClipboard(text, triggerBtn) {
    navigator.clipboard.writeText(text).then(() => {
      const origHtml = triggerBtn.innerHTML;
      triggerBtn.innerHTML = `
        <svg class="btn-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent-emerald)">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span style="color:var(--accent-emerald)">Copied!</span>
      `;
      setTimeout(() => {
        triggerBtn.innerHTML = origHtml;
      }, 2000);
    }).catch((err) => {
      console.error('Clipboard copy error:', err);
      showToast('Failed to copy to clipboard', 'error');
    });
  }

  function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
        ${type === 'error'
          ? '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>'
          : '<polyline points="20 6 9 17 4 12"></polyline>'
        }
      </svg>
      <span>${escapeHtml(message)}</span>
    `;

    DOM.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.25s ease-out';
      setTimeout(() => toast.remove(), 250);
    }, 3500);
  }

  function formatTimestamp(isoString) {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // Launch App
  init();
});
