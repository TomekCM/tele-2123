// Улучшенный интерфейс мессенджера с функциями отправки файлов и поддержкой Enter
document.addEventListener('DOMContentLoaded', function() {
    console.log("Telegram interface initialized");
    
    // Setup global handlers
    setupEventListeners();
    
    // Load chats immediately and with retries
    loadChats();
    setTimeout(loadChats, 500);
    setTimeout(loadChats, 1500);
    
    // Setup periodic refresh
    setInterval(loadChats, 15000);
    
    // Check for new messages periodically
    setInterval(checkNewMessages, 10000);
    
    // Setup file upload functionality
    setupFileUpload();
});

// Store random names for consistent display
const userNameMap = {};

// Cache the last loaded messages to avoid unnecessary refreshes
let lastLoadedChats = [];
let currentUserId = null;
let selectedFile = null;

// ===== CORE FUNCTIONS =====

function setupEventListeners() {
    // Setup refresh button
    const refreshBtn = document.getElementById('refreshChatsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadChats);
    }
    
    // Setup debug button
    const debugBtn = document.getElementById('debugBtn');
    if (debugBtn) {
        debugBtn.addEventListener('click', forceChatDisplay);
    }
    
    // Setup search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    // Setup attachment button
    const attachmentBtn = document.getElementById('attachmentBtn');
    if (attachmentBtn) {
        attachmentBtn.addEventListener('click', openFileUpload);
    }
    
    // Setup textarea to handle Enter key
    const replyText = document.getElementById('replyText');
    if (replyText) {
        replyText.addEventListener('keydown', function(e) {
            // Send on Enter (without Shift)
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendReply();
            }
            
            // Allow newlines with Shift+Enter
            if (e.key === 'Enter' && e.shiftKey) {
                // Let default behavior continue for newline
            }
        });
        
        // Handle paste events for images
        replyText.addEventListener('paste', handlePaste);
    }
    
    // Clipboard paste anywhere in the window
    window.addEventListener('paste', handlePaste);
}

function loadChats() {
    console.log("Loading chats...");
    
    fetch('/api/chats')
        .then(response => {
            if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
            return response.json();
        })
        .then(chats => {
            console.log(`Loaded ${chats.length} chats`);
            
            // Skip rendering if nothing changed
            if (JSON.stringify(chats) === JSON.stringify(lastLoadedChats)) {
                console.log("Chats unchanged, skipping render");
                return;
            }
            
            // Save for comparison
            lastLoadedChats = chats;
            
            // Render chats
            renderChats(chats);
        })
        .catch(error => {
            console.error("Failed to load chats:", error);
        });
}

function forceChatDisplay() {
    console.log("Force displaying chats...");
    fetch('/api/chats')
        .then(response => response.json())
        .then(data => {
            console.log(`Forced display of ${data.length} chats`);
            
            if (data.length === 0) {
                alert("No chats found in database. Try sending a message to your bot first.");
            } else {
                renderChats(data);
                alert(`Successfully loaded ${data.length} chats.`);
            }
        })
        .catch(error => {
            console.error("Error forcing chat display:", error);
            alert(`Error loading chats: ${error.message}`);
        });
}

function renderChats(chats) {
    const chatList = document.getElementById('chatList');
    if (!chatList) return;
    
    // Store current active chat ID
    const activeChat = document.querySelector('.chat-item.active');
    const activeChatId = activeChat ? activeChat.dataset.userId : null;
    
    // Clear chat list
    chatList.innerHTML = '';
    
    if (chats.length === 0) {
        chatList.innerHTML = '<div class="no-chats">No conversations yet</div>';
        return;
    }
    
    // Create chat items
    chats.forEach(chat => {
        const chatItem = createChatItem(chat);
        
        // Restore active state if needed
        if (chat.user_id == activeChatId) {
            chatItem.classList.add('active');
        }
        
        chatList.appendChild(chatItem);
    });
}

