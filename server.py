from flask import Flask, send_file, render_template_string, request, jsonify, send_from_directory
import requests
from screen import VideoWindow, VideoController  # Import the updated VideoWindow
import sys
import threading
import time
import os
import uuid
from werkzeug.utils import secure_filename
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QMetaObject, Qt, QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt5.QtMultimedia import QMediaContent
# Additional Raspberry Pi optimization settings
# Add these at the top of your server.py file

import os
import sys

def optimize_for_raspberry_pi():
    """Apply Raspberry Pi specific optimizations"""
    
    # Set environment variables for better performance
    os.environ['QT_QUICK_BACKEND'] = 'software'  # Use software rendering
    os.environ['QT_GRAPHICSSYSTEM'] = 'raster'   # Use raster graphics system
    os.environ['QT_XCB_GL_INTEGRATION'] = 'none' # Disable OpenGL integration
    
    # Disable Qt debug output for better performance
    os.environ['QT_LOGGING_RULES'] = '*.debug=false'
    
    # Set video decoder preferences (hardware acceleration if available)
    os.environ['QT_GSTREAMER_USE_PLAYBIN_VOLUME'] = '1'
    
    # Memory management
    os.environ['QT_QPA_PLATFORM'] = 'xcb'  # Use X11 backend
    
    print("Applied Raspberry Pi optimizations")

def configure_video_settings():
    """Configure optimal video settings for Raspberry Pi"""
    return {
        'max_videos': 4,  # Limit concurrent videos
        'video_resolution': (640, 480),  # Lower resolution for better performance
        'frame_rate': 30,  # Cap frame rate
        'buffer_size': 5,  # Smaller buffer
        'threads': 2,  # Limit thread count
    }

# System optimization commands to run on Raspberry Pi:
"""
# Add these to /boot/config.txt for better video performance:
gpu_mem=128          # Allocate more RAM to GPU
disable_overscan=1   # Disable overscan
hdmi_force_hotplug=1 # Force HDMI output
hdmi_group=1         # HDMI group
hdmi_mode=16         # 1080p 60Hz
max_usb_current=1    # Enable higher USB current

# Add these to /etc/rc.local for CPU optimization:
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Install hardware acceleration packages:
sudo apt-get install libgl1-mesa-dri
sudo apt-get install va-driver-all
sudo apt-get install gstreamer1.0-vaapi

# For better video codec support:
sudo apt-get install gstreamer1.0-plugins-bad
sudo apt-get install gstreamer1.0-plugins-ugly
sudo apt-get install gstreamer1.0-libav
"""

# Modified server.py startup section:
if __name__ == '__main__':
    # Apply Raspberry Pi optimizations before starting Qt
    optimize_for_raspberry_pi()
    
    # Rest of your server startup code...
    import socket
    print("Starting Optimized Multi-Video Control Server for Raspberry Pi...")
    
    # ... rest of your existing server code
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
video_controller = None

# Store video information server-side
videos_db = {}  # video_id -> video_info

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    global video_controller
    
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
            
            # Generate preview URL
            preview_url = f"/video-preview/{filename}"
            
            return jsonify({
                "success": True,
                "message": f"Video uploaded successfully: {filename}",
                "filename": filename,
                "filepath": absolute_path,
                "preview_url": preview_url
            })
            
        except Exception as e:
            print(f"Error uploading video: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": f"Failed to upload video: {str(e)}"}), 500
    
    return jsonify({"error": f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

@app.route('/add-video', methods=['POST'])
def add_video():
    """Add a video to the display"""
    global video_controller, videos_db
    
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    
    try:
        data = request.get_json()
        filepath = data.get('filepath')
        filename = data.get('filename')
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({"error": "Video file not found"}), 400
        
        # Generate unique video ID
        video_id = str(uuid.uuid4())
        
        # Add to Qt window
        video_controller.video_added.emit(video_id, filepath, filename)
        
        # Store in database
        preview_filename = os.path.basename(filepath)
        videos_db[video_id] = {
            'id': video_id,
            'name': filename,
            'filepath': filepath,
            'preview_url': f"/video-preview/{preview_filename}",
            'x': 200,
            'y': 150,
            'scale_x': 1.0,
            'scale_y': 1.0,
            'rotation': 0
        }
        
        return jsonify({
            "success": True,
            "video_id": video_id,
            "message": f"Video added successfully: {filename}"
        })
        
    except Exception as e:
        print(f"Error adding video: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to add video: {str(e)}"}), 500

@app.route('/remove-video', methods=['POST'])
def remove_video():
    """Remove a video from the display"""
    global video_controller, videos_db
    
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        
        if not video_id or video_id not in videos_db:
            return jsonify({"error": "Video not found"}), 400
        
        # Remove from Qt window
        video_controller.video_removed.emit(video_id)
        
        # Remove from database
        video_name = videos_db[video_id]['name']
        del videos_db[video_id]
        
        return jsonify({
            "success": True,
            "message": f"Video removed successfully: {video_name}"
        })
        
    except Exception as e:
        print(f"Error removing video: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to remove video: {str(e)}"}), 500

