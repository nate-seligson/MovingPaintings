from flask import Flask, send_file, render_template_string, request, jsonify, send_from_directory
import requests
from screen import VideoWindow  # Make sure this imports your fixed VideoWindow
import sys
import socket
import threading
import time
import os
from werkzeug.utils import secure_filename
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMetaObject, Qt, QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt5.QtMultimedia import QMediaContent

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploaded_videos'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'ogv', 'm4v'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global video window reference
window = None
qt_app = None
current_video_path = None

class VideoController(QObject):
    """Qt object to handle video control signals safely in the Qt thread"""
    position_changed = pyqtSignal(float, float)
    scale_changed = pyqtSignal(float, float)
    rotation_changed = pyqtSignal(float)
    video_changed = pyqtSignal(str)
    
    def __init__(self, video_window):
        super().__init__()
        self.video_window = video_window
        # Connect signals to slots
        self.position_changed.connect(self.set_position)
        self.scale_changed.connect(self.set_scale)
        self.rotation_changed.connect(self.set_rotation)
        self.video_changed.connect(self.change_video)
    
    @pyqtSlot(float, float)
    def set_position(self, x, y):
        if self.video_window:
            self.video_window.set_video_position(x, y)
    
    @pyqtSlot(float, float)
    def set_scale(self, x, y):
        if self.video_window:
            self.video_window.set_video_scale(x, y)
    
    @pyqtSlot(float)
    def set_rotation(self, angle):
        if self.video_window:
            self.video_window.set_video_rotation(angle)
    
    @pyqtSlot(str)
    def change_video(self, file_path):
        if self.video_window:
            try:
                # Clear the current playlist and add the new video
                self.video_window.playlist.clear()
                self.video_window.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
                self.video_window.playlist.setCurrentIndex(0)
                self.video_window.media_player.play()
                print(f"Video changed to: {file_path}")
            except Exception as e:
                print(f"Error changing video: {e}")

# Global controller
video_controller = None

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "127.0.0.1"  # Fallback to localhost

def get_screen_dimensions():
    """Get the screen dimensions from the Qt window"""
    global window
    if window:
        # Get the actual screen dimensions
        screen = window.screen()
        if screen:
            geometry = screen.geometry()
            return geometry.width(), geometry.height()
    # Default fallback
    return 1920, 1080

def setup_qt_app():
    """Setup Qt application and video window in a separate thread"""
    global window, qt_app, video_controller
    
    try:
        qt_app = QApplication(sys.argv)
        window = VideoWindow()
        
        # Create controller for thread-safe communication
        video_controller = VideoController(window)
        
        window.show()
        print("Qt application started successfully")
        
        # Get screen dimensions
        width, height = get_screen_dimensions()
        print(f"Screen dimensions: {width}x{height}")
        
        # Example of initial positioning
        window.set_video_position(200, 150)
        window.set_video_scale(1.0, 1.0)
        window.set_video_rotation(0)
        
        qt_app.exec_()
        
    except Exception as e:
        print(f"Error in Qt setup: {e}")
        import traceback
        traceback.print_exc()

@app.route('/screen-dimensions')
def screen_dimensions():
    """Return the screen dimensions"""
    width, height = get_screen_dimensions()
    return jsonify({
        "width": width,
        "height": height,
        "aspect_ratio": width / height if height > 0 else 1.77
    })

