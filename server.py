from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import datetime
import os
import json
import hashlib
import uuid
import logging
import mimetypes
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("server.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = '7653820469:AAHCZ_BGU9CDzCiC8i86Lvwz6Eua2S0f68U'  # Не забудь поменять на свой секретный ключ!

# Configure login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Create uploads folder if it doesn't exist
if not os.path.exists('static/uploads'):
    os.makedirs('static/uploads')

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('auth.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data:
        return User(user_data[0], user_data[1])
    return None

# Database helper functions
def get_db_connection(db_name):
    """Создает подключение к базе данных с row_factory"""
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize auth database if it doesn't exist
def init_auth_db():
    try:
        conn = sqlite3.connect('auth.db')
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Check if admin user exists, create if not
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        admin_user = cursor.fetchone()
        
        if not admin_user:
            # Create admin user with password 'admin'
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                ('admin', hashlib.sha256('admin'.encode()).hexdigest())
            )
            logger.info("Created default admin user")
        
        conn.commit()
        conn.close()
        logger.info("Auth database initialized")
    except Exception as e:
        logger.error(f"Error initializing auth database: {e}")

# Initialize message database
def init_messages_db():
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Create messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            message_text TEXT,
            timestamp TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            is_replied INTEGER DEFAULT 0,
            reply_text TEXT,
            telegram_sent INTEGER DEFAULT 0,
            has_media INTEGER DEFAULT 0,
            media_type TEXT,
            media_file_id TEXT,
            media_path TEXT
        )
        ''')
        
        # Create aliases table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS aliases (
            user_id INTEGER PRIMARY KEY,
            real_name TEXT,
            alias TEXT NOT NULL,
            created_at TEXT
        )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_sent ON messages (telegram_sent)')
        
        conn.commit()
        
        # Check if we have messages
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        logger.info(f"Message database initialized. Found {count} existing messages.")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing message database: {e}")

# Initialize databases
init_auth_db()
init_messages_db()

# Routes
@app.route('/')
@login_required
def index():
    logger.info(f"Index page accessed by user: {current_user.username}")
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required')
            return render_template('login.html', error='Username and password are required')
        
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect('auth.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username FROM users WHERE username = ? AND password = ?",
            (username, hashed_password)
        )
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data:
            user = User(user_data[0], user_data[1])
            login_user(user)
            logger.info(f"User logged in: {username}")
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/static/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    return send_from_directory('static/uploads', filename)

# API endpoints
@app.route('/api/chats')
@login_required
def get_chats():
    try:
        conn = get_db_connection('messages.db')
        cursor = conn.cursor()
        
        # Get chats with latest message for each user
        cursor.execute('''
        SELECT 
            m.user_id,
            m.username,
            m.first_name,
            m.message_text AS last_message_text,
            m.timestamp AS last_message_time,
            m.has_media,
            m.media_type,
            m.is_replied,
            m.reply_text,
            (SELECT COUNT(*) FROM messages 
             WHERE user_id = m.user_id AND is_read = 0 AND is_replied = 0) AS unread_count,
            a.alias
        FROM messages m
        LEFT JOIN aliases a ON m.user_id = a.user_id
        INNER JOIN (
            SELECT user_id, MAX(id) as max_id 
            FROM messages 
            GROUP BY user_id
        ) latest ON m.user_id = latest.user_id AND m.id = latest.max_id
        ORDER BY m.timestamp DESC
        ''')
        
        chats = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Retrieved {len(chats)} chats")
        
        conn.close()
        return jsonify(chats)
    except Exception as e:
        logger.error(f"Error fetching chats: {e}")
        return jsonify([])

@app.route('/api/messages/<int:user_id>')
@login_required
def get_messages(user_id):
    try:
        conn = get_db_connection('messages.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT 
            m.*,
            a.alias
        FROM messages m
        LEFT JOIN aliases a ON m.user_id = a.user_id
        WHERE m.user_id = ?
        ORDER BY m.timestamp
        ''', (user_id,))
        
        messages = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Retrieved {len(messages)} messages for user {user_id}")
        
        conn.close()
        return jsonify(messages)
    except Exception as e:
        logger.error(f"Error fetching messages for user {user_id}: {e}")
        return jsonify([])

