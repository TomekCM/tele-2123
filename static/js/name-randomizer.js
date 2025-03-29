// Name randomization for privacy
(function() {
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
    
    // Function to replace real names with random ones
    function anonymizeNames() {
        // Map to store consistent name mapping (user_id → random name)
        const nameMap = {};
        
        // Process all chat items
        document.querySelectorAll('.chat-item').forEach(chat => {
            const userId = chat.dataset.userId;
            if (!userId) return;
            
            // Generate or retrieve consistent random name for this user
            if (!nameMap[userId]) {
                const randomFirst = firstNames[Math.floor(Math.random() * firstNames.length)];
                const randomTitle = titles[Math.floor(Math.random() * titles.length)];
                nameMap[userId] = randomFirst + " (" + randomTitle + ")";
            }
            
            // Replace displayed name
            const nameElement = chat.querySelector('.chat-name');
            if (nameElement) nameElement.textContent = nameMap[userId];
        });
        
        // Also check if we need to update the chat header
        const chatHeader = document.querySelector('.chat-header h2');
        const currentUserId = document.getElementById('userIdInput')?.value;
        
        if (chatHeader && currentUserId && nameMap[currentUserId]) {
            // Don't replace "Select a chat" text
            if (chatHeader.textContent !== "Select a chat") {
                chatHeader.textContent = nameMap[currentUserId];
            }
        }
    }
    
    // Run after chats are loaded
    function setupNameRandomization() {
        // Override the displayChats function to add our anonymization
        const originalDisplayChats = window.ChatHandler.displayChats;
        
        window.ChatHandler.displayChats = function(chats) {
            // Call the original function first
            originalDisplayChats(chats);
            
            // Then anonymize names
            setTimeout(anonymizeNames, 0);
        };
        
        // Also anonymize when messages are loaded
        const originalLoadUserMessages = window.ChatHandler.loadUserMessages;
        
        window.ChatHandler.loadUserMessages = function(userId) {
            // Call original function
            originalLoadUserMessages(userId);
            
            // Anonymize after a short delay
            setTimeout(anonymizeNames, 100);
        };
    }
    
    // Set up once DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        // Wait for chat handler to initialize first
        setTimeout(setupNameRandomization, 500);
    });
})();