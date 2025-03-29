import os
import sys
import subprocess
import sqlite3
import time
import datetime
import psutil

def print_header():
    print("\n" + "=" * 60)
    print("TELEGRAM MESSENGER SYSTEM - STARTUP")
    print("Current time:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

def kill_existing_processes():
    """Kill any existing Python processes that might conflict"""
    print("Checking for existing Python processes...")
    
    killed = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Проверяем, это Python-процесс?
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and len(cmdline) > 1:
                    # Проверяем, связан ли он с нашей системой
                    script_name = os.path.basename(cmdline[1])
                    if script_name in ['bot.py', 'server.py', 'message_sender.py']:
                        print(f"Terminating existing process: {script_name} (PID: {proc.info['pid']})")
                        try:
                            proc.terminate()
                            killed += 1
                        except:
                            print(f"Could not terminate process {proc.info['pid']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed > 0:
        print(f"Terminated {killed} existing processes.")
        time.sleep(2)  # Дадим процессам время завершиться
    else:
        print("No existing processes found.")

def ensure_database_exists():
    """Initialize the database if it doesn't exist or has missing tables"""
    print("Checking database...")
    
    db_exists = os.path.exists('messages.db')
    if not db_exists:
        print("Database not found. Creating new database...")
    else:
        print("Database found. Verifying structure...")
    
    conn = sqlite3.connect('messages.db')
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')
    
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
    
    # Create search index table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS message_search (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        user_id INTEGER,
        content TEXT,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages (user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)')
    
    # Create uploads directory if it doesn't exist
    if not os.path.exists('static/uploads'):
        print("Creating static/uploads directory...")
        os.makedirs('static/uploads')
    
    # Commit changes and close connection
    conn.commit()
    
    # Verify structure
    cursor.execute("SELECT COUNT(*) FROM messages")
    msg_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('messages', 'aliases', 'message_search')")
    table_count = cursor.fetchone()[0]
    
    conn.close()
    
    if table_count == 3:
        print(f"Database verified successfully. Found {msg_count} messages.")
    else:
        print(f"Database verification issue. Expected 3 tables, found {table_count}.")
    
    return True

def start_bot():
    """Start the Telegram bot in a separate process"""
    print("\nStarting Telegram bot...")
    bot_process = subprocess.Popen([sys.executable, 'bot.py'], 
                                  creationflags=subprocess.CREATE_NEW_CONSOLE)
    print(f"Bot process started with PID: {bot_process.pid}")
    return bot_process

def start_message_sender():
    """Start the message sender in a separate process"""
    print("\nStarting message sender...")
    sender_process = subprocess.Popen([sys.executable, 'message_sender.py'],
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    print(f"Message sender process started with PID: {sender_process.pid}")
    return sender_process

def start_server():
    """Start the Flask server in a separate process"""
    print("\nStarting web server...")
    server_process = subprocess.Popen([sys.executable, 'server.py'],
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    print(f"Web server process started with PID: {server_process.pid}")
    return server_process

def main():
    print_header()
    
    try:
        # Останавливаем существующие процессы
        kill_existing_processes()
        
        # Initialize database
        ensure_database_exists()
        
        # Start components in the right order
        bot_process = start_bot()
        print("Waiting for bot to initialize...")
        time.sleep(5)  # Give bot more time to initialize
        
        sender_process = start_message_sender()
        print("Waiting for message sender to initialize...")
        time.sleep(2)
        
        server_process = start_server()
        
        print("\n" + "=" * 60)
        print("All components started successfully!")
        print("Web interface should be available at: http://localhost:5000")
        print("=" * 60 + "\n")
        
        print("Press Ctrl+C to stop all services...")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
            # Check if processes are still running
            if bot_process.poll() is not None:
                print("\nWARNING: Bot process has stopped! Restarting...")
                bot_process = start_bot()
                
            if sender_process.poll() is not None:
                print("\nWARNING: Message sender process has stopped! Restarting...")
                sender_process = start_message_sender()
                
            if server_process.poll() is not None:
                print("\nWARNING: Web server process has stopped! Restarting...")
                server_process = start_server()
            
    except KeyboardInterrupt:
        print("\nShutting down services...")
        # Cleanup will happen automatically when script ends
    
    print("System shutdown complete.")

if __name__ == "__main__":
    # Ensure psutil is installed
    try:
        import psutil
    except ImportError:
        print("Installing required package: psutil")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
    
    main()