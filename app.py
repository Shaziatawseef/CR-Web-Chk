import eventlet
eventlet.monkey_patch()
import os
import threading
import time
import shutil
from datetime import datetime
import json
import uuid
import io
import logging

from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this'
socketio = SocketIO(app, cors_allowed_origins="*")


import chk


active_sessions = {}


SESSION_DATA_FILE = "session_data.json"

def create_session(existing_session_id=None):
    if existing_session_id:
        session_id = existing_session_id
        session_dir = ensure_session_directory(session_id)
        session_data_path = os.path.join(session_dir, SESSION_DATA_FILE)

        if os.path.exists(session_data_path):
            try:
                with open(session_data_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                logger.info(f"Loaded existing session data for {session_id}")

                session_data.setdefault('session_id', session_id)
                session_data.setdefault('timestamp', datetime.now().isoformat())
                session_data.setdefault('created_at', time.time())
                session_data.setdefault('combo_file', None)
                session_data.setdefault('proxy_file', None)
                session_data.setdefault('proxy_type', 'http')
                session_data.setdefault('threads', 10)
                session_data.setdefault('is_running', False)
                session_data.setdefault('is_paused', False)
                session_data.setdefault('status_message_id', None)
                session_data.setdefault('current_session_id', session_id) 
                session_data.setdefault('combo_line_count', 0) 
                session_data.setdefault('proxy_line_count', 0) 


                if session_data['is_running']:
                    session_data['is_paused'] = True
                    logger.info(f"Auto-paused running checker for session {session_id} on reconnection.")

                    if session_id not in chk.counters:
                        chk.counters[session_id] = {
                            'checked': 0, 'invalid': 0, 'hits': 0, 'custom': 0,
                            'total_mega_fan': 0, 'total_fan_member': 0, 'total_ultimate_mega': 0,
                            'errors': 0, 'retries': 0,
                            'is_running': True, 
                            'is_paused': True,
                            'completed': False,
                            'start_time': datetime.fromisoformat(session_data['timestamp']),
                            'end_time': None,
                            'total_lines': session_data['combo_line_count']
                        }
                        logger.info(f"Re-initialized chk.counters for auto-paused session {session_id}.")
                    else:
                        chk.counters[session_id]['is_paused'] = True
                        logger.info(f"Updated chk.counters for {session_id} to paused.")

                active_sessions[session_id] = session_data
                return session_id, session_data
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON for session {session_id}: {e}. Creating new session data.")
        else:
            logger.info(f"No session_data.json found for {session_id}. Creating new session data.")

    session_id = str(uuid.uuid4())
    session_dir = ensure_session_directory(session_id) 

    session_data = {
        'session_id': session_id,
        'timestamp': datetime.now().isoformat(),
        'created_at': time.time(),
        'combo_file': None,
        'proxy_file': None,
        'proxy_type': 'http',
        'threads': 10,
        'is_running': False,
        'is_paused': False,
        'status_message_id': None,
        'current_session_id': session_id, 
        'combo_line_count': 0, 
        'proxy_line_count': 0 
    }

    active_sessions[session_id] = session_data
    save_session_data(session_id) 
    logger.info(f"Created new session: {session_id}")
    return session_id, session_data

def save_session_data(session_id):
    if session_id not in active_sessions:
        logger.warning(f"Attempted to save non-existent session: {session_id}")
        return

    session_data = active_sessions[session_id]
    session_dir = ensure_session_directory(session_id)
    session_data_path = os.path.join(session_dir, SESSION_DATA_FILE)

    try:
        with open(session_data_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=4)
        logger.debug(f"Saved session data for {session_id}")
    except Exception as e:
        logger.error(f"Failed to save session data for {session_id}: {e}")

def ensure_session_directory(session_id):
    directory = f"session_{session_id}"
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created session directory: {directory}")
    return directory

def reset_hits_file(session_id):
    session_dir = f"session_{session_id}"
    hit_file_path = f"{session_dir}/hits.txt"
    custom_file_path = f"{session_dir}/custom.txt"

    open(hit_file_path, 'w').close()
    open(custom_file_path, 'w').close()
    logger.info(f"Reset hits.txt and custom.txt for session {session_id}")

def clean_session_directory(session_id):
    directory = f"session_{session_id}"
    if not os.path.exists(directory):
        logger.warning(f"Attempted to clean non-existent directory: {directory}")
        return

    logger.info(f"Cleaning session directory: {directory}")


    hits_file = os.path.join(directory, "hits.txt")
    custom_file = os.path.join(directory, "custom.txt")

    backup_dir = os.path.join(directory, "backup")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        logger.info(f"Created backup directory: {backup_dir}")

    timestamp = time.strftime("%Y%m%d-%H%M%S")


    if os.path.exists(hits_file) and os.path.getsize(hits_file) > 0:
        backup_file = os.path.join(backup_dir, f"hits_{timestamp}.txt")
        shutil.copy2(hits_file, backup_file)
        logger.info(f"Backed up hits.txt to {backup_file}")


    if os.path.exists(custom_file) and os.path.getsize(custom_file) > 0:
        backup_file = os.path.join(backup_dir, f"custom_{timestamp}.txt")
        shutil.copy2(custom_file, backup_file)
        logger.info(f"Backed up custom.txt to {backup_file}")


    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if filename not in ["backup", SESSION_DATA_FILE] and os.path.isfile(file_path):
            try:
                os.remove(file_path)
                logger.debug(f"Removed file: {file_path}")
            except PermissionError:
                logger.warning(f"PermissionError: Could not delete {file_path}. It may be in use.")
            except Exception as e:
                logger.error(f"Error removing file {file_path}: {e}")

@app.route('/crun')
def index():
    return render_template('index.html')


@app.route('/upload_file', methods=['POST'])
def upload_file():
    session_id = request.form.get('session_id')
    file_type = request.form.get('file_type') 

    if not session_id or session_id not in active_sessions:
        logger.error(f"File upload failed: Invalid session ID {session_id}")
        return jsonify({'status': 'error', 'message': 'Invalid session ID'}), 400

    if 'file' not in request.files:
        logger.error(f"File upload failed for session {session_id}: No file part")
        return jsonify({'status': 'error', 'message': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        logger.error(f"File upload failed for session {session_id}: No selected file")
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    session_data = active_sessions[session_id]
    if session_data.get('is_running', False):
        logger.warning(f"Attempted to upload {file_type} while checker is running for session {session_id}")
        return jsonify({'status': 'error', 'message': '❌ UPLOAD FAILED. Stop the checker first.'}), 400

    session_dir = ensure_session_directory(session_id)
    file_path = os.path.join(session_dir, f"{file_type}.txt")
    line_count = 0

    try:

        file.save(file_path)
        logger.info(f"File '{file.filename}' saved to {file_path} for session {session_id}")

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            if file_type == 'combo':
                valid_lines = [line for line in lines if line.strip() and ':' in line]
                if not valid_lines:
                    os.remove(file_path) 
                    return jsonify({'status': 'error', 'message': '❌ NO VALID COMBO! MUST BE AS [email:password].'}), 400
                line_count = len(valid_lines)
            elif file_type == 'proxy':
                valid_lines = [line for line in lines if line.strip()]
                if not valid_lines:
                    os.remove(file_path) 
                    return jsonify({'status': 'error', 'message': '❌ No valid proxy lines found! File is empty.'}), 400
                line_count = len(valid_lines)


        if file_type == 'combo':
            session_data['combo_file'] = file_path
            session_data['combo_line_count'] = line_count
        elif file_type == 'proxy':
            session_data['proxy_file'] = file_path
            session_data['proxy_line_count'] = line_count
            session_data['proxy_type'] = request.form.get('proxy_type', 'http') 

        save_session_data(session_id)

        socketio.emit(f'{file_type}_uploaded', {
            'session_id': session_id,
            'count': line_count,
            'message': f'✅ DONE! {line_count} valid lines found for {file_type}.',
            'file_type': file_type,
            'proxy_type': session_data.get('proxy_type') 
        }, room=session_id) 

        return jsonify({'status': 'success', 'message': f'{file_type.capitalize()} uploaded successfully.'}), 200

    except Exception as e:
        logger.error(f"Error processing {file_type} upload for session {session_id}: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': f'Error processing {file_type} file: {str(e)}'}), 500


@socketio.on('connect')
def handle_connect():
    
    logger.info(f"Client connected: {request.sid}. Waiting for session request/reconnect.")
    
    stats = get_initial_stats()
    
    emit('stats_update', stats, room=request.sid)

@socketio.on('request_session')
def handle_request_session():
    session_id, session_data = create_session()
    
    socketio.server.enter_room(request.sid, session_id)
    emit('session_created', {'session_id': session_id}, room=request.sid)
    logger.info(f"New session requested and created: {session_id} for socket {request.sid}")

@socketio.on('reconnect_session')
def handle_reconnect_session(data):
    client_session_id = data.get('session_id')
    if not client_session_id:
        logger.warning(f"Client {request.sid} attempted to reconnect without a session_id.")
        emit('error', {'message': 'No session ID provided for reconnection.'}, room=request.sid)
        session_id, session_data = create_session() 
        socketio.server.enter_room(request.sid, session_id) 
        emit('session_created', {'session_id': session_id}, room=request.sid)
        return

    session_id, session_data = create_session(existing_session_id=client_session_id)

    if session_id == client_session_id: 
        
        socketio.server.enter_room(request.sid, session_id)
        logger.info(f"Client {request.sid} reconnected to existing session: {session_id}")

        current_stats = get_current_stats(session_id)


        previous_state = {
            'stats': current_stats,
            'combo_file_uploaded': session_data.get('combo_file') is not None and os.path.exists(session_data.get('combo_file', '')), 
            'proxy_file_uploaded': session_data.get('proxy_file') is not None and os.path.exists(session_data.get('proxy_file', '')),
            'threads': session_data.get('threads', 10),
            'proxy_type': session_data.get('proxy_type', 'http'),
            'checker_status': 'paused' if session_data['is_paused'] else ('running' if session_data['is_running'] else 'stopped')
        }

        emit('session_reconnected', {'session_id': session_id, 'previous_state': previous_state}, room=request.sid)


        if session_data.get('is_running', False): 
            logger.info(f"Resuming status update thread for auto-paused session {session_id}")
            if not hasattr(socketio, 'status_threads'):
                socketio.status_threads = {}
            if session_id not in socketio.status_threads or not socketio.status_threads[session_id].is_alive():
                status_thread = threading.Thread(
                    target=update_status_websocket,
                    args=(session_id,)
                )
                status_thread.daemon = True
                status_thread.start()
                socketio.status_threads[session_id] = status_thread
            else:
                logger.info(f"Status update thread for {session_id} already running.")

    else: 
        logger.warning(f"Client {request.sid} provided invalid session ID {client_session_id}. Created new session: {session_id}")
        socketio.server.enter_room(request.sid, session_id) 
        emit('session_created', {'session_id': session_id}, room=request.sid)


@socketio.on('upload_combo')
def handle_combo_upload(data):
    session_id = data['session_id']
    combo_content = data['content']

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'}, room=request.sid) 
        return

    session_data = active_sessions[session_id]
    if session_data.get('is_running', False):
        emit('error', {'message': '❌ FAILED WHILE UPLOADING. Stop the checker first.'}, room=request.sid) 
        return

    session_dir = ensure_session_directory(session_id)
    combo_file = os.path.join(session_dir, "combo.txt")

    lines = combo_content.strip().split('\n')
    valid_lines = [line for line in lines if line.strip() and ':' in line]

    if not valid_lines:
        emit('error', {'message': '❌ NO VALID COMBO! MUST BE AS [email:password].'}, room=request.sid) 
        return

    try:
        with open(combo_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(valid_lines))

        session_data['combo_file'] = combo_file
        session_data['combo_line_count'] = len(valid_lines) 
        save_session_data(session_id) 
        emit('combo_uploaded', {'count': len(valid_lines), 'message': f'✅ DONE! {len(valid_lines)} valid lines found.', 'file_type': 'combo'}, room=session_id) 
        logger.info(f"Combo uploaded for session {session_id}: {len(valid_lines)} lines.")
    except Exception as e:
        emit('error', {'message': f'Error saving combo file: {str(e)}'}, room=request.sid) 
        logger.error(f"Error saving combo file for {session_id}: {e}")


@socketio.on('upload_proxy')
def handle_proxy_upload(data):
    session_id = data['session_id']
    proxy_content = data['content']
    proxy_type = data.get('proxy_type', 'http') 

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'}, room=request.sid) 
        return

    session_data = active_sessions[session_id]
    if session_data.get('is_running', False):
        emit('error', {'message': '❌ UPLOAD FAILED. Stop the checker first.'}, room=request.sid)
        return

    session_dir = ensure_session_directory(session_id)
    proxy_file = os.path.join(session_dir, "proxy.txt")

    lines = proxy_content.strip().split('\n')
    valid_lines = [line for line in lines if line.strip()]

    if not valid_lines:
        emit('error', {'message': '❌ No valid proxy lines found! File is empty.'}, room=request.sid) 
        return

    try:
        with open(proxy_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(valid_lines))

        session_data['proxy_file'] = proxy_file
        session_data['proxy_type'] = proxy_type 
        session_data['proxy_line_count'] = len(valid_lines) 
        save_session_data(session_id) 
        emit('proxy_uploaded', {'count': len(valid_lines), 'type': proxy_type, 'message': f'✅ DONE! {len(valid_lines)} valid lines found.', 'file_type': 'proxy', 'proxy_type': proxy_type}, room=session_id) 
        logger.info(f"Proxy uploaded for session {session_id}: {len(valid_lines)} lines, type {proxy_type}.")
    except Exception as e:
        emit('error', {'message': f'Error saving proxy file: {str(e)}'}, room=request.sid) 
        logger.error(f"Error saving proxy file for {session_id}: {e}")


@socketio.on('start_checker')
def handle_start_checker(data):
    session_id = data['session_id']
    threads = data.get('threads', 10)

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'}, room=request.sid)
        return

    session_data = active_sessions[session_id]

    if session_data.get('is_running', False):
        emit('error', {'message': '❌ Checker is already running. Please stop it first.'}, room=request.sid) 
        return

    combo_file = session_data.get('combo_file')
    if not combo_file or not os.path.exists(combo_file) or os.path.getsize(combo_file) == 0:
        emit('error', {'message': '❌ MISSING COMBO FILE! Please upload a combo file first.'}, room=request.sid)
        return

    proxy_file = session_data.get('proxy_file')
    if not proxy_file or not os.path.exists(proxy_file) or os.path.getsize(proxy_file) == 0:
        emit('error', {'message': '❌ MISSING PROXY FILE! Please upload a proxy file first.'}, room=request.sid)
        return

    try:
        with open(combo_file, 'r', encoding='utf-8', errors='ignore') as f:
            combo_content = f.read().strip()
            if not combo_content or not any(':' in line for line in combo_content.splitlines()):
                emit('error', {'message': '❌ Invalid combo file! File must contain lines in format email:password.'}, room=request.sid)
                return
    except Exception as e:
        emit('error', {'message': f'❌ Error reading combo file: {str(e)}'}, room=request.sid)
        return

    try:
        with open(proxy_file, 'r', encoding='utf-8', errors='ignore') as f:
            proxy_content = f.read().strip()
            if not proxy_content:
                emit('error', {'message': '❌ Invalid proxy file! File is empty.'}, room=request.sid)
                return
    except Exception as e:
        emit('error', {'message': f'❌ Error reading proxy file: {str(e)}'}, room=request.sid)
        return

    if not (1 <= threads <= 100):
        emit('error', {'message': '❌ Thread count must be between 1 and 100.'}, room=request.sid)
        return

    reset_hits_file(session_id)

    if session_id in chk.counters:
        del chk.counters[session_id] 

    session_data['is_running'] = True
    session_data['is_paused'] = False
    session_data['threads'] = threads
    save_session_data(session_id) 

    
    if not hasattr(socketio, 'checker_threads'):
        socketio.checker_threads = {}
    if session_id not in socketio.checker_threads or not socketio.checker_threads[session_id].is_alive():
        checker_thread = threading.Thread(
            target=start_checker_process,
            args=(session_id, combo_file, proxy_file, threads, session_data['proxy_type'])
        )
        checker_thread.daemon = True
        checker_thread.start()
        socketio.checker_threads[session_id] = checker_thread
    else:
        logger.warning(f"Checker thread for session {session_id} is already running or not properly cleaned up.")
        emit('error', {'message': '❌ Checker thread already active for this session.'}, room=request.sid)
        return


    emit('checker_started', {'message': '✅ Checker started successfully!'}, room=session_id) 
    logger.info(f"Checker started for session {session_id} with {threads} threads.")

@socketio.on('stop_checker')
def handle_stop_checker(data):
    session_id = data['session_id']

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'}, room=request.sid)
        return

    session_data = active_sessions[session_id]

    
    is_active_in_backend = session_data.get('is_running', False)
    is_active_in_chk = session_id in chk.counters and chk.counters[session_id]['is_running']

    if not (is_active_in_backend or is_active_in_chk):
        emit('error', {'message': '❌ No active checking process to stop.'}, room=request.sid)
        return

    if session_id in chk.counters:
        chk.counters[session_id]['is_running'] = False
        chk.counters[session_id]['completed'] = False
        chk.counters[session_id]['end_time'] = datetime.now()
        logger.info(f"Signaled chk.py to stop for session {session_id}.")

    session_data['is_running'] = False
    session_data['is_paused'] = False
    save_session_data(session_id) 

    
    time.sleep(1) 

    hits_file = os.path.join(ensure_session_directory(session_id), "hits.txt")
    if os.path.exists(hits_file) and os.path.getsize(hits_file) > 0:
        try:
            with open(hits_file, 'r', encoding='utf-8') as f:
                content = f.read()

            emit('hits_available', {
                'content': content,
                'filename': f'hits_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            }, room=session_id) 
        except Exception as e:
            logger.error(f"Error reading hits file on stop for {session_id}: {e}")
            emit('error', {'message': f'Error reading hits file: {str(e)}'}, room=request.sid)

    clean_session_directory(session_id) 

    emit('checker_stopped', {'message': '✅ CHECKER HAS BEEN STOPPED.'}, room=session_id) 
    logger.info(f"Checker stopped for session {session_id}.")


@socketio.on('pause_checker')
def handle_pause_checker(data):
    session_id = data['session_id']

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'}, room=request.sid)
        return

    session_data = active_sessions[session_id]

    
    is_running_in_chk = session_id in chk.counters and chk.counters[session_id]['is_running']
    is_running_in_session_data = session_data.get('is_running', False)

    if not (is_running_in_chk or is_running_in_session_data):
        emit('error', {'message': '❌ No active checker to pause. Start one first.'}, room=request.sid)
        return

    if session_data.get('is_paused', False):
        emit('error', {'message': '❌ Checker is already paused.'}, room=request.sid)
        return

    if is_running_in_chk:
        chk.counters[session_id]['is_paused'] = True
        logger.info(f"Checker paused in chk.counters for session {session_id}.")
    else:
        if session_data.get('combo_file') and session_data.get('proxy_file'):
            chk.counters[session_id] = {
                'checked': 0, 'invalid': 0, 'hits': 0, 'custom': 0,
                'total_mega_fan': 0, 'total_fan_member': 0, 'total_ultimate_mega': 0,
                'errors': 0, 'retries': 0,
                'is_running': True, 
                'is_paused': True,
                'completed': False,
                'start_time': datetime.fromisoformat(session_data['timestamp']),
                'end_time': None,
                'total_lines': session_data['combo_line_count']
            }
            logger.info(f"Re-initialized chk.counters for session {session_id} to paused state during pause request.")
        else:
            emit('error', {'message': '❌ Cannot pause: Checker state is ambiguous or files are missing.'}, room=request.sid)
            logger.warning(f"Attempted to pause session {session_id} but chk.counters missing and session_data incomplete.")
            return

    session_data['is_paused'] = True
    save_session_data(session_id) 

    emit('checker_paused', {'message': '⏸ PAUSED. Use Continue to resume.'}, room=session_id) 
    logger.info(f"Checker paused for session {session_id}.")


@socketio.on('continue_checker')
def handle_continue_checker(data):
    session_id = data['session_id']

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'}, room=request.sid)
        return

    session_data = active_sessions[session_id]

    
    is_running_in_chk = session_id in chk.counters and chk.counters[session_id]['is_running']
    is_paused_in_chk = session_id in chk.counters and chk.counters[session_id]['is_paused']
    is_running_in_session_data = session_data.get('is_running', False)
    is_paused_in_session_data = session_data.get('is_paused', False)

    if not (is_running_in_chk or is_running_in_session_data):
        emit('error', {'message': '❌ No active checker to continue. Start one first.'}, room=request.sid)
        return
    if not (is_paused_in_chk or is_paused_in_session_data):
        emit('error', {'message': '❌ Checker is not paused.'}, room=request.sid)
        return

    
    if is_running_in_chk and is_paused_in_chk:
        chk.counters[session_id]['is_paused'] = False
        logger.info(f"Checker continued in chk.counters for session {session_id}.")
    else:
        
        if session_data.get('combo_file') and session_data.get('proxy_file'):
            chk.counters[session_id] = {
                'checked': 0, 'invalid': 0, 'hits': 0, 'custom': 0,
                'total_mega_fan': 0, 'total_fan_member': 0, 'total_ultimate_mega': 0,
                'errors': 0, 'retries': 0,
                'is_running': True, 
                'is_paused': False,
                'completed': False,
                'start_time': datetime.fromisoformat(session_data['timestamp']),
                'end_time': None,
                'total_lines': session_data['combo_line_count']
            }
            logger.info(f"Re-initialized chk.counters for session {session_id} to running state during continue request.")
            if not hasattr(socketio, 'status_threads'):
                socketio.status_threads = {}
            if session_id not in socketio.status_threads or not socketio.status_threads[session_id].is_alive():
                status_thread = threading.Thread(
                    target=update_status_websocket,
                    args=(session_id,)
                )
                status_thread.daemon = True
                status_thread.start()
                socketio.status_threads[session_id] = status_thread
            else:
                logger.info(f"Status update thread for {session_id} already running.")
        else:
            emit('error', {'message': '❌ Cannot continue: Checker state is ambiguous or files are missing.'}, room=request.sid)
            logger.warning(f"Attempted to continue session {session_id} but chk.counters missing and session_data incomplete.")
            return

    session_data['is_paused'] = False
    save_session_data(session_id) 

    emit('checker_continued', {'message': '▶️ Checker has been resumed.'}, room=session_id) 
    logger.info(f"Checker continued for session {session_id}.")

@socketio.on('download_hits')
def handle_download_hits(data):
    session_id = data['session_id']

    if session_id not in active_sessions:
        emit('error', {'message': 'Invalid session'}, room=request.sid)
        return

    hits_file = os.path.join(ensure_session_directory(session_id), "hits.txt")

    if not os.path.exists(hits_file) or os.path.getsize(hits_file) == 0:
        emit('error', {'message': '❌ No hits found!'}, room=request.sid)
        return

    try:
        with open(hits_file, 'r', encoding='utf-8') as f:
            content = f.read()

        emit('hits_download', {
            'content': content,
            'filename': f'hits_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        }, room=session_id) 
        logger.info(f"Hits downloaded for session {session_id}.")
    except Exception as e:
        emit('error', {'message': f'Error reading hits file: {str(e)}'}, room=request.sid)
        logger.error(f"Error reading hits file for download {session_id}: {e}")

def get_initial_stats():
    return {
        'status': '❌ STOPPED',
        'total_lines': 0,
        'checked': 0,
        'invalid': 0,
        'hits': 0,
        'custom': 0,
        'total_mega_fan': 0,
        'total_fan_member': 0,
        'total_ultimate_mega': 0,
        'errors': 0,
        'retries': 0,
        'cpm': 0,
        'elapsed_time': '0:00:00'
    }

def get_current_stats(session_id):
    if session_id in chk.counters:
        return chk.generate_stats_text(session_id)
    else:
        session_data = active_sessions.get(session_id)
        if session_data:
            stats = get_initial_stats()
            stats['total_lines'] = session_data.get('combo_line_count', 0)
            
            if session_data.get('is_running', False):
                if session_data.get('is_paused', False):
                    stats['status'] = '⏸️ PAUSED'
                else:
                    stats['status'] = '🔄 RUNNING' 
            return stats
        return get_initial_stats() 

def start_checker_process(session_id, combo_file, proxy_file, threads, proxy_type):
    try:
        
        if not hasattr(socketio, 'status_threads'):
            socketio.status_threads = {}
        if session_id not in socketio.status_threads or not socketio.status_threads[session_id].is_alive():
            status_thread = threading.Thread(
                target=update_status_websocket,
                args=(session_id,)
            )
            status_thread.daemon = True
            status_thread.start()
            socketio.status_threads[session_id] = status_thread
        else:
            logger.info(f"Status update thread for {session_id} already running.")


        
        chk.start_checker(session_id, combo_file, proxy_file, threads, socketio, proxy_type)

    except Exception as e:
        socketio.emit('error', {'message': f'Checker error: {str(e)}'}, room=session_id) 
        logger.critical(f"Critical checker error for session {session_id}: {e}", exc_info=True)
    finally:
        if session_id in active_sessions:
            session_data = active_sessions[session_id]
            
            if not session_data['is_paused']:
                session_data['is_running'] = False
                session_data['is_paused'] = False
                save_session_data(session_id)
                logger.info(f"Checker process finished for session {session_id}. Marked as stopped.")
            else:
                logger.info(f"Checker process finished for session {session_id} but left paused.")
        
        if hasattr(socketio, 'checker_threads') and session_id in socketio.checker_threads:
            del socketio.checker_threads[session_id]
        
        if hasattr(socketio, 'status_threads') and session_id in socketio.status_threads:
            if not chk.counters.get(session_id, {}).get('is_running', False) and not chk.counters.get(session_id, {}).get('is_paused', False):
                del socketio.status_threads[session_id]


def update_status_websocket(session_id):
    logger.info(f"Starting status update thread for session {session_id}")
    while session_id in active_sessions and (active_sessions[session_id]['is_running'] or active_sessions[session_id]['is_paused']):
        if session_id not in chk.counters or not chk.counters[session_id]['is_running']:
            logger.info(f"Checker process for {session_id} is no longer running in chk.counters. Stopping status update.")
            if session_id in active_sessions:
                session_data = active_sessions[session_id]
                if not session_data['is_paused']: 
                    session_data['is_running'] = False
                    session_data['is_paused'] = False
                    save_session_data(session_id)
            break 

        if chk.counters[session_id]['is_paused']:
            time.sleep(1)
            continue

        stats = chk.generate_stats_text(session_id) 

        socketio.emit('stats_update', stats, room=session_id) 


        if chk.counters[session_id]['completed'] and not chk.counters[session_id]['is_running']: 
            logger.info(f"All lines checked for session {session_id}. Marking as completed.")
            
            chk.counters[session_id]['end_time'] = datetime.now()

            
            if session_id in active_sessions:
                session_data = active_sessions[session_id]
                session_data['is_running'] = False
                session_data['is_paused'] = False 
                save_session_data(session_id)

            
            hits_file = os.path.join(ensure_session_directory(session_id), "hits.txt")
            if os.path.exists(hits_file) and os.path.getsize(hits_file) > 0:
                try:
                    with open(hits_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    socketio.emit('hits_available', {
                        'content': content,
                        'filename': f'hits_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
                    }, room=session_id) 
                    logger.info(f"Hits available for completed session {session_id}.")
                except Exception as e:
                    logger.error(f"Error reading hits file for completed session {session_id}: {e}")
                    socketio.emit('error', {'message': f'Error reading hits file: {str(e)}'}, room=session_id)

            
            clean_session_directory(session_id)

            
            socketio.emit('checker_completed', {'message': '✅ COMPLETE!'}, room=session_id) 
            break 

        time.sleep(2) 

    logger.info(f"Status update thread for session {session_id} has stopped.")
    
    if hasattr(socketio, 'status_threads') and session_id in socketio.status_threads:
        
        if not chk.counters.get(session_id, {}).get('is_running', False) and not chk.counters.get(session_id, {}).get('is_paused', False):
            del socketio.status_threads[session_id]


if __name__ == '__main__':
    for item in os.listdir('.'):
        if item.startswith('session_') and os.path.isdir(item):
            session_id_from_dir = item.replace('session_', '')
            session_data_path = os.path.join(item, SESSION_DATA_FILE)
            if not os.path.exists(session_data_path):
                logger.warning(f"Removing incomplete session directory: {item}")
                try:
                    shutil.rmtree(item)
                except Exception as e:
                    logger.error(f"Error removing old session directory {item}: {e}")
            else:

                try:
                    with open(session_data_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('is_running', False):
                            data['is_running'] = True 
                            data['is_paused'] = True
                            active_sessions[session_id_from_dir] = data
                            save_session_data(session_id_from_dir) 
                            logger.info(f"Loaded and auto-paused session {session_id_from_dir} from disk.")


                            if session_id_from_dir not in chk.counters:
                                chk.counters[session_id_from_dir] = {
                                    'checked': 0, 'invalid': 0, 'hits': 0, 'custom': 0,
                                    'total_mega_fan': 0, 'total_fan_member': 0, 'total_ultimate_mega': 0,
                                    'errors': 0, 'retries': 0,
                                    'is_running': True, 
                                    'is_paused': True,
                                    'completed': False,
                                    'start_time': datetime.fromisoformat(data['timestamp']),
                                    'end_time': None,
                                    'total_lines': data['combo_line_count']
                                }
                                logger.info(f"Re-initialized chk.counters for auto-paused session {session_id_from_dir} on startup.")
                                if not hasattr(socketio, 'status_threads'):
                                    socketio.status_threads = {}
                                if session_id_from_dir not in socketio.status_threads or not socketio.status_threads[session_id_from_dir].is_alive():
                                    status_thread = threading.Thread(
                                        target=update_status_websocket,
                                        args=(session_id_from_dir,)
                                    )
                                    status_thread.daemon = True
                                    status_thread.start()
                                    socketio.status_threads[session_id_from_dir] = status_thread
                                else:
                                    logger.info(f"Status update thread for {session_id_from_dir} already running on startup.")

                        else:

                            active_sessions[session_id_from_dir] = data
                            logger.info(f"Loaded non-running session {session_id_from_dir} from disk.")
                except json.JSONDecodeError as e:
                    logger.error(f"Corrupt session_data.json in {item}: {e}. Consider manual cleanup.")
                except Exception as e:
                    logger.error(f"Error loading session {session_id_from_dir} on startup: {e}")
                    
                    if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=80)
