// Debug script for chat display issues
(function() {
    // Wait for DOM to be ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log("Chat debugging script initialized");
        
        // Run diagnostics on page load
        setTimeout(runDiagnostics, 1000);
        
        // Add debug button to UI
        addDebugButton();
    });
    
    function addDebugButton() {
        const refreshContainer = document.querySelector('.refresh-container');
        if (!refreshContainer) {
            console.warn("Refresh container not found, can't add debug button");
            return;
        }
        
        const debugButton = document.createElement('button');
        debugButton.className = 'debug-button';
        debugButton.innerHTML = '<i class="fas fa-bug"></i> Debug';
        debugButton.style.marginLeft = '10px';
        debugButton.style.backgroundColor = '#ff9800';
        
        debugButton.addEventListener('click', runDiagnostics);
        refreshContainer.appendChild(debugButton);
        
        console.log("Debug button added to UI");
    }
    
    function runDiagnostics() {
        console.log("Running chat diagnostics...");
        
        // Check if chat list element exists
        const chatList = document.getElementById('chatList');
        if (!chatList) {
            console.error("CRITICAL ERROR: chatList element not found!");
            return;
        }
        
        // Fetch chats directly and log results
        fetch('/api/chats')
            .then(response => {
                console.log("Chat API response status:", response.status);
                if (!response.ok) {
                    throw new Error(`API returned ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log("Chat data received:", data);
                console.log(`Found ${data.length} chats in data`);
                
                if (data.length === 0) {
                    console.warn("No chats found in database!");
                    alert("No chats found in database. Try sending a message to your bot first, or click Add Test Message in debug page.");
                } else {
                    // Try to manually add chats to UI
                    console.log("Attempting to manually add chats to UI...");
                    chatList.innerHTML = '';
                    
                    data.forEach(chat => {
                        const chatItem = document.createElement('div');
                        chatItem.className = 'chat-item';
                        chatItem.dataset.userId = chat.user_id;
                        
                        let nameInitial = (chat.alias || chat.first_name || 'User').charAt(0).toUpperCase();
                        
                        chatItem.innerHTML = `
                            <div class="chat-avatar">${nameInitial}</div>
                            <div class="chat-info">
                                <div class="chat-header-row">
                                    <span class="chat-name">${chat.alias || chat.first_name || 'User ' + chat.user_id}</span>
                                    <span class="chat-time">${formatDate(chat.last_message_time)}</span>
                                </div>
                                <div class="chat-last-message">${chat.last_message_text || '(No message)'}</div>
                            </div>
                            ${chat.unread_count > 0 ? `<div class="unread-badge">${chat.unread_count}</div>` : ''}
                        `;
                        
                        chatItem.addEventListener('click', () => {
                            // Highlight active chat
                            document.querySelectorAll('.chat-item').forEach(item => {
                                item.classList.remove('active');
                            });
                            chatItem.classList.add('active');
                            
                            // Call existing loadMessages function if available
                            if (typeof window.loadMessages === 'function') {
                                window.loadMessages(chat.user_id);
                            } else {
                                console.warn('loadMessages function not found');
                                // Fallback - redirect to messages API
                                window.location.href = `/api/messages/${chat.user_id}`;
                            }
                        });
                        
                        chatList.appendChild(chatItem);
                    });
                    
                    console.log("Manual chat display complete");
                    alert(`Success! Found and displayed ${data.length} chats.`);
                }
            })
            .catch(error => {
                console.error("Error fetching chats:", error);
                alert(`Error fetching chats: ${error.message}\nCheck console for details.`);
            });
    }
    
    function formatDate(dateString) {
        if (!dateString) return 'Unknown';
        
        try {
            const date = new Date(dateString);
            const now = new Date();
            
            // Check if valid date
            if (isNaN(date.getTime())) {
                return dateString;
            }
            
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
        } catch (e) {
            console.error("Date formatting error:", e);
            return dateString;
        }
    }
})();