@app.route('/swap-video', methods=['POST'])
def swap_video():
    """Swap the video file for an existing video while keeping its position"""
    global video_controller, videos_db
    
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    
    try:
        data = request.get_json()
        video_id = data.get('video_id')
        new_filepath = data.get('filepath')
        new_filename = data.get('filename')
        
        if not video_id or video_id not in videos_db:
            return jsonify({"error": "Video not found"}), 400
        
        if not new_filepath or not os.path.exists(new_filepath):
            return jsonify({"error": "New video file not found"}), 400
        
        # Get the old file path to delete it later
        old_filepath = videos_db[video_id]['filepath']
        
        # Swap video in Qt window
        video_controller.video_swapped.emit(video_id, new_filepath)
        
        # Update database with new file info (keep position/scale/rotation)
        old_name = videos_db[video_id]['name']
        videos_db[video_id]['filepath'] = new_filepath
        videos_db[video_id]['name'] = new_filename
        
        # Update preview URL
        preview_filename = os.path.basename(new_filepath)
        videos_db[video_id]['preview_url'] = f"/video-preview/{preview_filename}"
        
        # Delete the old video file
        try:
            if os.path.exists(old_filepath) and old_filepath != new_filepath:
                os.remove(old_filepath)
                print(f"Deleted old video file: {old_filepath}")
        except Exception as e:
            print(f"Warning: Could not delete old video file {old_filepath}: {e}")
        
        print(f"Swapped video {video_id} from '{old_name}' to '{new_filename}'")
        
        return jsonify({
            "success": True,
            "message": f"Video swapped successfully to: {new_filename}"
        })
        
    except Exception as e:
        print(f"Error swapping video: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to swap video: {str(e)}"}), 500

@app.route('/get-videos')
def get_videos():
    """Get list of all videos"""
    try:
        # Get current state from Qt window if available
        if window:
            qt_videos_info = window.get_videos_info()
            # Update our database with current positions/scales
            for video_info in qt_videos_info:
                video_id = video_info['id']
                if video_id in videos_db:
                    videos_db[video_id].update({
                        'x': video_info['x'],
                        'y': video_info['y'],
                        'scale_x': video_info['scale_x'],
                        'scale_y': video_info['scale_y'],
                        'rotation': video_info['rotation']
                    })
        
        return jsonify({
            "success": True,
            "videos": list(videos_db.values())
        })
        
    except Exception as e:
        print(f"Error getting videos: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "videos": []
        })