function createChatItem(chat) {
    const chatItem = document.createElement('div');
    chatItem.className = 'chat-item';
    chatItem.dataset.userId = chat.user_id;
    
    // Get or generate a random name
    const displayName = getRandomName(chat.user_id);
    const nameInitial = displayName.charAt(0).toUpperCase();
    
    // Format last message text
    let lastMsgText = chat.last_message_text || '';
    if (chat.has_media === 1) {
        const mediaTypes = {
            'photo': '📷 Photo',
            'video': '🎥 Video',
            'document': '📄 Document',
            'voice': '🎤 Voice',
            'audio': '🎵 Audio',
            'sticker': '🏷️ Sticker'
        };
        lastMsgText = mediaTypes[chat.media_type] || '📎 Media';
    } else if (chat.is_replied && chat.reply_text) {
        lastMsgText = '👤 You: ' + chat.reply_text;
    }
    
    // Create chat HTML
    chatItem.innerHTML = `
        <div class="chat-avatar">${nameInitial}</div>
        <div class="chat-info">
            <div class="chat-name">${displayName}</div>
            <div class="chat-preview">${lastMsgText}</div>
        </div>
        <div class="chat-time">${formatDate(chat.last_message_time)}</div>
        ${chat.unread_count > 0 ? `<div class="unread-badge">${chat.unread_count}</div>` : ''}
    `;
    
    // Add click handler
    chatItem.addEventListener('click', () => {
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        
        chatItem.classList.add('active');
        loadMessages(chat.user_id);
    });
    
    return chatItem;
}

function loadMessages(userId) {
    console.log(`Loading messages for user ${userId}`);
    currentUserId = userId;
    
    // Show loading indicator
    const messagesContainer = document.getElementById('messagesContainer');
    if (messagesContainer) {
        messagesContainer.innerHTML = '<div class="loading-messages">Loading messages...</div>';
    }
    
    fetch(`/api/messages/${userId}`)
        .then(response => {
            if (!response.ok) throw new Error(`Error ${response.status}: ${response.statusText}`);
            return response.json();
        })
        .then(messages => {
            console.log(`Loaded ${messages.length} messages for user ${userId}`);
            
            // Render messages
            renderMessages(messages, userId);
            
            // Mark as read
            markAsRead(userId);
            
            // Update chat header
            updateChatHeader(messages, userId);
            
            // Show reply form
            showReplyForm(userId);
        })
        .catch(error => {
            console.error(`Failed to load messages for user ${userId}:`, error);
            
            if (messagesContainer) {
                messagesContainer.innerHTML = '<div class="error-message">Failed to load messages. Click refresh to try again.</div>';
            }
        });
}

