import subprocess
import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = 'change_this_secret_key_12345'
CORS(app)

# Default login credentials
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin123'

@app.route('/')
def index():
    return send_from_directory('templates', 'index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        session['logged_in'] = True
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'failed'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return jsonify({'status': 'ok'})

@app.route('/exec', methods=['POST'])
def execute():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    cmd = request.json.get('cmd', '').strip()
    if not cmd:
        return jsonify({'output': '', 'code': 0})
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        return jsonify({'output': output, 'code': result.returncode})
    except subprocess.TimeoutExpired:
        return jsonify({'output': 'Command timed out (30s)', 'code': -1})
    except Exception as e:
        return jsonify({'output': str(e), 'code': -1})

@app.route('/files', methods=['GET'])
def list_files():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    path = request.args.get('path', '.')
    if not os.path.exists(path):
        return jsonify({'error': 'Path not found'}), 404
    try:
        items = []
        for f in os.listdir(path):
            full = os.path.join(path, f)
            is_dir = os.path.isdir(full)
            size = os.path.getsize(full) if not is_dir else 0
            mtime = os.path.getmtime(full)
            items.append({
                'name': f,
                'is_dir': is_dir,
                'size': size,
                'modified': mtime
            })
        return jsonify({'files': items, 'path': path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file'}), 400
    path = request.form.get('path', '.')
    file.save(os.path.join(path, file.filename))
    return jsonify({'status': 'ok'})

@app.route('/download/<path:filename>', methods=['GET'])
def download(filename):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return send_from_directory('.', filename, as_attachment=True)

@app.route('/delete', methods=['POST'])
def delete():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    path = data.get('path')
    if not path or not os.path.exists(path):
        return jsonify({'error': 'Not found'}), 404
    try:
        if os.path.isdir(path):
            import shutil
            shutil.rmtree(path)
        else:
            os.remove(path)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/system', methods=['GET'])
def system_info():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()
        return jsonify({
            'cpu': cpu,
            'memory': {'total': mem.total, 'used': mem.used, 'free': mem.free, 'percent': mem.percent},
            'disk': {'total': disk.total, 'used': disk.used, 'free': disk.free, 'percent': disk.percent},
            'network': {'sent': net.bytes_sent, 'recv': net.bytes_recv}
        })
    except:
        return jsonify({'error': 'psutil not installed'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
