document.addEventListener('DOMContentLoaded', function() {
    let currentUserId = null;
    let currentMessageId = null;
    const chatList = document.getElementById('chatList');
    const messagesContainer = document.getElementById('messagesContainer');
    const chatHeader = document.getElementById('chatHeader');
    const replyContainer = document.getElementById('replyContainer');
    const replyText = document.getElementById('replyText');
    const sendButton = document.getElementById('sendButton');

    // Загружаем список чатов
    function loadChats() {
        fetch('/api/chats')
            .then(response => response.json())
            .then(chats => {
                chatList.innerHTML = '';
                chats.forEach(chat => {
                    const chatItem = document.createElement('div');
                    chatItem.className = 'chat-item';
                    chatItem.dataset.userId = chat.user_id;
                    
                    // Получаем первую букву имени для аватара
                    const initial = (chat.first_name || chat.username || 'U').charAt(0).toUpperCase();
                    
                    chatItem.innerHTML = `
                        <div class="chat-avatar">${initial}</div>
                        <div class="chat-info">
                            <div class="chat-header-row">
                                <div class="chat-name">${chat.first_name || chat.username || 'Пользователь'}</div>
                                <div class="chat-time">${formatTime(chat.timestamp)}</div>
                            </div>
                            <div class="chat-last-message">${chat.message_text}</div>
                        </div>
                        ${chat.unread_count > 0 ? `<div class="unread-badge">${chat.unread_count}</div>` : ''}
                    `;
                    
                    chatItem.addEventListener('click', () => loadMessages(chat.user_id, chat.first_name || chat.username || 'Пользователь'));
                    chatList.appendChild(chatItem);
                });
            })
            .catch(error => console.error('Ошибка при загрузке чатов:', error));
    }

    // Загружаем сообщения для выбранного чата
    function loadMessages(userId, userName) {
        currentUserId = userId;
        
        // Обновляем заголовок чата
        chatHeader.innerHTML = `<h3>${userName}</h3>`;
        
        // Показываем контейнер для ответа
        replyContainer.style.display = 'flex';
        
        // Удаляем класс active у всех чатов
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Добавляем класс active текущему чату
        document.querySelector(`.chat-item[data-user-id="${userId}"]`).classList.add('active');
        
        fetch(`/api/messages/${userId}`)
            .then(response => response.json())
            .then(messages => {
                messagesContainer.innerHTML = '';
                
                if (messages.length === 0) {
                    messagesContainer.innerHTML = '<div class="empty-chat-message">Нет сообщений</div>';
                    return;
                }
                
                messages.forEach(message => {
                    // Создаем элемент для сообщения пользователя
                    const messageEl = document.createElement('div');
                    messageEl.className = 'message message-incoming';
                    messageEl.innerHTML = `
                        <div class="message-text">${message.message_text}</div>
                        <div class="message-time">${formatTime(message.timestamp)}</div>
                    `;
                    messagesContainer.appendChild(messageEl);
                    
                    // Если есть ответ, создаем элемент для ответа
                    if (message.is_replied && message.reply_text) {
                        const replyEl = document.createElement('div');
                        replyEl.className = 'message message-outgoing';
                        replyEl.innerHTML = `
                            <div class="message-text">${message.reply_text}</div>
                            <div class="message-time">${formatTime(message.timestamp)}</div>
                        `;
                        messagesContainer.appendChild(replyEl);
                    }
                    
                    // Сохраняем ID последнего сообщения без ответа для отправки ответа
                    if (!message.is_replied) {
                        currentMessageId = message.id;
                    }
                });
                
                // Прокручиваем к последнему сообщению
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            })
            .catch(error => console.error('Ошибка при загрузке сообщений:', error));
    }

    // Отправка ответа
    sendButton.addEventListener('click', sendReply);
    replyText.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendReply();
        }
    });

    function sendReply() {
        const text = replyText.value.trim();
        if (!text || !currentUserId || !currentMessageId) return;
        
        fetch('/api/reply', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: currentUserId,
                message_id: currentMessageId,
                reply_text: text
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Очищаем поле ввода
                replyText.value = '';
                
                // Перезагружаем сообщения, чтобы показать ответ
                loadMessages(currentUserId, document.querySelector('.chat-header h3').textContent);
                
                // Обновляем список чатов
                loadChats();
            }
        })
        .catch(error => console.error('Ошибка при отправке ответа:', error));
    }

    // Форматирование времени
    function formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // Периодическое обновление чатов
    loadChats();
    setInterval(loadChats, 10000); // Обновляем каждые 10 секунд
});