function renderMessages(messages, userId) {
    const messagesContainer = document.getElementById('messagesContainer');
    if (!messagesContainer) return;
    
    // Clear container
    messagesContainer.innerHTML = '';
    
    if (messages.length === 0) {
        messagesContainer.innerHTML = '<div class="empty-chat-message">No messages yet</div>';
        return;
    }
    
    // Create wrapper
    const messagesWrapper = document.createElement('div');
    messagesWrapper.className = 'messages-wrapper';
    
    // Track date for separators
    let currentDate = null;
    
    // Render each message
    messages.forEach(message => {
        // Check if date changed
        const msgDate = new Date(message.timestamp);
        const dateStr = msgDate.toDateString();
        
        if (dateStr !== currentDate) {
            currentDate = dateStr;
            
            // Add date separator
            const separator = document.createElement('div');
            separator.className = 'date-separator';
            separator.innerHTML = `<span>${formatDateHeader(message.timestamp)}</span>`;
            messagesWrapper.appendChild(separator);
        }
        
        // Create message
        const messageEl = document.createElement('div');
        messageEl.className = `message ${message.is_replied ? 'message-outgoing' : 'message-incoming'}`;
        messageEl.dataset.messageId = message.id;
        
        let msgContent = '';
        
        // Add media content if present
        if (message.has_media === 1 && message.media_path) {
            msgContent += '<div class="message-media">';
            
            // Show media type indicator
            msgContent += `<div class="media-source">${message.media_type.charAt(0).toUpperCase() + message.media_type.slice(1)}</div>`;
            
            if (message.media_type === 'photo') {
                msgContent += `<img src="${message.media_path}" class="media-image" onclick="openImageViewer('${message.media_path}')">`;
            } else if (message.media_type === 'video') {
                msgContent += `<video controls class="media-video"><source src="${message.media_path}" type="video/mp4"></video>`;
            } else if (message.media_type === 'voice' || message.media_type === 'audio') {
                msgContent += `<audio controls class="media-audio"><source src="${message.media_path}"></audio>`;
            } else if (message.media_type === 'document') {
                msgContent += `<div class="media-document"><a href="${message.media_path}" download target="_blank">Download document</a></div>`;
            }
            
            msgContent += '</div>';
        }
        
        // Add message text
        const text = message.is_replied ? message.reply_text : message.message_text;
        if (text) {
            msgContent += `<div class="message-text">${text}</div>`;
        }
        
        // Add timestamp
        msgContent += `<div class="message-time">${formatTime(message.timestamp)}</div>`;
        
        // Add delete button
        msgContent += `
            <div class="message-actions">
                <button class="delete-button" onclick="deleteMessage(${message.id})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        messageEl.innerHTML = msgContent;
        messagesWrapper.appendChild(messageEl);
    });
    
    // Add all messages to container
    messagesContainer.appendChild(messagesWrapper);
    
    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function updateChatHeader(messages, userId) {
    if (messages.length === 0) return;
    
    // Use random name for privacy
    const displayName = getRandomName(userId);
    
    // Update header
    const chatHeader = document.getElementById('chatHeader');
    if (chatHeader) {
        chatHeader.innerHTML = `
            <div class="chat-header-info">
                <h2>${displayName}</h2>
            </div>
            <div class="chat-header-actions">
                <button id="setAliasBtn" class="header-action-btn">
                    <i class="fas fa-tag"></i> Set Alias
                </button>
                <button id="deleteConversationBtn" class="header-action-btn delete-btn">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        `;
        
        // Add event listeners
        document.getElementById('setAliasBtn').addEventListener('click', () => {
            promptSetAlias(userId, displayName);
        });
        
        document.getElementById('deleteConversationBtn').addEventListener('click', () => {
            confirmDeleteConversation(userId);
        });
    }
}

function showReplyForm(userId) {
    const replyForm = document.getElementById('replyForm');
    if (!replyForm) return;
    
    // Show form
    replyForm.style.display = 'flex';
    
    // Set user ID
    const userIdInput = document.getElementById('userIdInput');
    if (userIdInput) {
        userIdInput.value = userId;
    }
    
    // Focus text area
    const replyText = document.getElementById('replyText');
    if (replyText) {
        replyText.focus();
    }
}

// ===== FILE UPLOAD FUNCTIONS =====

function setupFileUpload() {
    // File input change
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelection);
    }
    
    // Browse button
    const browseBtn = document.getElementById('browseFilesBtn');
    if (browseBtn) {
        browseBtn.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
    }
    
    // Send file button
    const sendFileBtn = document.getElementById('sendFileBtn');
    if (sendFileBtn) {
        sendFileBtn.addEventListener('click', uploadAndSendFile);
    }
    
    // Close upload overlay
    const closeBtn = document.getElementById('closeFileUpload');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeFileUpload);
    }
    
    // Remove selected file
    const removeFileBtn = document.getElementById('removeFileBtn');
    if (removeFileBtn) {
        removeFileBtn.addEventListener('click', removeSelectedFile);
    }
    
    // Setup drag and drop
    const dropArea = document.getElementById('fileDropArea');
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.add('dragging');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.remove('dragging');
            }, false);
        });
        
        dropArea.addEventListener('drop', handleDrop, false);
    }
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelection(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

function handleFile(file) {
    selectedFile = file;
    
    // Display file info
    const fileNameEl = document.getElementById('selectedFileName');
    const fileContainer = document.getElementById('selectedFileContainer');
    const sendBtn = document.getElementById('sendFileBtn');
    
    if (fileNameEl && fileContainer && sendBtn) {
        fileNameEl.textContent = file.name;
        fileContainer.style.display = 'flex';
        sendBtn.disabled = false;
        
        // Update icon based on file type
        const iconEl = fileContainer.querySelector('.selected-file-icon');
        if (iconEl) {
            if (file.type.startsWith('image/')) {
                iconEl.className = 'fas fa-image selected-file-icon';
            } else if (file.type.startsWith('video/')) {
                iconEl.className = 'fas fa-video selected-file-icon';
            } else if (file.type.startsWith('audio/')) {
                iconEl.className = 'fas fa-music selected-file-icon';
            } else {
                iconEl.className = 'fas fa-file selected-file-icon';
            }
        }
    }
}

function removeSelectedFile() {
    selectedFile = null;
    
    const fileContainer = document.getElementById('selectedFileContainer');
    const sendBtn = document.getElementById('sendFileBtn');
    
    if (fileContainer && sendBtn) {
        fileContainer.style.display = 'none';
        sendBtn.disabled = true;
    }
    
    // Clear file input
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.value = '';
    }
}

function openFileUpload() {
    const overlay = document.getElementById('fileUploadOverlay');
    if (overlay) {
        overlay.style.display = 'flex';
    }
    
    // Reset file selection
    removeSelectedFile();
}

function closeFileUpload() {
    const overlay = document.getElementById('fileUploadOverlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
    
    // Reset file selection
    removeSelectedFile();
}

function uploadAndSendFile() {
    if (!selectedFile || !currentUserId) {
        return;
    }
    
    // Create form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('user_id', currentUserId);
    
    // Disable send button
    const sendBtn = document.getElementById('sendFileBtn');
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = 'Sending...';
    }
    
    // Upload file
    fetch('/api/upload-file', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close overlay
            closeFileUpload();
            
            // Refresh messages
            loadMessages(currentUserId);
            
            // Refresh chat list
            loadChats();
        } else {
            alert("Failed to upload file: " + (data.error || "Unknown error"));
            
            // Re-enable send button
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.textContent = 'Send';
            }
        }
    })
    .catch(error => {
        console.error("Failed to upload file:", error);
        alert("Failed to upload file: " + error.message);
        
        // Re-enable send button
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.textContent = 'Send';
        }
    });
}

function handlePaste(e) {
    // Check if we're pasting an image
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    
    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
            // Get image file
            const blob = items[i].getAsFile();
            
            if (blob && currentUserId) {
                // Prevent default paste into textarea
                e.preventDefault();
                
                // Create form data
                const formData = new FormData();
                formData.append('file', blob, 'pasted-image.png');
                formData.append('user_id', currentUserId);
                
                // Upload pasted image
                fetch('/api/upload-file', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Refresh messages
                        loadMessages(currentUserId);
                        
                        // Refresh chat list
                        loadChats();
                    } else {
                        alert("Failed to upload pasted image: " + (data.error || "Unknown error"));
                    }
                })
                .catch(error => {
                    console.error("Failed to upload pasted image:", error);
                    alert("Failed to upload pasted image: " + error.message);
                });
                
                return;
            }
        }
    }
}

// ===== HELPER FUNCTIONS =====

function getRandomName(userId) {
    // Return from cache if exists
    if (userNameMap[userId]) {
        return userNameMap[userId];
    }
    
    // Arrays of first names and titles
    const firstNames = [
        "Alex", "Blake", "Casey", "Dana", "Ellis", "Fran", "Grey", "Harper",
        "Indigo", "Jordan", "Kelly", "Logan", "Morgan", "Noel", "Parker", "Quinn",
        "Reese", "Sage", "Taylor", "Val", "Winter", "Aiden", "Brynn", "Charlie",
        "Drew", "Emery", "Finley", "Harley", "Jules", "Kai", "Lane", "Max",
        "Nova", "Oakley", "Piper", "River", "Skyler", "Tatum", "Wren", "Zion"
    ];
    
    const titles = [
        "Client", "User", "Person", "Contact", "Guest", "Member", "Visitor",
        "Customer", "Inquirer", "Subscriber", "Patron", "Friend", "Associate"
    ];
    
    // Generate random name
    const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
    const title = titles[Math.floor(Math.random() * titles.length)];
    const randomName = `${firstName} (${title})`;
    
    // Cache it
    userNameMap[userId] = randomName;
    
    return randomName;
}

function formatDateHeader(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    
    // Invalid date
    if (isNaN(date.getTime())) {
        return dateString;
    }
    
    // Today
    if (date.toDateString() === now.toDateString()) {
        return 'Today';
    }
    
    // Yesterday
    if (date.toDateString() === yesterday.toDateString()) {
        return 'Yesterday';
    }
    
    // Earlier this week (within 7 days)
    const daysDiff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    if (daysDiff < 7) {
        return date.toLocaleDateString(undefined, { weekday: 'long' });
    }
    
    // Other dates
    return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatTime(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    
    // Invalid date
    if (isNaN(date.getTime())) {
        return dateString;
    }
    
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    const now = new Date();
    
    // Invalid date
    if (isNaN(date.getTime())) {
        return dateString;
    }
    
    // Today
    if (date.toDateString() === now.toDateString()) {
        return formatTime(dateString);
    }
    
    // This week
    const daysDiff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
    if (daysDiff < 7) {
        return date.toLocaleDateString(undefined, { weekday: 'short' });
    }
    
    // This year
    if (date.getFullYear() === now.getFullYear()) {
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    }
    
    // Other years
    return date.toLocaleDateString(undefined, { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

function markAsRead(userId) {
    fetch(`/api/messages/${userId}/read`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Refresh chats to update unread count
            loadChats();
        }
    })
    .catch(error => {
        console.error("Failed to mark messages as read:", error);
    });
}

function checkNewMessages() {
    fetch('/api/new-messages')
        .then(response => response.json())
        .then(data => {
            if (data.has_new) {
                // Play notification sound
                playNotificationSound();
                
                // Show browser notification
                showBrowserNotification(`New messages from ${data.user_ids.length} conversations`);
                
                // Refresh chats
                loadChats();
                
                // Refresh current conversation if it has new messages
                if (currentUserId && data.user_ids.includes(parseInt(currentUserId))) {
                    loadMessages(currentUserId);
                }
            }
        })
        .catch(error => {
            console.error("Failed to check for new messages:", error);
        });
}

function playNotificationSound() {
    const audio = new Audio('/static/sounds/notification.mp3');
    audio.volume = 0.5;
    audio.play().catch(e => console.log("Could not play notification sound:", e));
}

function showBrowserNotification(message) {
    // Check if browser supports notifications
    if (!("Notification" in window)) {
        return;
    }
    
    // Request permission if needed
    if (Notification.permission !== "granted" && Notification.permission !== "denied") {
        Notification.requestPermission();
    }
    
    // Show notification if allowed
    if (Notification.permission === "granted") {
        new Notification("Telegram Web Interface", {
            body: message,
            icon: "/static/images/logo.png"
        });
    }
}

function handleSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const chatList = document.getElementById('chatList');
    
    if (!searchInput || !searchResults || !chatList) return;
    
    const query = searchInput.value.trim();
    
    // Show normal chat list if search is empty
    if (query === '') {
        searchResults.style.display = 'none';
        chatList.style.display = 'block';
        return;
    }
    
    // Show searching indicator
    searchResults.innerHTML = '<div class="searching">Searching...</div>';
    searchResults.style.display = 'block';
    chatList.style.display = 'none';
    
    // Search API
    fetch(`/api/search?term=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(results => {
            // Clear results
            searchResults.innerHTML = '';
            
            if (results.length === 0) {
                searchResults.innerHTML = '<div class="no-results">No results found</div>';
                return;
            }
            
            // Group results by user
            const userGroups = {};
            
            results.forEach(result => {
                if (!userGroups[result.user_id]) {
                    userGroups[result.user_id] = {
                        userId: result.user_id,
                        name: getRandomName(result.user_id),
                        messages: []
                    };
                }
                
                userGroups[result.user_id].messages.push(result);
            });
            
            // Create results HTML
            Object.values(userGroups).forEach(group => {
                const groupEl = document.createElement('div');
                groupEl.className = 'search-group';
                
                groupEl.innerHTML = `
                    <div class="search-group-header">
                        <span class="search-group-name">${group.name}</span>
                        <span class="search-count">${group.messages.length} matches</span>
                    </div>
                `;
                
                // Add first 3 matching messages
                const messagesList = document.createElement('div');
                messagesList.className = 'search-messages';
                
                group.messages.slice(0, 3).forEach(msg => {
                    const messageEl = document.createElement('div');
                    messageEl.className = 'search-message';
                    
                    // Highlight the search term
                    let content = msg.message_text || msg.reply_text || '';
                    content = content.replace(new RegExp(query, 'gi'), match => `<mark>${match}</mark>`);
                    
                    messageEl.innerHTML = `
                        <div class="search-message-time">${formatDate(msg.timestamp)}</div>
                        <div class="search-message-content">${content}</div>
                    `;
                    
                    // Add click handler
                    messageEl.addEventListener('click', () => {
                        // Reset search
                        searchInput.value = '';
                        searchResults.style.display = 'none';
                        chatList.style.display = 'block';
                        
                        // Load the conversation
                        loadMessages(group.userId);
                        
                        // Update active chat
                        document.querySelectorAll('.chat-item').forEach(item => {
                            item.classList.remove('active');
                            if (item.dataset.userId == group.userId) {
                                item.classList.add('active');
                            }
                        });
                    });
                    
                    messagesList.appendChild(messageEl);
                });
                
                // Add view all button if needed
                if (group.messages.length > 3) {
                    const viewAllBtn = document.createElement('button');
                    viewAllBtn.className = 'view-all-btn';
                    viewAllBtn.textContent = `View all ${group.messages.length} messages`;
                    
                    viewAllBtn.addEventListener('click', () => {
                        // Reset search
                        searchInput.value = '';
                        searchResults.style.display = 'none';
                        chatList.style.display = 'block';
                        
                        // Load the conversation
                        loadMessages(group.userId);
                        
                        // Update active chat
                        document.querySelectorAll('.chat-item').forEach(item => {
                            item.classList.remove('active');
                            if (item.dataset.userId == group.userId) {
                                item.classList.add('active');
                            }
                        });
                    });
                    
                    messagesList.appendChild(viewAllBtn);
                }
                
                groupEl.appendChild(messagesList);
                searchResults.appendChild(groupEl);
            });
        })
        .catch(error => {
            console.error("Search failed:", error);
            searchResults.innerHTML = '<div class="error-message">Search failed. Please try again.</div>';
        });
}

// ===== ACTION FUNCTIONS =====

function promptSetAlias(userId, currentName) {
    const alias = prompt(`Set alias for ${currentName}:`, currentName);
    
    if (alias === null) return; // User cancelled
    
    fetch('/api/set-alias', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: userId,
            alias: alias
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Refresh data
            loadChats();
            loadMessages(userId);
        } else {
            alert("Failed to set alias: " + (data.error || "Unknown error"));
        }
    })
    .catch(error => {
        console.error("Failed to set alias:", error);
        alert("Failed to set alias: " + error.message);
    });
}

