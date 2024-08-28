import tkinter as tk
import logging
import sqlite3
from flask import Flask, jsonify, request
import threading
import os
import valve.source.a2s

# Настройка логирования
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s')

logging.info('Application started')

# Настройка базы данных
def init_db():
    if not os.path.exists('servers.db'):
        conn = sqlite3.connect('servers.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE servers
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      ip TEXT NOT NULL)''')
        conn.commit()
        conn.close()

def get_db_connection():
    conn = sqlite3.connect('servers.db', check_same_thread=False)
    return conn

init_db()

# Функция для добавления сервера в базу данных
def add_server(name, ip):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO servers (name, ip) VALUES (?, ?)", (name, ip))
        conn.commit()
        conn.close()
        logging.info(f'Server added: {name} ({ip})')
    except sqlite3.Error as e:
        logging.error(f'SQLite error: {e}')
    except Exception as e:
        logging.error(f'Error adding server: {e}')

# Функция для получения списка серверов
def get_servers():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM servers')
        servers = c.fetchall()
        conn.close()
        return servers
    except sqlite3.Error as e:
        logging.error(f'SQLite error: {e}')
        return []
    except Exception as e:
        logging.error(f'Error fetching servers: {e}')
        return []

# Функция для удаления сервера
def delete_server(server_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM servers WHERE id = ?', (server_id,))
        conn.commit()
        conn.close()
        logging.info(f'Server deleted: {server_id}')
    except sqlite3.Error as e:
        logging.error(f'SQLite error: {e}')
    except Exception as e:
        logging.error(f'Error deleting server: {e}')

# Функция для получения информации о сервере
def get_server_info(ip):
    try:
        address = (ip, 27015)  # Порт по умолчанию для CS 1.6
        with valve.source.a2s.ServerQuerier(address) as server:
            info = server.info()
            players = server.players()
            return {
                'name': info['server_name'],
                'map': info['map'],
                'players': len(players['players']),
                'max_players': info['max_players'],
                'ping': info['ping']
            }
    except Exception as e:
        logging.error(f'Error fetching server info: {e}')
        return None

# Настройка Flask API
app = Flask(__name__)

@app.route('/api/servers', methods=['GET'])
def api_get_servers():
    try:
        servers = get_servers()
        return jsonify({'servers': [{'id': s[0], 'name': s[1], 'ip': s[2]} for s in servers]})
    except Exception as e:
        logging.error(f'Error in API get_servers: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/api/servers', methods=['POST'])
def api_add_server():
    try:
        data = request.json
        add_server(data['name'], data['ip'])
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f'Error in API add_server: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/api/servers/<int:server_id>', methods=['DELETE'])
def api_delete_server(server_id):
    try:
        delete_server(server_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f'Error in API delete_server: {e}')
        return jsonify({'error': 'Internal Server Error'}), 500

# Функция для запуска Flask API в отдельном потоке
def run_api():
    app.run(debug=True, use_reloader=False)

# Настройка GUI
def on_add_server():
    name = name_entry.get()
    ip = ip_entry.get()
    add_server(name, ip)
    update_server_list()

def on_delete_server():
    selected = server_list.curselection()
    if selected:
        server_id = server_list.get(selected[0]).split()[0]
        delete_server(server_id)
        update_server_list()

def update_server_list():
    servers = get_servers()
    server_list.delete(0, tk.END)
    for server in servers:
        info = get_server_info(server[2])
        if info:
            server_list.insert(tk.END, f"{server[0]} {server[1]} ({server[2]}) - {info['players']}/{info['max_players']} players, Ping: {info['ping']} ms")
        else:
            server_list.insert(tk.END, f"{server[0]} {server[1]} ({server[2]}) - Info not available")
    root.after(5000, update_server_list)  # Update every 5 seconds

root = tk.Tk()
root.title("Server Monitor")

tk.Label(root, text="Server Name").grid(row=0, column=0, padx=10, pady=10)
name_entry = tk.Entry(root)
name_entry.grid(row=0, column=1, padx=10, pady=10)

tk.Label(root, text="Server IP").grid(row=1, column=0, padx=10, pady=10)
ip_entry = tk.Entry(root)
ip_entry.grid(row=1, column=1, padx=10, pady=10)

add_button = tk.Button(root, text="Add Server", command=on_add_server)
add_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

delete_button = tk.Button(root, text="Delete Server", command=on_delete_server)
delete_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

server_list = tk.Listbox(root)
server_list.grid(row=4, column=0, columnspan=2, padx=10, pady=10)

update_server_list()

# Запуск Flask API в отдельном потоке
api_thread = threading.Thread(target=run_api)
api_thread.start()

# Запуск GUI
root.mainloop()


