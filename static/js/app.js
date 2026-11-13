/**
 * MemoraAI – Advanced Futuristic Frontend Controller
 * Tagline: "Every Conversation Matters. Every Memory Counts."
 */

document.addEventListener('DOMContentLoaded', () => {
  // Application State
  const state = {
    currentConversationId: null,
    conversations: [],
    stagedFiles: [], // Array of { id, original_filename, file_size, file_category }
    isGenerating: false,
    theme: localStorage.getItem('memoraai-theme') || 'dark',
    fontSize: localStorage.getItem('memoraai-font-size') || 'normal',
    chatDensity: localStorage.getItem('memoraai-density') || 'comfortable',
    activeModal: null,
    targetConvIdForModal: null,
    libraryCategory: 'all',
  };

  // DOM Elements
  const DOM = {
    appContainer: document.getElementById('appContainer'),
    dragDropOverlay: document.getElementById('dragDropOverlay'),

    // Theme & Display
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
    historyCountBadge: document.getElementById('historyCountBadge'),
    fileLibraryBtn: document.getElementById('fileLibraryBtn'),
    totalFilesBadge: document.getElementById('totalFilesBadge'),
    settingsBtn: document.getElementById('settingsBtn'),

    // Header
    activeChatTitle: document.getElementById('activeChatTitle'),
    headerRenameBtn: document.getElementById('headerRenameBtn'),
    modelBadgeText: document.getElementById('modelBadgeText'),
    headerFilesBadge: document.getElementById('headerFilesBadge'),
    headerFilesCount: document.getElementById('headerFilesCount'),
    exportChatBtn: document.getElementById('exportChatBtn'),
    clearChatBtn: document.getElementById('clearChatBtn'),

    // Chat Viewport
    chatViewport: document.getElementById('chatViewport'),
    welcomeScreen: document.getElementById('welcomeScreen'),
    messagesContainer: document.getElementById('messagesContainer'),
    typingIndicator: document.getElementById('typingIndicator'),
    typingStatusText: document.getElementById('typingStatusText'),
    scrollAnchor: document.getElementById('scrollAnchor'),

    // Input & Attachments
    chatForm: document.getElementById('chatForm'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    sendIcon: document.querySelector('.send-icon'),
    sendSpinner: document.querySelector('.send-spinner'),
    attachBtn: document.getElementById('attachBtn'),
    filePickerInput: document.getElementById('filePickerInput'),
    attachmentsPreviewStrip: document.getElementById('attachmentsPreviewStrip'),
    stagedAttachmentsList: document.getElementById('stagedAttachmentsList'),
    inputStatusNote: document.getElementById('inputStatusNote'),

    // File Library Modal
    fileLibraryModal: document.getElementById('fileLibraryModal'),
    fileLibraryCloseBtn: document.getElementById('fileLibraryCloseBtn'),
    fileLibraryDoneBtn: document.getElementById('fileLibraryDoneBtn'),
    librarySearchInput: document.getElementById('librarySearchInput'),
    libraryFilterPills: document.getElementById('libraryFilterPills'),
    libraryFilesGrid: document.getElementById('libraryFilesGrid'),
    libraryEmptyState: document.getElementById('libraryEmptyState'),
    libraryUploadBtn: document.getElementById('libraryUploadBtn'),

    // Document Preview Modal
    documentPreviewModal: document.getElementById('documentPreviewModal'),
    previewFilename: document.getElementById('previewFilename'),
    previewMetaBar: document.getElementById('previewMetaBar'),
    previewTextBox: document.getElementById('previewTextBox'),
    previewModalCloseBtn: document.getElementById('previewModalCloseBtn'),
    previewCopyBtn: document.getElementById('previewCopyBtn'),
    previewDoneBtn: document.getElementById('previewDoneBtn'),

    // Settings Modal
    settingsModal: document.getElementById('settingsModal'),
    settingsModalClose: document.getElementById('settingsModalClose'),
    settingsCloseBtn: document.getElementById('settingsCloseBtn'),
    settingThemeDarkBtn: document.getElementById('settingThemeDarkBtn'),
    settingThemeLightBtn: document.getElementById('settingThemeLightBtn'),
    settingsProviderVal: document.getElementById('settingsProviderVal'),
    settingsModelVal: document.getElementById('settingsModelVal'),
    settingsApiStatus: document.getElementById('settingsApiStatus'),
    settingsDbStatus: document.getElementById('settingsDbStatus'),

    // Conversation Actions Modals
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

    // Toast Container
    toastContainer: document.getElementById('toastContainer'),
  };

  // Configure marked.js
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
     1. INITIALIZATION & THEME/FONT SETTINGS
     ========================================================================== */
  function init() {
    applyTheme(state.theme);
    applyFontSize(state.fontSize);
    applyChatDensity(state.chatDensity);
    bindEvents();
    autoResizeTextarea();
    fetchConversations();
    updateTotalFilesCount();
    checkSystemHealth();
  }

  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('memoraai-theme', theme);

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

    if (DOM.settingThemeDarkBtn && DOM.settingThemeLightBtn) {
      DOM.settingThemeDarkBtn.classList.toggle('active', isDark);
      DOM.settingThemeLightBtn.classList.toggle('active', !isDark);
    }

    if (DOM.hljsDark && DOM.hljsLight) {
      DOM.hljsDark.disabled = !isDark;
      DOM.hljsLight.disabled = isDark;
    }
  }

  function toggleTheme() {
    const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
  }

  function applyFontSize(size) {
    state.fontSize = size;
    document.documentElement.setAttribute('data-font-size', size);
    localStorage.setItem('memoraai-font-size', size);

    document.querySelectorAll('[data-font]').forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-font') === size);
    });
  }

  function applyChatDensity(density) {
    state.chatDensity = density;
    document.documentElement.setAttribute('data-chat-density', density);
    localStorage.setItem('memoraai-density', density);

    document.querySelectorAll('[data-density]').forEach((btn) => {
      btn.classList.toggle('active', btn.getAttribute('data-density') === density);
    });
  }

  /* ==========================================================================
     2. EVENT BINDINGS
     ========================================================================== */
  function bindEvents() {
    // Theme toggles
    DOM.themeToggleBtn.addEventListener('click', toggleTheme);
    DOM.headerThemeBtn.addEventListener('click', toggleTheme);
    if (DOM.settingThemeDarkBtn) DOM.settingThemeDarkBtn.addEventListener('click', () => applyTheme('dark'));
    if (DOM.settingThemeLightBtn) DOM.settingThemeLightBtn.addEventListener('click', () => applyTheme('light'));

    // Font & Density buttons
    document.querySelectorAll('[data-font]').forEach((btn) => {
      btn.addEventListener('click', () => applyFontSize(btn.getAttribute('data-font')));
    });
    document.querySelectorAll('[data-density]').forEach((btn) => {
      btn.addEventListener('click', () => applyChatDensity(btn.getAttribute('data-density')));
    });

    // Mobile Sidebar
    DOM.mobileMenuBtn.addEventListener('click', openSidebar);
    DOM.sidebarBackdrop.addEventListener('click', closeSidebar);

    // New Chat
    DOM.newChatBtn.addEventListener('click', startNewChat);

    // Search Conversations
    let searchDebounce;
    DOM.conversationSearchInput.addEventListener('input', (e) => {
      const term = e.target.value.trim();
      DOM.searchClearBtn.style.display = term ? 'block' : 'none';
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => fetchConversations(term), 250);
    });

    DOM.searchClearBtn.addEventListener('click', () => {
      DOM.conversationSearchInput.value = '';
      DOM.searchClearBtn.style.display = 'none';
      fetchConversations();
    });

    // File Attachment Interactions
    DOM.attachBtn.addEventListener('click', () => DOM.filePickerInput.click());
    DOM.filePickerInput.addEventListener('change', handleFilePickerChange);

    // Drag and Drop Global Overlay
    window.addEventListener('dragenter', handleDragEnter);
    window.addEventListener('dragover', handleDragOver);
    DOM.dragDropOverlay.addEventListener('dragleave', handleDragLeave);
    DOM.dragDropOverlay.addEventListener('drop', handleDrop);

    // Input Handling
    DOM.messageInput.addEventListener('input', () => {
      autoResizeTextarea();
      updateSendButtonState();
    });

    DOM.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (canSubmitMessage()) {
          submitUserMessage();
        }
      }
    });

    DOM.chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      if (canSubmitMessage()) {
        submitUserMessage();
      }
    });

    // Suggested Starter Prompt Cards
    document.querySelectorAll('.suggested-card').forEach((card) => {
      card.addEventListener('click', () => {
        const action = card.getAttribute('data-action');
        const prompt = card.getAttribute('data-prompt') || '';

        if (action === 'upload-trigger') {
          DOM.filePickerInput.click();
          if (prompt) {
            DOM.messageInput.value = prompt;
            autoResizeTextarea();
            updateSendButtonState();
          }
        } else if (prompt && !state.isGenerating) {
          DOM.messageInput.value = prompt;
          autoResizeTextarea();
          updateSendButtonState();
          submitUserMessage();
        }
      });
    });

    // Header Actions
    DOM.activeChatTitle.addEventListener('click', openRenameForActive);
    DOM.headerRenameBtn.addEventListener('click', openRenameForActive);
    DOM.exportChatBtn.addEventListener('click', handleExportChat);
    DOM.clearChatBtn.addEventListener('click', openClearModal);

    // File Library Actions
    DOM.fileLibraryBtn.addEventListener('click', openFileLibraryModal);
    DOM.fileLibraryCloseBtn.addEventListener('click', closeModals);
    DOM.fileLibraryDoneBtn.addEventListener('click', closeModals);
    DOM.libraryUploadBtn.addEventListener('click', () => DOM.filePickerInput.click());

    DOM.librarySearchInput.addEventListener('input', (e) => {
      filterLibraryFiles(e.target.value.trim(), state.libraryCategory);
    });

    DOM.libraryFilterPills.querySelectorAll('.filter-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        DOM.libraryFilterPills.querySelectorAll('.filter-pill').forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        state.libraryCategory = pill.getAttribute('data-category');
        filterLibraryFiles(DOM.librarySearchInput.value.trim(), state.libraryCategory);
      });
    });

    // Document Preview Modal Actions
    DOM.previewModalCloseBtn.addEventListener('click', closeModals);
    DOM.previewDoneBtn.addEventListener('click', closeModals);
    DOM.previewCopyBtn.addEventListener('click', () => {
      copyToClipboard(DOM.previewTextBox.textContent, DOM.previewCopyBtn);
    });

    // Settings Modal
    DOM.settingsBtn.addEventListener('click', openSettingsModal);
    DOM.settingsCloseBtn.addEventListener('click', closeModals);
    DOM.settingsModalClose.addEventListener('click', closeModals);

    // Dialog Modal Actions
    DOM.renameModalClose.addEventListener('click', closeModals);
    DOM.renameCancelBtn.addEventListener('click', closeModals);
    DOM.renameSaveBtn.addEventListener('click', handleRenameSubmit);
    DOM.renameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleRenameSubmit();
      }
    });

    DOM.deleteModalClose.addEventListener('click', closeModals);
    DOM.deleteCancelBtn.addEventListener('click', closeModals);
    DOM.deleteConfirmBtn.addEventListener('click', handleDeleteSubmit);

    DOM.clearModalClose.addEventListener('click', closeModals);
    DOM.clearCancelBtn.addEventListener('click', closeModals);
    DOM.clearConfirmBtn.addEventListener('click', handleClearSubmit);

    // Close on overlay click
    document.querySelectorAll('.modal-overlay').forEach((modal) => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModals();
      });
    });

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        startNewChat();
      }
      if (e.key === 'Escape') {
        closeModals();
        closeSidebar();
        DOM.dragDropOverlay.classList.remove('active');
      }
    });
  }

  /* ==========================================================================
     3. FILE UPLOAD & ATTACHMENT HANDLING
     ========================================================================== */
  function handleDragEnter(e) {
    e.preventDefault();
    DOM.dragDropOverlay.classList.add('active');
  }

  function handleDragOver(e) {
    e.preventDefault();
  }

  function handleDragLeave(e) {
    e.preventDefault();
    if (e.relatedTarget === null || e.relatedTarget === document.documentElement) {
      DOM.dragDropOverlay.classList.remove('active');
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    DOM.dragDropOverlay.classList.remove('active');
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
      processFilesUpload(Array.from(e.dataTransfer.files));
    }
  }

  function handleFilePickerChange(e) {
    if (e.target.files && e.target.files.length > 0) {
      processFilesUpload(Array.from(e.target.files));
      DOM.filePickerInput.value = ''; // Reset input so same file can be selected again
    }
  }

  async function processFilesUpload(filesList) {
    if (!filesList || filesList.length === 0) return;

    DOM.inputStatusNote.textContent = 'Extracting and processing file content...';
    DOM.attachmentsPreviewStrip.style.display = 'block';

    const formData = new FormData();
    if (state.currentConversationId) {
      formData.append('conversation_id', state.currentConversationId);
    }

    filesList.forEach((file) => {
      formData.append('files', file);
      // Pre-render local staging card with uploading indicator
      renderStagedPlaceholder(file.name, file.size);
    });

    try {
      const res = await fetch('/api/files/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || 'File upload failed', 'error');
        DOM.inputStatusNote.textContent = 'File upload failed. Please try again.';
        renderStagedFiles();
        return;
      }

      // Add uploaded files to stagedFiles array
      if (data.files && data.files.length > 0) {
        data.files.forEach((f) => {
          if (!state.stagedFiles.some((sf) => sf.id === f.id)) {
            state.stagedFiles.push(f);
          }
        });

        // If upload created a new conversation
        if (data.conversation_id && !state.currentConversationId) {
          state.currentConversationId = data.conversation_id;
          fetchConversations();
        }

        renderStagedFiles();
        updateTotalFilesCount();
        showToast(`Uploaded ${data.files.length} file(s) successfully!`, 'success');
        DOM.inputStatusNote.textContent = 'Ready to chat about your files. Ask questions or summarize!';
      }

      if (data.errors && data.errors.length > 0) {
        showToast(data.errors.join('; '), 'error');
      }
    } catch (err) {
      console.error('File upload network error:', err);
      showToast('Network error while uploading files', 'error');
      DOM.inputStatusNote.textContent = 'File upload interrupted.';
    } finally {
      updateSendButtonState();
      DOM.messageInput.focus();
    }
  }

  function renderStagedPlaceholder(fileName, fileSize) {
    const card = document.createElement('div');
    card.className = 'staged-file-card uploading';
    const ext = fileName.split('.').pop().toLowerCase();
    card.innerHTML = `
      <div class="file-pill-icon ${ext}">${ext.slice(0, 3)}</div>
      <div class="staged-file-info">
        <span class="staged-file-name">${escapeHtml(fileName)}</span>
        <span class="staged-file-size">Extracting...</span>
      </div>
    `;
    DOM.stagedAttachmentsList.appendChild(card);
  }

  function renderStagedFiles() {
    DOM.stagedAttachmentsList.innerHTML = '';
    if (state.stagedFiles.length === 0) {
      DOM.attachmentsPreviewStrip.style.display = 'none';
      return;
    }

    DOM.attachmentsPreviewStrip.style.display = 'block';

    state.stagedFiles.forEach((file) => {
      const card = document.createElement('div');
      card.className = 'staged-file-card';
      const ext = file.original_filename.split('.').pop().toLowerCase();

      card.innerHTML = `
        <div class="file-pill-icon ${ext}">${ext.slice(0, 3)}</div>
        <div class="staged-file-info">
          <span class="staged-file-name" title="${escapeHtml(file.original_filename)}">${escapeHtml(file.original_filename)}</span>
          <span class="staged-file-size">${formatBytes(file.file_size)} • Ready</span>
        </div>
        <button type="button" class="staged-file-remove-btn" title="Remove attachment">&times;</button>
      `;

      card.querySelector('.staged-file-remove-btn').addEventListener('click', () => {
        removeStagedFile(file.id);
      });

      DOM.stagedAttachmentsList.appendChild(card);
    });
  }

  function removeStagedFile(fileId) {
    state.stagedFiles = state.stagedFiles.filter((f) => f.id !== fileId);
    renderStagedFiles();
    updateSendButtonState();
  }

  /* ==========================================================================
     4. CHAT MESSAGING & API INTEGRATION
     ========================================================================== */
  function canSubmitMessage() {
    const hasText = DOM.messageInput.value.trim().length > 0;
    const hasFiles = state.stagedFiles.length > 0;
    return (hasText || hasFiles) && !state.isGenerating;
  }

  async function submitUserMessage() {
    if (!canSubmitMessage()) return;

    const text = DOM.messageInput.value.trim();
    const attachedFiles = [...state.stagedFiles];
    const fileIds = attachedFiles.map((f) => f.id);

    setGeneratingState(true);
    DOM.welcomeScreen.style.display = 'none';

    // Append user message to feed with file badges
    appendMessageBubble('user', text || '[Attached Documents]', new Date().toISOString(), true, attachedFiles);

    // Reset input and clear staged files
    DOM.messageInput.value = '';
    state.stagedFiles = [];
    renderStagedFiles();
    autoResizeTextarea();

    // Show thinking indicator
    showTypingIndicator(fileIds.length > 0 ? 'Analyzing document content...' : 'MemoraAI is thinking...');
    scrollToBottom();

    try {
      const payload = {
        message: text,
        file_ids: fileIds,
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

      // Update active conversation ID and title
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
      DOM.inputStatusNote.textContent = 'MemoraAI remembers past turns in this conversation.';
    } catch (err) {
      console.error('Chat error:', err);
      hideTypingIndicator();
      const errText = 'Unable to connect to the MemoraAI service. Please check your network and configuration.';
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
    showTypingIndicator('Regenerating response with document context...');
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

      // Remove last assistant row from DOM
      const assistantRows = DOM.messagesContainer.querySelectorAll('.assistant-row:not(#typingIndicator .assistant-row)');
      if (assistantRows.length > 0) {
        assistantRows[assistantRows.length - 1].remove();
      }

      // Append new regenerated assistant message
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
     5. MESSAGE BUBBLES RENDERING & CODE BLOCKS
     ========================================================================== */
  function appendMessageBubble(role, content, timestamp, shouldAnimate = true, attachments = []) {
    const isUser = role === 'user';
    const row = document.createElement('div');
    row.className = `message-row ${isUser ? 'user-row' : 'assistant-row'}`;
    if (!shouldAnimate) row.style.animation = 'none';

    // Avatar
    const avatar = document.createElement('div');
    avatar.className = `message-avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}`;
    avatar.innerHTML = isUser
      ? '<span>U</span>'
      : `<img src="/static/images/memoraai-avatar.png" alt="MemoraAI" width="34" height="34">`;

    // Content wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';

    // If attachments present, render pills
    if (attachments && attachments.length > 0) {
      const pillsWrap = document.createElement('div');
      pillsWrap.className = 'message-attachments-pills';
      attachments.forEach((att) => {
        const pill = document.createElement('span');
        pill.className = 'msg-file-pill';
        pill.innerHTML = `
          <svg class="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          <span>${escapeHtml(att.filename || att.original_filename)}</span>
        `;
        pillsWrap.appendChild(pill);
      });
      wrapper.appendChild(pillsWrap);
    }

    // Message Bubble
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

    // Assistant Action Toolbar (Copy, Regenerate, Feedback)
    if (!isUser) {
      const actionsBar = document.createElement('div');
      actionsBar.className = 'message-actions-bar';

      const copyBtn = document.createElement('button');
      copyBtn.className = 'msg-action-btn';
      copyBtn.innerHTML = `
        <svg class="btn-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        <span>Copy</span>
      `;
      copyBtn.addEventListener('click', () => copyToClipboard(content, copyBtn));

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
    avatar.innerHTML = `<img src="/static/images/memoraai-avatar.png" alt="MemoraAI" width="34" height="34">`;

    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble assistant-bubble';
    bubble.style.borderColor = 'var(--accent-rose)';
    bubble.innerHTML = `
      <div style="color: var(--accent-rose); font-weight: 600; display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>Notice</span>
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

      let lang = 'code';
      const classes = code.className.split(' ');
      for (const cls of classes) {
        if (cls.startsWith('language-')) {
          lang = cls.replace('language-', '');
          break;
        }
      }

      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-container';

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
      copyBtn.addEventListener('click', () => copyToClipboard(code.innerText, copyBtn));

      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(header);
      wrapper.appendChild(pre);

      if (typeof hljs !== 'undefined') {
        hljs.highlightElement(code);
      }
    });
  }

  /* ==========================================================================
     6. CONVERSATION MANAGEMENT & EXPORT
     ========================================================================== */
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
      DOM.historyCountBadge.textContent = state.conversations.length;
    } catch (err) {
      console.error('Error fetching conversations:', err);
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
          <button class="item-action-btn btn-rename" title="Rename" data-id="${conv.id}">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
          </button>
          <button class="item-action-btn btn-delete" title="Delete" data-id="${conv.id}">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      `;

      item.querySelector('.conversation-item-main').addEventListener('click', () => {
        loadConversation(conv.id);
        closeSidebar();
      });

      item.querySelector('.btn-rename').addEventListener('click', (e) => {
        e.stopPropagation();
        openRenameModal(conv.id, conv.title);
      });

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
    state.stagedFiles = [];
    renderStagedFiles();
    updateHeaderFilesBadge(0);

    document.querySelectorAll('.conversation-item').forEach((el) => el.classList.remove('active'));
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

      document.querySelectorAll('.conversation-item').forEach((el) => {
        el.classList.toggle('active', el.getAttribute('data-id') === conv.id);
      });

      // Update header files badge
      const fileCount = conv.files ? conv.files.length : 0;
      updateHeaderFilesBadge(fileCount);

      // Render messages
      DOM.messagesContainer.innerHTML = '';
      if (conv.messages && conv.messages.length > 0) {
        DOM.welcomeScreen.style.display = 'none';
        conv.messages.forEach((msg) => {
          appendMessageBubble(msg.role, msg.content, msg.created_at, false, msg.attachments || []);
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

  function handleExportChat() {
    if (!state.currentConversationId) {
      showToast('No active conversation to export', 'error');
      return;
    }
    window.location.href = `/api/conversations/${state.currentConversationId}/export?format=markdown`;
    showToast('Exporting conversation transcript...', 'success');
  }

  function updateHeaderFilesBadge(count) {
    if (count > 0) {
      DOM.headerFilesBadge.style.display = 'flex';
      DOM.headerFilesCount.textContent = count;
    } else {
      DOM.headerFilesBadge.style.display = 'none';
    }
  }

  /* ==========================================================================
     7. FILE LIBRARY MODAL & PREVIEW
     ========================================================================== */
  async function openFileLibraryModal() {
    DOM.fileLibraryModal.style.display = 'flex';
    fetchLibraryFiles();
  }

  async function fetchLibraryFiles() {
    try {
      const res = await fetch('/api/files');
      if (!res.ok) throw new Error('Failed to load files');
      const data = await res.json();
      state.allFiles = data.files || [];
      renderLibraryGrid(state.allFiles);
      updateTotalFilesCount();
    } catch (err) {
      console.error('Library fetch error:', err);
      showToast('Could not load file library', 'error');
    }
  }

  function filterLibraryFiles(searchQuery, category) {
    if (!state.allFiles) return;
    let filtered = state.allFiles;

    if (category && category !== 'all') {
      filtered = filtered.filter((f) => f.file_category === category);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter((f) => f.original_filename.toLowerCase().includes(q));
    }
    renderLibraryGrid(filtered);
  }

  function renderLibraryGrid(files) {
    DOM.libraryFilesGrid.innerHTML = '';
    if (!files || files.length === 0) {
      DOM.libraryEmptyState.style.display = 'block';
      return;
    }

    DOM.libraryEmptyState.style.display = 'none';

    files.forEach((file) => {
      const card = document.createElement('div');
      card.className = 'library-file-card';
      const ext = file.original_filename.split('.').pop().toLowerCase();

      card.innerHTML = `
        <div class="file-card-top">
          <div class="file-card-icon ${ext}">${ext.slice(0, 3)}</div>
          <div class="file-card-details">
            <span class="file-card-title" title="${escapeHtml(file.original_filename)}">${escapeHtml(file.original_filename)}</span>
            <span class="file-card-meta">${formatBytes(file.file_size)} • ${formatTimestamp(file.created_at)}</span>
          </div>
        </div>
        <div class="file-card-actions">
          <button class="btn-file-action btn-preview-file" data-id="${file.id}">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
              <circle cx="12" cy="12" r="3"></circle>
            </svg>
            <span>Preview</span>
          </button>
          <button class="btn-file-action delete btn-delete-file" data-id="${file.id}" title="Delete file">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
            </svg>
            <span>Delete</span>
          </button>
        </div>
      `;

      // Preview button
      card.querySelector('.btn-preview-file').addEventListener('click', () => {
        openDocumentPreview(file.id, file.original_filename);
      });

      // Delete button
      card.querySelector('.btn-delete-file').addEventListener('click', async () => {
        if (confirm(`Delete ${file.original_filename}?`)) {
          await deleteFileRecord(file.id);
        }
      });

      DOM.libraryFilesGrid.appendChild(card);
    });
  }

  async function openDocumentPreview(fileId, filename) {
    try {
      const res = await fetch(`/api/files/${fileId}/content`);
      if (!res.ok) throw new Error('Failed to load file text');
      const data = await res.json();

      DOM.previewFilename.textContent = filename;
      DOM.previewMetaBar.textContent = `File ID: ${fileId} • Chunks: ${data.chunks ? data.chunks.length : 0} • Characters: ${data.extracted_text.length}`;
      DOM.previewTextBox.textContent = data.extracted_text || '[No extractable text found in this file]';
      DOM.documentPreviewModal.style.display = 'flex';
    } catch (err) {
      showToast('Could not load document preview', 'error');
    }
  }

  async function deleteFileRecord(fileId) {
    try {
      const res = await fetch(`/api/files/${fileId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      showToast('File deleted', 'success');
      fetchLibraryFiles();
      updateTotalFilesCount();
    } catch (err) {
      showToast('Failed to delete file', 'error');
    }
  }

  async function updateTotalFilesCount() {
    try {
      const res = await fetch('/api/files');
      if (res.ok) {
        const data = await res.json();
        const count = data.count || 0;
        DOM.totalFilesBadge.textContent = `${count} file${count === 1 ? '' : 's'}`;
      }
    } catch (e) {}
  }

  /* ==========================================================================
     8. CONVERSATION DIALOGS (RENAME, DELETE, CLEAR)
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
      const res = await fetch(`/api/conversations/${state.targetConvIdForModal}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');

      const wasActive = state.currentConversationId === state.targetConvIdForModal;
      closeModals();
      fetchConversations();
      if (wasActive) startNewChat();
      showToast('Conversation deleted', 'success');
    } catch (err) {
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
      const res = await fetch(`/api/conversations/${state.currentConversationId}/clear`, { method: 'POST' });
      if (!res.ok) throw new Error('Clear failed');

      DOM.messagesContainer.innerHTML = '';
      DOM.welcomeScreen.style.display = 'flex';
      closeModals();
      fetchConversations();
      showToast('Conversation messages cleared', 'success');
    } catch (err) {
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
    DOM.fileLibraryModal.style.display = 'none';
    DOM.documentPreviewModal.style.display = 'none';
    state.targetConvIdForModal = null;
  }

  async function checkSystemHealth() {
    try {
      const res = await fetch('/api/health');
      if (!res.ok) return;
      const data = await res.json();
      if (DOM.settingsProviderVal) {
        DOM.settingsProviderVal.textContent = data.provider === 'google-gemini' ? 'Google Gemini' : 'OpenAI';
      }
      if (DOM.settingsModelVal) {
        DOM.settingsModelVal.textContent = data.model;
        DOM.modelBadgeText.textContent = data.model;
      }
      if (DOM.settingsApiStatus) {
        DOM.settingsApiStatus.textContent = data.openai_configured ? 'Active & Ready' : 'API Key Missing in .env';
        DOM.settingsApiStatus.style.color = data.openai_configured ? 'var(--accent-emerald)' : 'var(--accent-rose)';
      }
      if (DOM.settingsDbStatus) {
        DOM.settingsDbStatus.textContent = data.database === 'connected' ? 'Connected (SQLite)' : data.database;
        DOM.settingsDbStatus.style.color = data.database === 'connected' ? 'var(--accent-emerald)' : 'var(--accent-rose)';
      }
    } catch (e) {}
  }

  /* ==========================================================================
     9. UI HELPERS & UTILITIES
     ========================================================================== */
  function openSidebar() {
    DOM.sidebar.classList.add('open');
    DOM.sidebarBackdrop.classList.add('active');
  }

  function closeSidebar() {
    DOM.sidebar.classList.remove('open');
    DOM.sidebarBackdrop.classList.remove('active');
  }

  function autoResizeTextarea() {
    DOM.messageInput.style.height = 'auto';
    DOM.messageInput.style.height = Math.min(DOM.messageInput.scrollHeight, 200) + 'px';
  }

  function updateSendButtonState() {
    DOM.sendBtn.disabled = !canSubmitMessage();
  }

  function setGeneratingState(isGenerating) {
    state.isGenerating = isGenerating;
    DOM.sendBtn.disabled = isGenerating;
    DOM.messageInput.disabled = isGenerating;
    DOM.attachBtn.disabled = isGenerating;

    if (isGenerating) {
      DOM.sendIcon.style.display = 'none';
      DOM.sendSpinner.style.display = 'block';
    } else {
      DOM.sendIcon.style.display = 'block';
      DOM.sendSpinner.style.display = 'none';
      updateSendButtonState();
    }
  }

  function showTypingIndicator(statusText = 'MemoraAI is thinking...') {
    DOM.typingStatusText.textContent = statusText;
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
      setTimeout(() => { triggerBtn.innerHTML = origHtml; }, 2000);
    }).catch(() => showToast('Failed to copy', 'error'));
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

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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