function confirmDeleteConversation(userId) {
    if (confirm("Are you sure you want to delete this entire conversation?")) {
        fetch(`/api/conversation/${userId}/delete`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Refresh chat list
                loadChats();
                
                // Clear messages
                const messagesContainer = document.getElementById('messagesContainer');
                if (messagesContainer) {
                    messagesContainer.innerHTML = '<div class="empty-chat-message">Conversation deleted</div>';
                }
                
                // Hide reply form
                const replyForm = document.getElementById('replyForm');
                if (replyForm) {
                    replyForm.style.display = 'none';
                }
                
                // Reset header
                const chatHeader = document.getElementById('chatHeader');
                if (chatHeader) {
                    chatHeader.innerHTML = '<h2>Select a chat</h2>';
                }
                
                // Reset current user
                currentUserId = null;
            } else {
                alert("Failed to delete conversation: " + (data.error || "Unknown error"));
            }
        })
        .catch(error => {
            console.error("Failed to delete conversation:", error);
            alert("Failed to delete conversation: " + error.message);
        });
    }
}

function deleteMessage(messageId) {
    if (confirm("Delete this message?")) {
        fetch(`/api/message/${messageId}/delete`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove message from UI
                const messageEl = document.querySelector(`.message[data-message-id="${messageId}"]`);
                if (messageEl) {
                    messageEl.remove();
                }
                
                // Refresh chats to update last message
                loadChats();
            } else {
                alert("Failed to delete message: " + (data.error || "Unknown error"));
            }
        })
        .catch(error => {
            console.error("Failed to delete message:", error);
            alert("Failed to delete message: " + error.message);
        });
    }
}