@app.route('/upload-video', methods=['POST'])
def upload_video():
    """Handle video upload"""
    global current_video_path, video_controller
    
    # Check if video_controller is initialized
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    
    # Check if the post request has the file part
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    file = request.files['video']
    
    # If user does not select file, browser may submit empty part without filename
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Secure the filename
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = str(int(time.time()))
            filename = f"{timestamp}_{filename}"
            
            # Save the file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get absolute path
            absolute_path = os.path.abspath(filepath)
            current_video_path = absolute_path
            
            # Change the video in the Qt window
            video_controller.video_changed.emit(absolute_path)
            
            # Generate preview URL (you might want to extract a frame here)
            preview_url = f"/video-preview/{filename}"
            
            return jsonify({
                "success": True,
                "message": f"Video uploaded successfully: {filename}",
                "filename": filename,
                "filepath": filepath,
                "preview_url": preview_url
            })
            
        except Exception as e:
            print(f"Error uploading video: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to upload video: {str(e)}"}), 500
    
    return jsonify({"error": f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

@app.route('/video-preview/<filename>')
def video_preview(filename):
    """Serve uploaded video files for preview"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype='video/mp4')
    except FileNotFoundError:
        return jsonify({"error": "Video file not found"}), 404

@app.route('/control', methods=['POST'])
def control_video():
    """Handle video control commands"""
    global video_controller
    
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        command_type = data.get('type')
        
        if command_type == 'position':
            x = float(data.get('x', 0))
            y = float(data.get('y', 0))
            # Use Qt signal to safely call from another thread
            video_controller.position_changed.emit(x, y)
            return jsonify({"success": True, "message": f"Position set to ({x}, {y})"})
            
        elif command_type == 'scale':
            x = float(data.get('x', 1.0))
            y = float(data.get('y', 1.0))
            video_controller.scale_changed.emit(x, y)
            return jsonify({"success": True, "message": f"Scale set to ({x}, {y})"})
            
        elif command_type == 'rotation':
            z = float(data.get('z', 0))
            video_controller.rotation_changed.emit(z)
            return jsonify({"success": True, "message": f"Rotation set to {z} degrees"})
            
        else:
            return jsonify({"error": f"Unknown command type: {command_type}"}), 400
            
    except Exception as e:
        print(f"Error in control_video: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error processing command: {str(e)}"}), 500

# Option 1: Serve a local HTML file
@app.route('/local')
def local_html():
    try:
        return send_file('example.html')  # Make sure to save the HTML as example.html
    except FileNotFoundError:
        return jsonify({"error": "example.html file not found"}), 404

# Option 2: Serve an external HTML file via URL
@app.route('/external')
def external_html():
    try:
        url = 'https://example.com/index.html'  # Replace with your external URL
        response = requests.get(url)
        return render_template_string(response.text)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch external HTML: {str(e)}"}), 500

@app.route('/')
def home():
    """Basic home route with usage information"""
    return """
    <h1>Video Control Server</h1>
    <p>Features:</p>
    <ul>
        <li>Control video position, scale, and rotation</li>
        <li>Upload custom videos</li>
        <li>Adaptive preview based on screen aspect ratio</li>
        <li>Precise numeric input controls</li>
    </ul>
    <p>Send POST requests to /control with JSON data:</p>
    <pre>
    Position: {"type": "position", "x": 100, "y": 50}
    Scale: {"type": "scale", "x": 0.8, "y": 0.8}
    Rotation: {"type": "rotation", "z": 45}
    </pre>
    <p><a href="/local">Open Control Interface</a></p>
    """

@app.route('/status')
def status():
    """Check server status"""
    global window, video_controller, current_video_path
    width, height = get_screen_dimensions()
    return jsonify({
        "qt_app_running": qt_app is not None,
        "video_window_created": window is not None,
        "video_controller_ready": video_controller is not None,
        "window_visible": window.isVisible() if window else False,
        "screen_dimensions": {"width": width, "height": height},
        "current_video": current_video_path,
        "upload_folder": os.path.abspath(app.config['UPLOAD_FOLDER'])
    })

if __name__ == '__main__':
    print("Starting Video Control Server...")
    
    # Start Qt application in a separate daemon thread
    qt_thread = threading.Thread(target=setup_qt_app, daemon=True)
    qt_thread.start()
    
    # Wait for Qt to initialize
    print("Waiting for Qt application to initialize...")
    max_wait = 10  # Wait up to 10 seconds
    wait_count = 0
    
    while video_controller is None and wait_count < max_wait:
        time.sleep(1)
        wait_count += 1
        print(f"Waiting... {wait_count}/{max_wait}")
    
    if video_controller is None:
        print("WARNING: Qt application may not have initialized properly")
    else:
        print("Qt application initialized successfully")
    
    # Get local IP automatically
    host_ip = get_local_ip()
    port = 5000
    
    print(f"Starting Flask server on {host_ip}:{port}")
    print(f"Control interface: http://{host_ip}:{port}/local")
    print(f"Send control commands to: http://{host_ip}:{port}/control")
    print(f"Upload videos to: http://{host_ip}:{port}/upload-video")
    print(f"Check status at: http://{host_ip}:{port}/status")
    
    try:
        app.run(host=host_ip, port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()