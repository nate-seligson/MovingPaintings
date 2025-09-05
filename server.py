from flask import Flask, send_file, render_template_string, request, jsonify
import requests
from screen import VideoWindow
import sys
import socket
import threading
from PyQt5.QtWidgets import QApplication

app = Flask(__name__)

# Global video window reference
window = None

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
    global window
    q_app = QApplication(sys.argv)
    window = VideoWindow()
    window.show()

    # Example of initial positioning
    window.set_video_position(200, 100)
    window.set_video_scale(0.5, 0.5)
    window.set_video_rotation(15)

    q_app.exec_()

@app.route('/control', methods=['POST'])
def control_video():
    """Handle video control commands"""
    global window
    
    if not window:
        return jsonify({"error": "Video window not initialized"}), 500
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        command_type = data.get('type')
        
        if command_type == 'position':
            x = data.get('x', 0)
            y = data.get('y', 0)
            window.set_video_position(x, y)
            return jsonify({"success": True, "message": f"Position set to ({x}, {y})"})
            
        elif command_type == 'scale':
            x = data.get('x', 1.0)
            y = data.get('y', 1.0)
            window.set_video_scale(x, y)
            return jsonify({"success": True, "message": f"Scale set to ({x}, {y})"})
            
        elif command_type == 'rotation':
            z = data.get('z', 0)  # Using z for rotation value as specified
            window.set_video_rotation(z)
            return jsonify({"success": True, "message": f"Rotation set to {z} degrees"})
            
        else:
            return jsonify({"error": f"Unknown command type: {command_type}"}), 400
            
    except Exception as e:
        return jsonify({"error": f"Error processing command: {str(e)}"}), 500


@app.route('/local')
def local_html():
    return send_file('example.html')  # Make sure example.html exists

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
    """

if __name__ == '__main__':
    # Start Qt application in a separate thread
    qt_thread = threading.Thread(target=setup_qt_app, daemon=True)
    qt_thread.start()
    
    # Wait a moment for Qt to initialize
    import time
    time.sleep(2)
    
    # Get local IP automatically
    host_ip = get_local_ip()
    port = 5000
    
    print(f"Starting Flask server on {host_ip}:{port}")
    print(f"Send control commands to: http://{host_ip}:{port}/control")
    
    app.run(host=host_ip, port=port, debug=False)  # debug=False to avoid issues with threading