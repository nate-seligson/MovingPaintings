import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene
from PyQt5.QtCore import Qt, QSizeF, QUrl, QRectF
from PyQt5.QtGui import QTransform, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem


class VideoWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Default video file - will be overridden if a new video is loaded
        self.video_file = "/home/pil/Downloads/MovingPaintings/65562-515098354_medium.mp4"
        self.current_video_file = self.video_file  # Keep track of current video

        # Transform parameters - these will be set by the HTML interface
        self.video_x = 0  # horizontal position offset (0-1 normalized)
        self.video_y = 0  # vertical position offset (0-1 normalized)
        self.video_rotation = 0  # rotation in degrees
        self.scale_x = 1.0  # horizontal scale factor
        self.scale_y = 1.0  # vertical scale factor

        # Screen dimensions for normalization
        self.screen_width = 0
        self.screen_height = 0
        self.video_width = 0
        self.video_height = 0

        # Initialize attributes
        self.video_item = None
        self.media_player = None
        self.playlist = None  # Make playlist accessible

        self.initUI()

    def initUI(self):
        self.setWindowTitle('')
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

        # Video item
        self.video_item = QGraphicsVideoItem()
        self.graphics_scene.addItem(self.video_item)

        # Media player + playlist
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.playlist = QMediaPlaylist()
        self.playlist.setPlaybackMode(QMediaPlaylist.Loop)
        self.media_player.setPlaylist(self.playlist)
        
        # Load initial video
        self.load_video(self.video_file)

        self.media_player.setVideoOutput(self.video_item)

        # Connect signals
        self.media_player.metaDataChanged.connect(self.on_metadata_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.error.connect(self.on_media_error)
        self.media_player.play()

    def load_video(self, file_path):
        """Load a video file into the playlist"""
        try:
            # Clear existing playlist
            self.playlist.clear()
            
            # Add new video
            self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            self.playlist.setCurrentIndex(0)
            
            # Update current video file
            self.current_video_file = file_path
            
            # Reset video dimensions to trigger recalculation
            self.video_width = 0
            self.video_height = 0
            
            print(f"Loaded video: {file_path}")
            return True
            
        except Exception as e:
            print(f"Error loading video: {e}")
            return False

    def change_video(self, file_path):
        """Change to a new video file (called from Flask server)"""
        if self.load_video(file_path):
            # Restart playback
            self.media_player.stop()
            self.media_player.play()
            print(f"Video changed successfully to: {file_path}")
            return True
        return False

    def on_metadata_changed(self):
        """Handle metadata changes to get video dimensions"""
        if self.video_item is None:
            return
        
        # Try to get video resolution
        video_size = self.media_player.metaData("Resolution")
        if video_size and video_size.isValid():
            self.video_width = video_size.width()
            self.video_height = video_size.height()
            self.video_item.setSize(QSizeF(self.video_width, self.video_height))
            print(f"Video size set: {self.video_width}x{self.video_height}")
            self.apply_transformations()

    def on_media_status_changed(self, status):
        """Handle media status changes"""
        if status == QMediaPlayer.LoadedMedia:
            # Fallback method to get video size if metadata doesn't work
            if self.video_width == 0 or self.video_height == 0:
                # Set a default size and let Qt figure it out
                self.video_item.setSize(QSizeF(640, 480))  # Default size
                self.video_width = 640
                self.video_height = 480
                print("Using default video size: 640x480")
            self.apply_transformations()
        elif status == QMediaPlayer.InvalidMedia:
            print(f"Invalid media: {self.current_video_file}")
        elif status == QMediaPlayer.EndOfMedia:
            # This shouldn't happen with Loop mode, but just in case
            self.media_player.play()

    def on_media_error(self):
        """Handle media player errors"""
        error = self.media_player.error()
        error_string = self.media_player.errorString()
        print(f"Media player error ({error}): {error_string}")
        
        # Try to fallback to default video if available
        if self.current_video_file != self.video_file:
            print("Attempting to load default video as fallback...")
            self.load_video(self.video_file)
            self.media_player.play()

    def apply_transformations(self):
        """Apply position, scale, and rotation transformations"""
        if self.video_item is None or not hasattr(self, 'graphics_scene') or self.graphics_scene is None:
            return

        # Make sure we have valid screen dimensions
        if self.screen_width == 0 or self.screen_height == 0:
            self.screen_width = self.width() if self.width() > 0 else 1920
            self.screen_height = self.height() if self.height() > 0 else 1080

        # Calculate actual pixel positions from normalized values (0-400 -> 0-screen_width)
        actual_x = (self.video_x / 400.0) * self.screen_width
        actual_y = (self.video_y / 300.0) * self.screen_height

        # Create transform
        transform = QTransform()
        
        # Set the transform origin to the center of the video for better rotation/scaling
        video_center_x = self.video_width * self.scale_x / 2
        video_center_y = self.video_height * self.scale_y / 2
        
        # Move to position
        transform.translate(actual_x, actual_y)
        
        # Move to center for rotation and scaling
        transform.translate(video_center_x, video_center_y)
        
        # Apply rotation
        transform.rotate(self.video_rotation)
        
        # Apply scaling
        transform.scale(self.scale_x, self.scale_y)
        
        # Move back from center
        transform.translate(-video_center_x, -video_center_y)

        self.video_item.setTransform(transform)
        
        print(f"Applied transform - Pos: ({actual_x:.1f}, {actual_y:.1f}), "
              f"Scale: ({self.scale_x:.2f}, {self.scale_y:.2f}), "
              f"Rotation: {self.video_rotation}°")

    # Methods called by Flask server (these match the HTML interface)
    def set_video_position(self, x: float, y: float):
        """Set video position using HTML slider values (x: 0-400, y: 0-300)"""
        self.video_x = float(x)
        self.video_y = float(y)
        print(f"Setting position: x={x}, y={y}")
        self.apply_transformations()

    def set_video_scale(self, scale_x: float, scale_y: float):
        """Set video scale factors (0.1 to 2.0)"""
        self.scale_x = float(scale_x)
        self.scale_y = float(scale_y)
        print(f"Setting scale: x={scale_x}, y={scale_y}")
        self.apply_transformations()

    def set_video_rotation(self, angle: float):
        """Set video rotation in degrees (0-360)"""
        self.video_rotation = float(angle)
        print(f"Setting rotation: {angle}°")
        self.apply_transformations()

    def get_screen_dimensions(self):
        """Return the current screen dimensions"""
        return self.screen_width, self.screen_height

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        
        # Check if UI components are initialized before proceeding
        if not hasattr(self, 'graphics_scene') or self.graphics_scene is None:
            print("ResizeEvent called before UI initialization - skipping")
            return
            
        if not hasattr(self, 'graphics_view') or self.graphics_view is None:
            print("ResizeEvent called before graphics_view initialization - skipping")
            return
        
        # Update screen dimensions
        self.screen_width = self.width()
        self.screen_height = self.height()
        
        # Update scene size
        self.graphics_scene.setSceneRect(0, 0, self.screen_width, self.screen_height)
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.KeepAspectRatio)
        
        # Reapply transformations with new screen size
        self.apply_transformations()


# Test the video window independently
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VideoWindow()
    window.show()
    
    # Test some transformations after a delay
    from PyQt5.QtCore import QTimer
    
    def test_transforms():
        print("Testing transformations...")
        window.set_video_position(200, 100)  # Center-ish
        window.set_video_scale(0.8, 0.8)     # Slightly smaller
        window.set_video_rotation(15)        # 15 degree rotation
    
    QTimer.singleShot(2000, test_transforms)  # Test after 2 seconds
    
    sys.exit(app.exec_())