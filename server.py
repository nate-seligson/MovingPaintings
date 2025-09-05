from flask import Flask, send_file, render_template_string, request, jsonify, send_from_directory
import socket
from screen import VideoWindow, VideoController
import sys
import threading
import time
import os
import uuid
from werkzeug.utils import secure_filename
from PyQt5.QtWidgets import QApplication

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploaded_videos'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'ogv', 'm4v'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global references
window = None
qt_app = None
video_controller = None
videos_db = {}  # video_id -> video_info

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_screen_dimensions():
    if window:
        screen = window.screen()
        if screen:
            geo = screen.geometry()
            return geo.width(), geo.height()
    return 1920, 1080

def setup_qt_app():
    global window, qt_app, video_controller
    try:
        qt_app = QApplication(sys.argv)
        window = VideoWindow()
        video_controller = VideoController(window)
        window.show()
        qt_app.exec_()
    except Exception as e:
        print(f"Error in Qt setup: {e}")

# ----------------------- Flask Routes -----------------------

@app.route('/screen-dimensions')
def screen_dimensions():
    w, h = get_screen_dimensions()
    return jsonify({"width": w, "height": h, "aspect_ratio": w/h if h else 1.77})

@app.route('/upload-video', methods=['POST'])
def upload_video():
    global video_controller
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = f"{int(time.time())}_{secure_filename(file.filename)}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({
            "success": True,
            "filename": filename,
            "filepath": os.path.abspath(filepath),
            "preview_url": f"/video-preview/{filename}"
        })
    return jsonify({"error": f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

@app.route('/add-video', methods=['POST'])
def add_video():
    global video_controller, videos_db
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    data = request.get_json()
    filepath = data.get('filepath')
    filename = data.get('filename')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "Video file not found"}), 400
    video_id = str(uuid.uuid4())
    video_controller.video_added.emit(video_id, filepath, filename)
    videos_db[video_id] = {
        'id': video_id, 'name': filename, 'filepath': filepath,
        'preview_url': f"/video-preview/{os.path.basename(filepath)}",
        'x': 200, 'y': 150, 'scale_x': 1.0, 'scale_y': 1.0, 'rotation': 0
    }
    return jsonify({"success": True, "video_id": video_id})

@app.route('/remove-video', methods=['POST'])
def remove_video():
    global video_controller, videos_db
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    data = request.get_json()
    video_id = data.get('video_id')
    if not video_id or video_id not in videos_db:
        return jsonify({"error": "Video not found"}), 400
    video_controller.video_removed.emit(video_id)
    del videos_db[video_id]
    return jsonify({"success": True})

@app.route('/swap-video', methods=['POST'])
def swap_video():
    global video_controller, videos_db
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    data = request.get_json()
    video_id = data.get('video_id')
    new_filepath = data.get('filepath')
    new_filename = data.get('filename')
    if not video_id or video_id not in videos_db:
        return jsonify({"error": "Video not found"}), 400
    if not new_filepath or not os.path.exists(new_filepath):
        return jsonify({"error": "New video file not found"}), 400
    old_filepath = videos_db[video_id]['filepath']
    video_controller.video_swapped.emit(video_id, new_filepath)
    videos_db[video_id]['filepath'] = new_filepath
    videos_db[video_id]['name'] = new_filename
    videos_db[video_id]['preview_url'] = f"/video-preview/{os.path.basename(new_filepath)}"
    if os.path.exists(old_filepath) and old_filepath != new_filepath:
        try: os.remove(old_filepath)
        except: pass
    return jsonify({"success": True})

@app.route('/get-videos')
def get_videos():
    return jsonify({"success": True, "videos": list(videos_db.values())})

@app.route('/video-preview/<filename>')
def video_preview(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype='video/mp4')

@app.route('/control-video', methods=['POST'])
def control_video():
    global video_controller, videos_db
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    data = request.get_json()
    video_id = data.get('video_id')
    cmd_type = data.get('type')
    if not video_id or video_id not in videos_db:
        return jsonify({"error": "Video not found"}), 400
    if cmd_type == 'position':
        x, y = float(data.get('x', 0)), float(data.get('y', 0))
        video_controller.position_changed.emit(video_id, x, y)
        videos_db[video_id]['x'], videos_db[video_id]['y'] = x, y
    elif cmd_type == 'scale':
        sx, sy = float(data.get('x', 1.0)), float(data.get('y', 1.0))
        video_controller.scale_changed.emit(video_id, sx, sy)
        videos_db[video_id]['scale_x'], videos_db[video_id]['scale_y'] = sx, sy
    elif cmd_type == 'rotation':
        rz = float(data.get('z', 0))
        video_controller.rotation_changed.emit(video_id, rz)
        videos_db[video_id]['rotation'] = rz
    else:
        return jsonify({"error": f"Unknown command type: {cmd_type}"}), 400
    return jsonify({"success": True})

@app.route('/local')
def local_html():
    try:
        return send_file('multi_video_interface.html')
    except FileNotFoundError:
        return jsonify({"error": "multi_video_interface.html not found"}), 404

@app.route('/')
def home():
    return "<h1>Multi-Video Control Server</h1><p>Open /local to control videos.</p>"

@app.route('/status')
def status():
    return jsonify({
        "qt_app_running": qt_app is not None,
        "video_window_created": window is not None,
        "video_controller_ready": video_controller is not None,
        "window_visible": window.isVisible() if window else False,
        "videos_count": len(videos_db)
    })

def get_lan_ip():
    """
    Detects LAN IP address of the machine.
    Falls back to 127.0.0.1 if not found.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to connect; dummy IP
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"
# ----------------------- Main -----------------------
if __name__ == '__main__':
    print("Starting Multi-Video Control Server...")

    qt_thread = threading.Thread(target=setup_qt_app, daemon=True)
    qt_thread.start()

    # Wait for Qt
    print("Waiting for Qt app to initialize...")
    max_wait = 10
    for i in range(max_wait):
        if video_controller: break
        time.sleep(1)
        print(f"Waiting... {i+1}/{max_wait}")

    port = 5000
    lan_ip = get_lan_ip()  # Detect LAN IP automatically
    print(f"\nFlask server running on all LAN interfaces, port {port}")
    print(f"Access the control interface via: http://{lan_ip}:{port}/local")
    print(f"Check server status via: http://{lan_ip}:{port}/status")

    try:
        # Bind to all interfaces so LAN devices can connect
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("Shutting down server...")
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()