@app.route('/api/messages/<int:user_id>/read', methods=['POST'])
@login_required
def mark_as_read(user_id):
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE messages SET is_read = 1 WHERE user_id = ? AND is_read = 0 AND is_replied = 0",
            (user_id,)
        )
        
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Marked {updated} messages as read for user {user_id}")
        return jsonify({'success': True, 'updated': updated})
    except Exception as e:
        logger.error(f"Error marking messages as read for user {user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/reply', methods=['POST'])
@login_required
def reply():
    try:
        logger.info(f"Received reply request: Content-Type: {request.headers.get('Content-Type')}")
        
        # Проверяем, пришел ли запрос как JSON или как форма
        if request.is_json:
            data = request.json
            logger.info(f"Request JSON data: {data}")
            user_id = data.get('user_id')
            reply_text = data.get('reply_text')
        else:
            logger.info(f"Request form data: {request.form}")
            user_id = request.form.get('user_id')
            reply_text = request.form.get('reply_text')
        
        logger.info(f"Parsed user_id: {user_id}, reply_text: {reply_text[:30] if reply_text else None}")
        
        if not user_id or not reply_text:
            error_msg = 'Missing required fields'
            logger.error(f"Error in reply: {error_msg}")
            return jsonify({'success': False, 'error': error_msg})
        
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ВАЖНО: telegram_sent = 0, чтобы бот отправил сообщение
        logger.info(f"Inserting reply for user {user_id} with telegram_sent=0")
        cursor.execute(
            """INSERT INTO messages 
               (user_id, message_text, timestamp, is_read, is_replied, reply_text, telegram_sent) 
               VALUES (?, NULL, ?, 1, 1, ?, 0)""",
            (user_id, timestamp, reply_text)
        )
        
        new_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully added reply (ID: {new_id}) to user {user_id}")
        return jsonify({'success': True, 'message_id': new_id})
    except Exception as e:
        logger.error(f"Error sending reply: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/message/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Get media path if any
        cursor.execute("SELECT media_path FROM messages WHERE id = ?", (message_id,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Message not found'})
        
        media_path = result[0]
        
        # Delete the message
        cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        
        conn.commit()
        conn.close()
        
        # Delete media file if exists
        if media_path and os.path.exists(media_path.lstrip('/')):
            try:
                os.remove(media_path.lstrip('/'))
            except Exception as e:
                logger.error(f"Error deleting media file: {e}")
        
        logger.info(f"Deleted message {message_id}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/conversation/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_conversation(user_id):
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Get all media files to delete
        cursor.execute("SELECT media_path FROM messages WHERE user_id = ? AND media_path IS NOT NULL", (user_id,))
        media_paths = cursor.fetchall()
        
        # Delete all messages for this user
        cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
        
        # Remove alias if exists
        cursor.execute("DELETE FROM aliases WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        # Delete media files
        for path in media_paths:
            if path[0] and os.path.exists(path[0].lstrip('/')):
                try:
                    os.remove(path[0].lstrip('/'))
                except Exception as e:
                    logger.error(f"Error deleting media file: {e}")
        
        logger.info(f"Deleted conversation with user {user_id}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting conversation with user {user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/set-alias', methods=['POST'])
@login_required
def set_alias():
    try:
        data = request.json
        user_id = data.get('user_id')
        alias = data.get('alias')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Missing user_id'})
        
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get the real name for this user
        cursor.execute(
            "SELECT first_name FROM messages WHERE user_id = ? AND first_name IS NOT NULL LIMIT 1",
            (user_id,)
        )
        result = cursor.fetchone()
        real_name = result[0] if result else None
        
        # Check if alias already exists
        cursor.execute("SELECT user_id FROM aliases WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            if alias:  # Update existing alias
                cursor.execute(
                    "UPDATE aliases SET alias = ? WHERE user_id = ?",
                    (alias, user_id)
                )
            else:  # Remove alias if empty
                cursor.execute("DELETE FROM aliases WHERE user_id = ?", (user_id,))
        elif alias:  # Insert new alias if not empty
            cursor.execute(
                "INSERT INTO aliases (user_id, real_name, alias, created_at) VALUES (?, ?, ?, ?)",
                (user_id, real_name, alias, timestamp)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Set alias for user {user_id}: {alias}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error setting alias: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/new-messages')
@login_required
def check_new_messages():
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Find users with unread messages
        cursor.execute(
            "SELECT DISTINCT user_id FROM messages WHERE is_read = 0 AND is_replied = 0"
        )
        
        user_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        logger.info(f"Checked for new messages. Found {len(user_ids)} users with unread messages.")
        return jsonify({
            'has_new': len(user_ids) > 0,
            'user_ids': user_ids
        })
    except Exception as e:
        logger.error(f"Error checking for new messages: {e}")
        return jsonify({'has_new': False, 'user_ids': []})

@app.route('/api/search')
@login_required
def search():
    try:
        term = request.args.get('term', '')
        
        if not term or len(term) < 2:
            return jsonify([])
        
        conn = get_db_connection('messages.db')
        cursor = conn.cursor()
        
        # Search in messages
        cursor.execute('''
        SELECT 
            m.id,
            m.user_id,
            m.first_name,
            m.message_text,
            m.reply_text,
            m.timestamp,
            m.is_replied,
            CASE
                WHEN m.message_text LIKE ? THEN m.message_text
                ELSE m.reply_text
            END as content,
            a.alias
        FROM messages m
        LEFT JOIN aliases a ON m.user_id = a.user_id
        WHERE m.message_text LIKE ? OR m.reply_text LIKE ?
        ORDER BY m.timestamp DESC
        LIMIT 50
        ''', (f'%{term}%', f'%{term}%', f'%{term}%'))
        
        results = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Search for '{term}' returned {len(results)} results")
        
        conn.close()
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error searching for '{term}': {e}")
        return jsonify([])

@app.route('/diagnostic')
@login_required
def diagnostic_page():
    """Диагностическая страница для проверки отправки сообщений"""
    try:
        # Получаем ID последнего пользователя из базы данных
        conn = get_db_connection('messages.db')
        cursor = conn.cursor()
        
        # Получаем ID последнего пользователя
        cursor.execute("SELECT DISTINCT user_id FROM messages ORDER BY id DESC LIMIT 1")
        user_result = cursor.fetchone()
        user_id = user_result['user_id'] if user_result else ""
        
        # Получаем сообщения, ожидающие отправки
        cursor.execute('''
        SELECT 
            id, user_id, reply_text, timestamp, telegram_sent
        FROM messages 
        WHERE is_replied = 1 AND telegram_sent = 0
        ORDER BY timestamp DESC
        ''')
        
        pending_messages = [dict(row) for row in cursor.fetchall()]
        
        # Получаем последние отправленные сообщения
        cursor.execute('''
        SELECT 
            id, user_id, reply_text, timestamp, telegram_sent
        FROM messages 
        WHERE is_replied = 1
        ORDER BY timestamp DESC
        LIMIT 10
        ''')
        
        recent_messages = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # HTML для диагностической страницы с формой отправки
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Diagnostic Page</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .form-container {{ border: 1px solid #ddd; padding: 20px; margin-bottom: 20px; }}
                .message {{ border-bottom: 1px solid #eee; padding: 10px 0; }}
                .message-sent {{ background-color: #f0fff0; }}
                .message-pending {{ background-color: #fff0f0; }}
                button {{ padding: 10px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }}
                textarea {{ width: 100%; height: 100px; padding: 10px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>Diagnostic Page</h1>
            
            <div class="form-container">
                <h2>Send test message via HTML form</h2>
                <form action="/api/direct-send" method="post">
                    <div>
                        <label for="user_id">User ID:</label>
                        <input type="text" id="user_id" name="user_id" value="{user_id}" required>
                    </div>
                    <div>
                        <label for="message">Message:</label>
                        <textarea id="message" name="message" required>Test message from diagnostic form</textarea>
                    </div>
                    <button type="submit">Send Message</button>
                </form>
            </div>
            
            <div class="form-container">
                <h2>Send test message via AJAX (JSON)</h2>
                <div>
                    <label for="ajax_user_id">User ID:</label>
                    <input type="text" id="ajax_user_id" value="{user_id}" required>
                </div>
                <div>
                    <label for="ajax_message">Message:</label>
                    <textarea id="ajax_message" required>Test message from AJAX</textarea>
                </div>
                <button onclick="sendAjaxMessage()">Send Message (AJAX)</button>
                <div id="ajax_result" style="margin-top: 10px; padding: 10px; border: 1px solid #ddd;"></div>
            </div>
            
            <h2>Pending Messages ({len(pending_messages)})</h2>
            <div>
                {"".join(f'''
                <div class="message message-pending">
                    <p><strong>ID:</strong> {msg['id']}</p>
                    <p><strong>User ID:</strong> {msg['user_id']}</p>
                    <p><strong>Text:</strong> {msg['reply_text']}</p>
                    <p><strong>Time:</strong> {msg['timestamp']}</p>
                    <p><strong>Status:</strong> Pending (telegram_sent={msg['telegram_sent']})</p>
                </div>
                ''' for msg in pending_messages) if pending_messages else "<p>No pending messages</p>"}
            </div>
            
            <h2>Recent Messages</h2>
            <div>
                {"".join(f'''
                <div class="message {'message-sent' if msg['telegram_sent'] == 1 else 'message-pending'}">
                    <p><strong>ID:</strong> {msg['id']}</p>
                    <p><strong>User ID:</strong> {msg['user_id']}</p>
                    <p><strong>Text:</strong> {msg['reply_text']}</p>
                    <p><strong>Time:</strong> {msg['timestamp']}</p>
                    <p><strong>Status:</strong> {"Sent" if msg['telegram_sent'] == 1 else "Pending"} (telegram_sent={msg['telegram_sent']})</p>
                </div>
                ''' for msg in recent_messages) if recent_messages else "<p>No recent messages</p>"}
            </div>
            
            <script>
                function sendAjaxMessage() {{
                    const userId = document.getElementById('ajax_user_id').value;
                    const message = document.getElementById('ajax_message').value;
                    const resultDiv = document.getElementById('ajax_result');
                    
                    if (!userId || !message) {{
                        resultDiv.innerHTML = "<p style='color: red;'>Please fill in all fields</p>";
                        return;
                    }}
                    
                    resultDiv.innerHTML = "<p>Sending message...</p>";
                    
                    fetch('/api/reply', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            user_id: userId,
                            reply_text: message
                        }})
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        resultDiv.innerHTML = `<p>Response: ${{JSON.stringify(data)}}</p>`;
                        if (data.success) {{
                            resultDiv.innerHTML += "<p style='color: green;'>✅ Message sent successfully! Refresh page to see updates.</p>";
                        }} else {{
                            resultDiv.innerHTML += `<p style='color: red;'>❌ Error: ${{data.error || 'Unknown error'}}</p>`;
                        }}
                    }})
                    .catch(error => {{
                        resultDiv.innerHTML = `<p style='color: red;'>❌ Error: ${{error.message}}</p>`;
                    }});
                }}
            </script>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Error rendering diagnostic page: {e}")
        return f"Error: {e}"

@app.route('/api/direct-send', methods=['POST'])
@login_required
def direct_send():
    """Прямая отправка сообщения через обычную форму HTML"""
    try:
        user_id = request.form.get('user_id')
        message = request.form.get('message')
        
        if not user_id or not message:
            return "Error: Missing user_id or message", 400
        
        # Сохраняем сообщение в базе данных
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute(
            """INSERT INTO messages 
               (user_id, message_text, timestamp, is_read, is_replied, reply_text, telegram_sent) 
               VALUES (?, NULL, ?, 1, 1, ?, 0)""",
            (user_id, timestamp, message)
        )
        
        message_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Added direct message (ID: {message_id}) to user {user_id}")
        
        # Перенаправляем обратно на диагностическую страницу
        return redirect(url_for('diagnostic_page'))
    except Exception as e:
        logger.error(f"Error sending direct message: {e}")
        return f"Error: {e}", 500

@app.route('/debug')
@login_required
def debug_page():
    try:
        conn = get_db_connection('messages.db')
        cursor = conn.cursor()
        
        # Get database stats
        cursor.execute("SELECT COUNT(*) as count FROM messages")
        message_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM messages")
        user_count = cursor.fetchone()['count']
        
        # Get users
        cursor.execute('''
        SELECT 
            m.user_id,
            m.first_name,
            a.alias,
            COUNT(*) as message_count,
            MAX(m.timestamp) as last_message,
            SUM(CASE WHEN m.is_read = 0 AND m.is_replied = 0 THEN 1 ELSE 0 END) as unread_count
        FROM messages m
        LEFT JOIN aliases a ON m.user_id = a.user_id
        GROUP BY m.user_id
        ORDER BY last_message DESC
        ''')
        
        users = [dict(row) for row in cursor.fetchall()]
        
        # Get recent messages
        cursor.execute('''
        SELECT 
            id,
            user_id,
            first_name,
            message_text,
            reply_text,
            timestamp,
            is_read,
            is_replied,
            telegram_sent
        FROM messages
        ORDER BY timestamp DESC
        LIMIT 10
        ''')
        
        recent_messages = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('debug.html', 
                              message_count=message_count,
                              user_count=user_count,
                              users=users,
                              recent_messages=recent_messages)
    except Exception as e:
        logger.error(f"Error rendering debug page: {e}")
        return f"Error: {e}"

@app.route('/add-test-message')
@login_required
def add_test_message():
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Current timestamp
        now = datetime.datetime.now()
        timestamp1 = now.strftime("%Y-%m-%d %H:%M:%S")
        timestamp2 = (now - datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Add incoming message
        cursor.execute(
            """INSERT INTO messages 
            (user_id, username, first_name, message_text, timestamp, is_read, is_replied) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (123456789, 'test_user', 'Test User', 'Hello! This is a test message to verify chat display.', 
             timestamp2, 0, 0)
        )
        
        # Add outgoing reply with telegram_sent = 0
        cursor.execute(
            """INSERT INTO messages 
            (user_id, message_text, timestamp, is_read, is_replied, reply_text, telegram_sent) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (123456789, None, timestamp1, 1, 1, 'This is a test reply from the system.', 0)
        )
        
        conn.commit()
        conn.close()
        
        logger.info("Added test messages successfully")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error adding test message: {e}")
        return f"Error: {e}"

# Маршрут для загрузки файлов
@app.route('/api/upload-file', methods=['POST'])
@login_required
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'})
        
        file = request.files['file']
        user_id = request.form.get('user_id')
        
        if not file or not user_id:
            return jsonify({'success': False, 'error': 'Missing file or user ID'})
        
        # Определяем тип файла
        mime_type = file.content_type
        media_type = 'document'  # По умолчанию
        
        if mime_type.startswith('image/'):
            media_type = 'photo'
        elif mime_type.startswith('video/'):
            media_type = 'video'
        elif mime_type.startswith('audio/'):
            media_type = 'audio'
        
        # Генерируем уникальное имя файла
        original_filename = secure_filename(file.filename)
        file_ext = os.path.splitext(original_filename)[1]
        if not file_ext and mime_type:
            ext = mimetypes.guess_extension(mime_type)
            if ext:
                file_ext = ext
        
        unique_filename = uuid.uuid4().hex + file_ext
        upload_folder = os.path.join('static', 'uploads')
        
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Сохраняем информацию о файле в БД
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ВАЖНО: telegram_sent = 0, чтобы бот отправил сообщение
        cursor.execute(
            """INSERT INTO messages 
            (user_id, message_text, timestamp, is_read, is_replied, reply_text,
             has_media, media_type, media_path, telegram_sent) 
            VALUES (?, NULL, ?, 1, 1, ?, 1, ?, ?, 0)""",
            (user_id, timestamp, "Sent file", media_type, '/' + file_path.replace('\\', '/'))
        )
        
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Uploaded file (ID: {new_id}) for user {user_id}: {unique_filename}")
        return jsonify({'success': True, 'file_path': '/' + file_path.replace('\\', '/')})
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Маршрут для диагностики отправки сообщений
@app.route('/debug/pending-messages')
@login_required
def pending_messages():
    try:
        conn = get_db_connection('messages.db')
        cursor = conn.cursor()
        
        # Получаем сообщения, ожидающие отправки
        cursor.execute('''
        SELECT 
            id, user_id, reply_text, timestamp, telegram_sent
        FROM messages 
        WHERE is_replied = 1 AND telegram_sent = 0
        ORDER BY timestamp DESC
        ''')
        
        pending = [dict(row) for row in cursor.fetchall()]
        
        # Получаем последние отправленные сообщения
        cursor.execute('''
        SELECT 
            id, user_id, reply_text, timestamp, telegram_sent
        FROM messages 
        WHERE is_replied = 1 AND telegram_sent = 1
        ORDER BY timestamp DESC
        LIMIT 5
        ''')
        
        sent = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'pending_count': len(pending),
            'pending_messages': pending,
            'recent_sent': sent
        })
    except Exception as e:
        logger.error(f"Error checking pending messages: {e}")
        return jsonify({'error': str(e)})

# Маршрут для сброса флагов отправки (для диагностики)
@app.route('/debug/reset-sent-flags', methods=['POST'])
@login_required
def reset_sent_flags():
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Сбрасываем флаг для сообщений, которые были отмечены как отправленные, но могли не дойти
        cursor.execute('''
        UPDATE messages 
        SET telegram_sent = 0 
        WHERE is_replied = 1 AND telegram_sent = 1 AND id > (SELECT MAX(id) - 50 FROM messages)
        ''')
        
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Reset telegram_sent flag for {updated} messages")
        return jsonify({'success': True, 'reset_count': updated})
    except Exception as e:
        logger.error(f"Error resetting telegram_sent flags: {e}")
        return jsonify({'success': False, 'error': str(e)})

# Add debug template filter
@app.template_filter('format_time')
def format_time(timestamp):
    if not timestamp:
        return ''
    try:
        dt = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp

# Улучшенная обработка ошибок
@app.errorhandler(Exception)
def handle_error(e):
    logger.error(f"Unhandled error: {str(e)}")
    import traceback
    traceback.print_exc()
    return jsonify({"success": False, "error": str(e)}), 500

# Добавляем маршрут для мониторинга бота
@app.route('/monitor')
@login_required
def monitor():
    """Страница мониторинга системы"""
    try:
        conn = get_db_connection('messages.db')
        cursor = conn.cursor()
        
        # Статистика сообщений
        cursor.execute("SELECT COUNT(*) as total FROM messages")
        total_messages = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM messages WHERE telegram_sent = 0 AND is_replied = 1")
        pending_messages = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM messages WHERE telegram_sent = 1 AND is_replied = 1")
        sent_messages = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM messages WHERE is_read = 0 AND is_replied = 0")
        unread_messages = cursor.fetchone()['total']
        
        # Последние активные пользователи
        cursor.execute('''
        SELECT 
            m.user_id,
            m.username,
            m.first_name,
            a.alias,
            MAX(m.timestamp) as last_active,
            COUNT(*) as message_count
        FROM messages m
        LEFT JOIN aliases a ON m.user_id = a.user_id
        GROUP BY m.user_id
        ORDER BY last_active DESC
        LIMIT 10
        ''')
        
        active_users = [dict(row) for row in cursor.fetchall()]
        
        # Ошибки отправки (сообщения старше 5 минут, которые не отправлены)
        time_threshold = (datetime.datetime.now() - datetime.timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
        SELECT 
            id, user_id, reply_text, timestamp
        FROM messages 
        WHERE is_replied = 1 
          AND telegram_sent = 0 
          AND timestamp < ?
        ORDER BY timestamp ASC
        ''', (time_threshold,))
        
        failed_messages = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('monitor.html', 
                               total_messages=total_messages,
                               pending_messages=pending_messages,
                               sent_messages=sent_messages,
                               unread_messages=unread_messages,
                               active_users=active_users,
                               failed_messages=failed_messages)
    except Exception as e:
        logger.error(f"Error rendering monitor page: {e}")
        return f"Error: {e}"

# Маршрут для принудительной отправки проблемных сообщений
@app.route('/debug/force-send-message/<int:message_id>', methods=['POST'])
@login_required
def force_send_message(message_id):
    try:
        conn = sqlite3.connect('messages.db')
        cursor = conn.cursor()
        
        # Обновляем статус сообщения
        cursor.execute("UPDATE messages SET telegram_sent = 0 WHERE id = ?", (message_id,))
        
        # Проверяем, было ли обновление успешным
        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"Message {message_id} marked for resending")
            status = "success"
            message = f"Message {message_id} marked for resending"
        else:
            logger.error(f"Message {message_id} not found")
            status = "error"
            message = f"Message {message_id} not found"
        
        conn.close()
        return jsonify({'status': status, 'message': message})
    except Exception as e:
        logger.error(f"Error force-sending message {message_id}: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    logger.info("Starting server on http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)