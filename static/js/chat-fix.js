(function() {
    // Chat list fix module
    const ChatDisplayFix = {
        init: function() {
            console.log('Chat display fix initialized');
            this.setupEventListeners();
            this.fetchAndDisplayChats();
        },
        
        setupEventListeners: function() {
            // Add event listener for page load
            window.addEventListener('load', () => this.fetchAndDisplayChats());
            
            // Add refresh button if it exists
            const refreshBtn = document.getElementById('refreshChatsBtn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => this.fetchAndDisplayChats());
            }
        },
        
        fetchAndDisplayChats: function() {
            console.log('Fetching chats...');
            
            // First try the regular endpoint
            fetch('/api/chats')
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Error ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log(`Received ${data.length} chats`);
                    this.displayChats(data);
                })
                .catch(error => {
                    console.error('Failed to fetch chats:', error);
                    // Try debug endpoint as fallback
                    this.fetchDebugData();
                });
        },
        
        fetchDebugData: function() {
            console.log('Trying debug endpoint...');
            fetch('/api/debug/chats')
                .then(response => response.json())
                .then(data => {
                    console.log('Debug data:', data);
                    if (data.users && data.users.length > 0) {
                        alert(`Found ${data.users.length} users in database but couldn't display chats. Check console for details.`);
                    } else {
                        alert('No users found in database. Try adding a test message first.');
                    }
                })
                .catch(error => {
                    console.error('Debug endpoint failed:', error);
                });
        },
        
        displayChats: function(chats) {
            const chatList = document.getElementById('chatList');
            if (!chatList) {
                console.error('Chat list element not found!');
                return;
            }
            
            // Clear existing chats
            chatList.innerHTML = '';
            
            if (chats.length === 0) {
                const noChatItem = document.createElement('div');
                noChatItem.className = 'chat-item';
                noChatItem.innerHTML = '<p>No active chats</p>';
                chatList.appendChild(noChatItem);
                return;
            }
            
            // Display each chat
            chats.forEach(chat => {
                this.createChatItem(chat, chatList);
            });
            
            console.log('Chats displayed successfully');
        },
        
        createChatItem: function(chat, chatList) {
            const chatItem = document.createElement('div');
            chatItem.className = 'chat-item';
            chatItem.dataset.userId = chat.user_id;
            
            let nameInitial = (chat.alias || chat.first_name || 'User').charAt(0).toUpperCase();
            
            let lastMsgText = chat.last_message_text || '';
            let msgIcon = '';
            
            if (chat.has_media === 1) {
                const mediaTypes = {
                    'photo': '📷 Photo',
                    'video': '🎥 Video',
                    'document': '📄 Document',
                    'voice': '🎤 Voice message',
                    'audio': '🎵 Audio',
                    'sticker': '🏷️ Sticker'
                };
                
                msgIcon = mediaTypes[chat.media_type] || '📎 Media';
                
                if (chat.last_message_text && chat.last_message_text.trim()) {
                    lastMsgText = msgIcon + ': ' + chat.last_message_text;
                } else {
                    lastMsgText = msgIcon;
                }
            } else if (chat.is_replied && chat.reply_text) {
                // If it's our reply, indicate it
                lastMsgText = '👤 You: ' + chat.reply_text;
            }
            
            chatItem.innerHTML = `
                <div class="chat-avatar">${nameInitial}</div>
                <div class="chat-info">
                    <div class="chat-header-row">
                        <span class="chat-name">${chat.alias || chat.first_name || 'User ' + chat.user_id}</span>
                        <span class="chat-time">${this.formatDate(chat.last_message_time)}</span>
                    </div>
                    <div class="chat-last-message">${lastMsgText}</div>
                </div>
                ${chat.unread_count > 0 ? `<div class="unread-badge">${chat.unread_count}</div>` : ''}
            `;
            
            chatItem.addEventListener('click', () => {
                // Call existing loadMessages function if available
                if (typeof window.loadMessages === 'function') {
                    document.querySelectorAll('.chat-item').forEach(item => {
                        item.classList.remove('active');
                    });
                    chatItem.classList.add('active');
                    window.loadMessages(chat.user_id);
                } else {
                    console.warn('loadMessages function not available');
                    // Fallback - go to messages directly
                    window.location.href = `/api/messages/${chat.user_id}`;
                }
            });
            
            chatList.appendChild(chatItem);
        },
        
        formatDate: function(dateString) {
            if (!dateString) return '';
            
            const date = new Date(dateString);
            const now = new Date();
            
            // If today, show time only
            if (date.toDateString() === now.toDateString()) {
                return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            }
            
            // If this year, show date without year
            if (date.getFullYear() === now.getFullYear()) {
                return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
            }
            
            // Otherwise show full date
            return date.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
        }
    };
    
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => ChatDisplayFix.init());
    
    // Expose globally for debugging
    window.ChatDisplayFix = ChatDisplayFix;
})();