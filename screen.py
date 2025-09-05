import sys
import uuid
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene
from PyQt5.QtCore import Qt, QSizeF, QUrl, QRectF, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QTransform, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem


class VideoItem:
    """Represents a single video with its properties and player"""
    def __init__(self, video_id, file_path, target_width=200, target_height=150):
        self.id = video_id
        self.file_path = file_path
        self.target_width = target_width  # Standard size in pixels
        self.target_height = target_height
        
        # Transform parameters
        self.x = 200  # Position (0-400 range for UI)
        self.y = 150  # Position (0-300 range for UI) 
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.rotation = 0
        
        # Qt objects
        self.video_item = QGraphicsVideoItem()
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.loop_timer = QTimer()
        
        # Set up the video item with target size
        self.video_item.setSize(QSizeF(self.target_width, self.target_height))
        self.media_player.setVideoOutput(self.video_item)
        
        # Set up looping
        self.setup_looping()
        
        # Load the video
        self.load_video()
    
    def setup_looping(self):
        """Set up seamless looping"""
        self.media_player.positionChanged.connect(self.check_near_end)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
    
    def check_near_end(self, position):
        """Check if we're near the end and prepare to loop"""
        duration = self.media_player.duration()
        if duration > 0 and position > duration - 100:  # 100ms before end
            # Seek back to beginning for seamless loop
            self.media_player.setPosition(0)
    
    def on_media_status_changed(self, status):
        """Handle media status changes"""
        if status == QMediaPlayer.EndOfMedia:
            # Backup loop mechanism
            self.media_player.setPosition(0)
            self.media_player.play()
    
    def load_video(self):
        """Load the video file"""
        try:
            media_content = QMediaContent(QUrl.fromLocalFile(self.file_path))
            self.media_player.setMedia(media_content)
            print(f"Loaded video {self.id}: {os.path.basename(self.file_path)}")
            return True
        except Exception as e:
            print(f"Error loading video {self.id}: {e}")
            return False
    
    def play(self):
        """Start playing the video"""
        self.media_player.play()
    
    def stop(self):
        """Stop the video"""
        self.media_player.stop()
    
    def cleanup(self):
        """Clean up resources"""
        self.stop()
        self.media_player.setMedia(QMediaContent())
        if self.video_item.scene():
            self.video_item.scene().removeItem(self.video_item)


class VideoController(QObject):
    """Qt object to handle video control signals safely in the Qt thread"""
    position_changed = pyqtSignal(str, float, float)  # video_id, x, y
    scale_changed = pyqtSignal(str, float, float)     # video_id, x, y
    rotation_changed = pyqtSignal(str, float)         # video_id, angle
    video_added = pyqtSignal(str, str, str)           # video_id, file_path, filename
    video_removed = pyqtSignal(str)                   # video_id
    
    def __init__(self, video_window):
        super().__init__()
        self.video_window = video_window
        # Connect signals to slots
        self.position_changed.connect(self.video_window.set_video_position)
        self.scale_changed.connect(self.video_window.set_video_scale)
        self.rotation_changed.connect(self.video_window.set_video_rotation)
        self.video_added.connect(self.video_window.add_video)
        self.video_removed.connect(self.video_window.remove_video)


class VideoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Dictionary to store all video items
        self.videos = {}  # video_id -> VideoItem
        
        # Screen dimensions
        self.screen_width = 0
        self.screen_height = 0
        
        # Standard video size (all videos will be scaled to this base size)
        self.standard_video_width = 200
        self.standard_video_height = 150
        
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Multi-Video Display')
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")

        # Get screen dimensions
        self.screen_width = self.width()
        self.screen_height = self.height()

        # Graphics view + scene
        self.graphics_view = QGraphicsView(self)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(self.graphics_view)

        # Set scene to match screen size
        self.graphics_scene = QGraphicsScene(0, 0, self.screen_width, self.screen_height)
        self.graphics_scene.setBackgroundBrush(QColor("black"))
        self.graphics_view.setScene(self.graphics_scene)

        # Fit the view to the scene
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.KeepAspectRatio)

    def add_video(self, video_id, file_path, filename):
        """Add a new video to the display"""
        try:
            # Create new video item
            video_item = VideoItem(
                video_id, 
                file_path, 
                self.standard_video_width, 
                self.standard_video_height
            )
            
            # Add to scene
            self.graphics_scene.addItem(video_item.video_item)
            
            # Store reference
            self.videos[video_id] = video_item
            
            # Apply initial transformations
            self.apply_transformations(video_id)
            
            # Start playing
            video_item.play()
            
            print(f"Added video {video_id}: {filename}")
            return True
            
        except Exception as e:
            print(f"Error adding video {video_id}: {e}")
            return False

    def remove_video(self, video_id):
        """Remove a video from the display"""
        try:
            if video_id in self.videos:
                video_item = self.videos[video_id]
                video_item.cleanup()
                del self.videos[video_id]
                print(f"Removed video {video_id}")
                return True
            return False
        except Exception as e:
            print(f"Error removing video {video_id}: {e}")
            return False

    def apply_transformations(self, video_id):
        """Apply position, scale, and rotation transformations to a specific video"""
        if video_id not in self.videos:
            return

        video_item = self.videos[video_id]
        
        # Make sure we have valid screen dimensions
        if self.screen_width == 0 or self.screen_height == 0:
            self.screen_width = self.width() if self.width() > 0 else 1920
            self.screen_height = self.height() if self.height() > 0 else 1080

        # Calculate actual pixel positions from normalized values (0-400 -> 0-screen_width)
        actual_x = (video_item.x / 400.0) * self.screen_width
        actual_y = (video_item.y / 300.0) * self.screen_height

        # Create transform
        transform = QTransform()
        
        # Calculate the center of the standardized video size (not original video size)
        video_center_x = self.standard_video_width * video_item.scale_x / 2
        video_center_y = self.standard_video_height * video_item.scale_y / 2
        
        # Move to position
        transform.translate(actual_x, actual_y)
        
        # Move to center for rotation and scaling
        transform.translate(video_center_x, video_center_y)
        
        # Apply rotation
        transform.rotate(video_item.rotation)
        
        # Apply scaling
        transform.scale(video_item.scale_x, video_item.scale_y)
        
        # Move back from center
        transform.translate(-video_center_x, -video_center_y)

        video_item.video_item.setTransform(transform)
        
        print(f"Applied transform to {video_id} - Pos: ({actual_x:.1f}, {actual_y:.1f}), "
              f"Scale: ({video_item.scale_x:.2f}, {video_item.scale_y:.2f}), "
              f"Rotation: {video_item.rotation}°")

    def set_video_position(self, video_id: str, x: float, y: float):
        """Set video position using HTML slider values (x: 0-400, y: 0-300)"""
        if video_id in self.videos:
            self.videos[video_id].x = float(x)
            self.videos[video_id].y = float(y)
            print(f"Setting position for {video_id}: x={x}, y={y}")
            self.apply_transformations(video_id)

    def set_video_scale(self, video_id: str, scale_x: float, scale_y: float):
        """Set video scale factors (0.1 to 2.0)"""
        if video_id in self.videos:
            self.videos[video_id].scale_x = float(scale_x)
            self.videos[video_id].scale_y = float(scale_y)
            print(f"Setting scale for {video_id}: x={scale_x}, y={scale_y}")
            self.apply_transformations(video_id)

    def set_video_rotation(self, video_id: str, angle: float):
        """Set video rotation in degrees (0-360)"""
        if video_id in self.videos:
            self.videos[video_id].rotation = float(angle)
            print(f"Setting rotation for {video_id}: {angle}°")
            self.apply_transformations(video_id)

    def get_screen_dimensions(self):
        """Return the current screen dimensions"""
        return self.screen_width, self.screen_height

    def get_videos_info(self):
        """Return information about all videos"""
        videos_info = []
        for video_id, video_item in self.videos.items():
            videos_info.append({
                'id': video_id,
                'file_path': video_item.file_path,
                'filename': os.path.basename(video_item.file_path),
                'x': video_item.x,
                'y': video_item.y,
                'scale_x': video_item.scale_x,
                'scale_y': video_item.scale_y,
                'rotation': video_item.rotation
            })
        return videos_info

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        
        # Check if UI components are initialized before proceeding
        if not hasattr(self, 'graphics_scene') or self.graphics_scene is None:
            return
            
        if not hasattr(self, 'graphics_view') or self.graphics_view is None:
            return
        
        # Update screen dimensions
        self.screen_width = self.width()
        self.screen_height = self.height()
        
        # Update scene size
        self.graphics_scene.setSceneRect(0, 0, self.screen_width, self.screen_height)
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.KeepAspectRatio)
        
        # Reapply transformations for all videos with new screen size
        for video_id in self.videos:
            self.apply_transformations(video_id)


# Test the video window independently
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoWindow()
    window.show()
    
    # Test adding multiple videos after a delay
    from PyQt5.QtCore import QTimer
    
    def test_multiple_videos():
        print("Testing multiple videos...")
        # Add first video
        video1_path = "/home/pil/Downloads/MovingPaintings/65562-515098354_medium.mp4"
        if os.path.exists(video1_path):
            window.add_video("video1", video1_path, "video1.mp4")
            window.set_video_position("video1", 100, 100)
            window.set_video_scale("video1", 0.8, 0.8)
        
        # Add second video
        # window.add_video("video2", "path/to/video2.mp4", "video2.mp4")
        # window.set_video_position("video2", 300, 200)
        # window.set_video_rotation("video2", 45)
    
    QTimer.singleShot(2000, test_multiple_videos)  # Test after 2 seconds
    
    sys.exit(app.exec_())