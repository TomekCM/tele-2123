<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Messenger Interface</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/push.js@1.0.12/bin/push.min.js"></script>
    <style>
        /* Add these styles to properly separate messages */
        .message {
            max-width: 70%;
            padding: 12px 15px;
            border-radius: 12px;
            margin-bottom: 15px;
            position: relative;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            clear: both;  /* Force each message to a new line */
            display: block;  /* Ensure block display */
        }

        .message-incoming {
            align-self: flex-start;
            background-color: white;
            border-top-left-radius: 4px;
            margin-right: auto;
            float: left;  /* Ensure left alignment */
        }

        .message-outgoing {
            align-self: flex-end;
            background-color: #dff8c6;
            border-top-right-radius: 4px;
            margin-left: auto;
            float: right;  /* Ensure right alignment */
        }

        /* Clear floats to ensure separation */
        .message::after {
            content: "";
            display: table;
            clear: both;
        }

        /* Date separator styling */
        .date-separator {
            text-align: center;
            margin: 15px 0;
            position: relative;
            clear: both;
            width: 100%;
        }

        .date-separator span {
            background-color: rgba(0, 0, 0, 0.5);
            color: white;
            padding: 5px 15px;
            border-radius: 15px;
            font-size: 12px;
            display: inline-block;
        }

        .messages-wrapper {
            width: 100%;
            display: flex;
            flex-direction: column;
        }

        /* Media source identification */
        .media-source {
            color: #777;
            font-size: 12px;
            margin-bottom: 5px;
            padding: 2px 5px;
            background-color: rgba(0,0,0,0.1);
            border-radius: 4px;
            display: inline-block;
        }
    </style>
    <!-- Add at the end of the <head> section -->
    <script src="{{ url_for('static', filename='js/chat-debug.js') }}"></script>
</head>
<body>
    <div class="messenger-container">
        <div class="sidebar">
            <div class="sidebar-header">
                <h2>Chats</h2>
                <div class="search-container">
                    <input type="text" id="searchInput" placeholder="Search...">
                    <i class="fas fa-search search-icon"></i>
                </div>
                <div class="user-actions">
                    <a href="{{ url_for('logout') }}" class="logout-btn">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </div>
                <!-- Add near the top of your sidebar -->
                <div class="refresh-container">
                    <button id="refreshChatsBtn" class="refresh-button">
                        <i class="fas fa-sync-alt"></i> Refresh Chats
                    </button>
                </div>
            </div>
            <div class="chat-list" id="chatList"></div>
            <div class="search-results" id="searchResults" style="display: none;"></div>
        </div>
        <div class="chat-container">
            <div class="chat-header" id="chatHeader">
                <h3>Select a chat</h3>
            </div>
            <div class="messages-container" id="messagesContainer">
                <div class="empty-chat-message">Select a chat on the left to start messaging</div>
            </div>
        </div>
    </div>
</body>
</html>