@app.route('/video-preview/<filename>')
def video_preview(filename):
    """Serve uploaded video files for preview"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, mimetype='video/mp4')
    except FileNotFoundError:
        return jsonify({"error": "Video file not found"}), 404

@app.route('/control-video', methods=['POST'])
def control_video():
    """Handle video control commands for specific videos"""
    global video_controller, videos_db
    
    if not video_controller:
        return jsonify({"error": "Video window not initialized"}), 500
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
        
        video_id = data.get('video_id')
        command_type = data.get('type')
        
        if not video_id or video_id not in videos_db:
            return jsonify({"error": "Video not found"}), 400
        
        if command_type == 'position':
            x = float(data.get('x', 0))
            y = float(data.get('y', 0))
            # Use Qt signal to safely call from another thread
            video_controller.position_changed.emit(video_id, x, y)
            # Update database
            videos_db[video_id]['x'] = x
            videos_db[video_id]['y'] = y
            return jsonify({"success": True, "message": f"Position set to ({x}, {y}) for video {video_id}"})
            
        elif command_type == 'scale':
            x = float(data.get('x', 1.0))
            y = float(data.get('y', 1.0))
            video_controller.scale_changed.emit(video_id, x, y)
            # Update database
            videos_db[video_id]['scale_x'] = x
            videos_db[video_id]['scale_y'] = y
            return jsonify({"success": True, "message": f"Scale set to ({x}, {y}) for video {video_id}"})
            
        elif command_type == 'rotation':
            z = float(data.get('z', 0))
            video_controller.rotation_changed.emit(video_id, z)
            # Update database
            videos_db[video_id]['rotation'] = z
            return jsonify({"success": True, "message": f"Rotation set to {z} degrees for video {video_id}"})
            
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
        return send_file('multi_video_interface.html')  # Update to match your HTML filename
    except FileNotFoundError:
        return jsonify({"error": "multi_video_interface.html file not found. Make sure the HTML file is in the same directory as this Flask app."}), 404

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
    <h1>Multi-Video Control Server</h1>
    <p>Features:</p>
    <ul>
        <li>Add multiple videos to one screen</li>
        <li>Control each video individually (position, scale, rotation)</li>
        <li>Upload custom videos</li>
        <li>Swap videos while maintaining position/scale/rotation</li>
        <li>Remove videos from display</li>
        <li>Consistent video sizing regardless of aspect ratio</li>
        <li>Enhanced seamless video looping with multiple fallback mechanisms</li>
    </ul>
    <p>API Endpoints:</p>
    <ul>
        <li>POST /control-video - Control video position/scale/rotation</li>
        <li>POST /upload-video - Upload new video files</li>
        <li>POST /add-video - Add uploaded video to display</li>
        <li>POST /swap-video - Swap video file while keeping position</li>
        <li>POST /remove-video - Remove video from display</li>
        <li>GET /get-videos - Get list of all videos</li>
        <li>GET /screen-dimensions - Get display screen dimensions</li>
    </ul>
    <p>Control JSON format:</p>
    <pre>
    Position: {"video_id": "uuid", "type": "position", "x": 100, "y": 50}
    Scale: {"video_id": "uuid", "type": "scale", "x": 0.8, "y": 0.8}
    Rotation: {"video_id": "uuid", "type": "rotation", "z": 45}
    </pre>
    <p><a href="/local">Open Multi-Video Control Interface</a></p>
    """

@app.route('/status')
def status():
    """Check server status"""
    global window, video_controller, videos_db
    width, height = get_screen_dimensions()
    return jsonify({
        "qt_app_running": qt_app is not None,
        "video_window_created": window is not None,
        "video_controller_ready": video_controller is not None,
        "window_visible": window.isVisible() if window else False,
        "screen_dimensions": {"width": width, "height": height},
        "videos_count": len(videos_db),
        "videos": list(videos_db.keys()),
        "upload_folder": os.path.abspath(app.config['UPLOAD_FOLDER']),
        "allowed_extensions": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024)
    })

if __name__ == '__main__':
    import socket

    print("Starting Multi-Video Control Server...")

    # Detect LAN IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception as e:
        print(f"Could not detect LAN IP, defaulting to 127.0.0.1: {e}")
        local_ip = "127.0.0.1"

    port = 6969

    # Start Flask in a separate daemon thread
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, threaded=True),
        daemon=True
    )
    flask_thread.start()
    print(f"Flask server started on LAN: http://{local_ip}:{port}/local")

    # Run Qt in the main thread
    setup_qt_app()