// ===== GLOBAL FUNCTIONS =====

// This function needs to be global for the form onsubmit attribute
window.sendReply = function() {
    const replyForm = document.getElementById('replyForm');
    const replyText = document.getElementById('replyText');
    const userIdInput = document.getElementById('userIdInput');
    
    if (!replyForm || !replyText || !userIdInput) return false;
    
    const reply = replyText.value.trim();
    const userId = userIdInput.value;
    
    if (!reply || !userId) return false;
    
    // Disable form
    replyText.disabled = true;
    const submitBtn = replyForm.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = true;
    
    // Send reply
    fetch('/api/reply', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: userId,
            reply_text: reply
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Clear form
            replyText.value = '';
            
            // Re-enable form
            replyText.disabled = false;
            if (submitBtn) submitBtn.disabled = false;
            
            // Focus text area
            replyText.focus();
            
            // Refresh messages and chats
            loadMessages(userId);
            loadChats();
        } else {
            alert("Failed to send reply: " + (data.error || "Unknown error"));
            
            // Re-enable form
            replyText.disabled = false;
            if (submitBtn) submitBtn.disabled = false;
        }
    })
    .catch(error => {
        console.error("Failed to send reply:", error);
        alert("Failed to send reply: " + error.message);
        
        // Re-enable form
        replyText.disabled = false;
        if (submitBtn) submitBtn.disabled = false;
    });
    
    return false; // Prevent form submission
};

// Function for opening image viewer
window.openImageViewer = function(imagePath) {
    const viewer = document.createElement('div');
    viewer.className = 'image-viewer';
    
    viewer.innerHTML = `
        <div class="image-viewer-content">
            <span class="close-viewer">&times;</span>
            <img src="${imagePath}" alt="Full size image">
        </div>
    `;
    
    document.body.appendChild(viewer);
    
    // Close on click outside or on close button
    viewer.addEventListener('click', function(e) {
        if (e.target === viewer || e.target.classList.contains('close-viewer')) {
            document.body.removeChild(viewer);
        }
    });
};

// Function to delete message (needed globally for onclick)
window.deleteMessage = function(messageId) {
    deleteMessage(messageId);
};