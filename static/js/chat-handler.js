// Add at the beginning of the file (after the first few lines) 
// Auto-refresh chats every 10 seconds
setInterval(loadChatsAutomatically, 10000);

// Fix for initial loading - call multiple times with delays
setTimeout(loadChatsAutomatically, 100);
setTimeout(loadChatsAutomatically, 500);
setTimeout(loadChatsAutomatically, 1500);

(function() {
    // Функция loadChatsAutomatically объявлена в этом скоупе,
    // благодаря поднятию (hoisting) она доступна для вызова выше.
    
    // Wait for everything to be ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log("Chat handler initialized");
        
        // Wait a moment then load chats
        setTimeout(loadChatsAutomatically, 500);
        
        // Set up a global window function for loading messages
        window.loadMessages = function(userId) {
            console.log(`Loading messages for user ${userId}`);
            loadUserMessages(userId);
        };
    });
    
    function loadChatsAutomatically() {
        console.log("Auto-loading chats...");
        fetch('/api/chats')
            .then(response => response.json())
            .then(data => {
                displayChats(data);
            })
            .catch(error => {
                console.error("Error loading chats:", error);
            });
    }
    
    function loadUserMessages(userId) {
        console.log(`Loading messages for user ${userId}`);
        // Implementation for loading user messages can be added here.
    }
    
    function displayChats(chats) {
        const chatList = document.getElementById('chatList');
        if (!chatList) {
            console.error("Chat list element not found");
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
        
        // Add each chat
        chats.forEach(chat => {
            const chatItem = document.createElement('div');
            chatItem.className = 'chat-item';
            chatItem.dataset.userId = chat.user_id;
            
            let nameInitial = (chat.alias || chat.first_name || 'User').charAt(0).toUpperCase();
            
            let lastMsgText = chat.last_message_text || '';
            if (chat.has_media === 1) {
                const mediaTypes = {
                    'photo': '📷 Photo',
                    'video': '🎥 Video',
                    'document': '📄 Document',
                    'voice': '🎤 Voice message',
                    'audio': '🎵 Audio',
                    'sticker': '🏷️ Sticker'
                };
                lastMsgText = mediaTypes[chat.media_type] || '📎 Media';
            } else if (chat.is_replied && chat.reply_text) {
                lastMsgText = '👤 You: ' + chat.reply_text;
            }
            
            chatItem.innerHTML = `
                <div class="chat-initial">${nameInitial}</div>
                <div class="chat-info">
                    <p class="chat-name">${chat.alias || chat.first_name || 'User'}</p>
                    <p class="chat-last-message">${lastMsgText}</p>
                </div>
            `;
            
            chatItem.addEventListener('click', function() {
                window.loadMessages(chat.user_id);
            });
            
            chatList.appendChild(chatItem);
        });
    }
    
    // Add this after the initial function declaration in chat-handler.js
    window.ChatHandler = {
        loadChats: loadChatsAutomatically,
        loadUserMessages: loadUserMessages,
        displayChats: displayChats  // Expose this for the name randomizer
    };
})();
