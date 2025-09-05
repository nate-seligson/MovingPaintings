from flask import Flask, send_file, render_template_string, request, jsonify
import requests
from screen import VideoWindow  # Make sure this imports your fixed VideoWindow
import sys
import socket
import threading
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMetaObject, Qt, QObject, pyqtSignal, pyqtSlot

app = Flask(__name__)

# Global video window reference
window = None
qt_app = None

class VideoController(QObject):
    """Qt object to handle video control signals safely in the Qt thread"""
    position_changed = pyqtSignal(float, float)
    scale_changed = pyqtSignal(float, float)
    rotation_changed = pyqtSignal(float)
    
    def __init__(self, video_window):
        super().__init__()
        self.video_window = video_window
        # Connect signals to slots
        self.position_changed.connect(self.set_position)
        self.scale_changed.connect(self.set_scale)
        self.rotation_changed.connect(self.set_rotation)
    
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

# Global controller
video_controller = None

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
        
        # Example of initial positioning
        window.set_video_position(0, 0)
        window.set_video_scale(1.0, 1.0)
        window.set_video_rotation(0)
        
        qt_app.exec_()
        
    except Exception as e:
        print(f"Error in Qt setup: {e}")
        import traceback
        traceback.print_exc()

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
        return send_file('example.html')  # Make sure example.html exists
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
    global window, video_controller
    return jsonify({
        "qt_app_running": qt_app is not None,
        "video_window_created": window is not None,
        "video_controller_ready": video_controller is not None,
        "window_visible": window.isVisible() if window else False
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
    print(f"Check status at: http://{host_ip}:{port}/status")
    
    try:
        app.run(host=host_ip, port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()