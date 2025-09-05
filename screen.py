import sys
import uuid
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene
from PyQt5.QtCore import Qt, QSizeF, QUrl, QRectF, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QTransform, QColor, QPainter
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem


class VideoItem:
    """Represents a single video with its properties and player - Optimized for performance"""
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
        
        # Performance optimization flags
        self._transform_dirty = True
        self._cached_transform = QTransform()
        
        # Qt objects
        self.video_item = QGraphicsVideoItem()
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        
        # Optimized looping timer - reduced frequency
        self.loop_timer = QTimer()
        self.position_check_timer = QTimer()
        
        # Looping state
        self.duration = 0
        self.is_looping = True
        self.loop_point_ms = 100  # Increased tolerance for better performance
        self._last_position_check = 0
        
        # Set up the video item with target size
        self.video_item.setSize(QSizeF(self.target_width, self.target_height))
        self.media_player.setVideoOutput(self.video_item)
        
        # Performance optimizations for video item
        self.video_item.setCacheMode(self.video_item.DeviceCoordinateCache)
        
        # Set up looping with reduced overhead
        self.setup_optimized_looping()
        
        # Load the video
        self.load_video()
    
    def setup_optimized_looping(self):
        """Set up optimized looping with reduced CPU overhead"""
        # Primary looping mechanism - position monitoring (less frequent)
        self.media_player.positionChanged.connect(self.check_near_end)
        self.media_player.durationChanged.connect(self.on_duration_changed)
        
        # Secondary looping mechanism - media status monitoring
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        
        # Reduced frequency position checking - every 200ms instead of 100ms
        self.position_check_timer.timeout.connect(self.force_loop_check)
        self.position_check_timer.start(200)
        
        # Backup timer
        self.loop_timer.timeout.connect(self.backup_loop)
    
    def on_duration_changed(self, duration):
        """Update duration and set backup timer"""
        self.duration = duration
        if self.duration > 0:
            # Less aggressive backup timing for better performance
            backup_interval = max(self.duration - 500, 2000)  # 500ms before end, min 2 seconds
            self.loop_timer.start(backup_interval)
    
    def check_near_end(self, position):
        """Optimized loop check - reduced frequency"""
        # Skip frequent position checks to reduce CPU load
        if position - self._last_position_check < 100:  # Only check every 100ms
            return
        self._last_position_check = position
        
        if self.duration > 0 and self.is_looping:
            time_remaining = self.duration - position
            if time_remaining <= self.loop_point_ms:
                self.perform_loop()
    
    def force_loop_check(self):
        """Reduced frequency forced position checking"""
        if not self.is_looping or self.duration <= 0:
            return
            
        current_position = self.media_player.position()
        time_remaining = self.duration - current_position
        
        # Larger threshold for less frequent checks
        if time_remaining <= 300:  # 300ms threshold
            self.perform_loop()
    
    def backup_loop(self):
        """Backup loop mechanism"""
        if self.is_looping:
            self.perform_loop()
    
    def perform_loop(self):
        """Perform the actual loop operation - optimized"""
        try:
            self.loop_timer.stop()
            self.media_player.setPosition(0)
            
            if self.media_player.state() != QMediaPlayer.PlayingState:
                self.media_player.play()
            
            if self.duration > 0:
                backup_interval = max(self.duration - 500, 2000)
                self.loop_timer.start(backup_interval)
                
        except Exception as e:
            print(f"Video {self.id}: Error in perform_loop: {e}")
    
    def on_media_status_changed(self, status):
        """Handle media status changes"""
        if status == QMediaPlayer.EndOfMedia and self.is_looping:
            self.perform_loop()
        elif status == QMediaPlayer.LoadedMedia:
            if not self.media_player.state() == QMediaPlayer.PlayingState:
                self.play()
    
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
    
    def swap_video(self, new_file_path):
        """Swap the video file while maintaining position and transform settings"""
        try:
            self.media_player.stop()
            self.file_path = new_file_path
            
            media_content = QMediaContent(QUrl.fromLocalFile(new_file_path))
            self.media_player.setMedia(media_content)
            
            self.duration = 0
            self.loop_timer.stop()
            self.play()
            
            print(f"Swapped video {self.id} to: {os.path.basename(new_file_path)}")
            return True
            
        except Exception as e:
            print(f"Error swapping video {self.id}: {e}")
            return False
    
    def play(self):
        """Start playing the video"""
        try:
            self.is_looping = True
            self.media_player.play()
        except Exception as e:
            print(f"Error playing video {self.id}: {e}")
    
    def stop(self):
        """Stop the video"""
        try:
            self.is_looping = False
            self.media_player.stop()
            self.loop_timer.stop()
            self.position_check_timer.stop()
        except Exception as e:
            print(f"Error stopping video {self.id}: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.stop()
            self.media_player.setMedia(QMediaContent())
            if self.video_item.scene():
                self.video_item.scene().removeItem(self.video_item)
        except Exception as e:
            print(f"Error cleaning up video {self.id}: {e}")
    
    def mark_transform_dirty(self):
        """Mark transform as dirty for caching optimization"""
        self._transform_dirty = True
    
    def get_cached_transform(self, screen_width, screen_height, standard_width, standard_height):
        """Get cached transform or compute new one if dirty"""
        if not self._transform_dirty:
            return self._cached_transform
        
        # Calculate actual pixel positions
        actual_x = (self.x / 400.0) * screen_width
        actual_y = (self.y / 300.0) * screen_height
        
        # Create optimized transform
        transform = QTransform()
        video_center_x = standard_width / 2
        video_center_y = standard_height / 2
        
        transform.translate(actual_x, actual_y)
        transform.translate(video_center_x, video_center_y)
        transform.rotate(self.rotation)
        transform.scale(self.scale_x, self.scale_y)
        transform.translate(-video_center_x, -video_center_y)
        
        # Cache the transform
        self._cached_transform = transform
        self._transform_dirty = False
        
        return transform


class VideoController(QObject):
    """Qt object to handle video control signals safely in the Qt thread"""
    position_changed = pyqtSignal(str, float, float)
    scale_changed = pyqtSignal(str, float, float)
    rotation_changed = pyqtSignal(str, float)
    video_added = pyqtSignal(str, str, str)
    video_removed = pyqtSignal(str)
    video_swapped = pyqtSignal(str, str)
    
    def __init__(self, video_window):
        super().__init__()
        self.video_window = video_window
        # Connect signals to slots
        self.position_changed.connect(self.video_window.set_video_position)
        self.scale_changed.connect(self.video_window.set_video_scale)
        self.rotation_changed.connect(self.video_window.set_video_rotation)
        self.video_added.connect(self.video_window.add_video)
        self.video_removed.connect(self.video_window.remove_video)
        self.video_swapped.connect(self.video_window.swap_video)


class VideoWindow(QMainWindow):
    """Optimized video window for maximum performance on Raspberry Pi"""
    def __init__(self):
        super().__init__()
        
        # Dictionary to store all video items
        self.videos = {}  # video_id -> VideoItem
        
        # Screen dimensions
        self.screen_width = 0
        self.screen_height = 0
        
        # Standard video size
        self.standard_video_width = 200
        self.standard_video_height = 150
        
        # Performance optimization flags
        self._batch_updates = False
        self._pending_updates = set()
        
        # Batch update timer for performance
        self.batch_timer = QTimer()
        self.batch_timer.timeout.connect(self.process_batch_updates)
        self.batch_timer.setSingleShot(True)
        
        self.initUI()
        self.update_screen_dimensions()

    def initUI(self):
        """Initialize UI with performance optimizations"""
        self.setWindowTitle('Multi-Video Display - High Performance')
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")

        # Optimized graphics view setup
        self.graphics_view = QGraphicsView(self)
        
        # Performance optimizations for graphics view
        self.graphics_view.setRenderHint(QPainter.Antialiasing, False)  # Disable anti-aliasing for speed
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, False)  # Disable smooth transforms
        self.graphics_view.setRenderHint(QPainter.TextAntialiasing, False)
        self.graphics_view.setOptimizationFlags(
            QGraphicsView.DontSavePainterState |
            QGraphicsView.DontAdjustForAntialiasing
        )
        
        # Disable scroll bars for better performance
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Set viewport update mode for better performance
        self.graphics_view.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
        
        # Disable drag mode for performance
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        
        self.setCentralWidget(self.graphics_view)

        # Optimized graphics scene
        self.graphics_scene = QGraphicsScene()
        self.graphics_scene.setBackgroundBrush(QColor("black"))
        
        # Performance optimizations for scene
        self.graphics_scene.setItemIndexMethod(QGraphicsScene.NoIndex)  # Disable spatial indexing for small scenes
        
        self.graphics_view.setScene(self.graphics_scene)

    def update_screen_dimensions(self):
        """Update screen dimensions and refresh all video positions"""
        old_width, old_height = self.screen_width, self.screen_height
        
        self.screen_width = self.width() if self.width() > 0 else 1920
        self.screen_height = self.height() if self.height() > 0 else 1080
        
        # Update scene size
        self.graphics_scene.setSceneRect(0, 0, self.screen_width, self.screen_height)
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.KeepAspectRatio)
        
        if old_width != self.screen_width or old_height != self.screen_height:
            print(f"Screen dimensions updated: {self.screen_width}x{self.screen_height}")
            
            # Mark all transforms as dirty and batch update
            for video_id, video_item in self.videos.items():
                video_item.mark_transform_dirty()
            self.batch_update_all_transforms()

    def add_video(self, video_id, file_path, filename):
        """Add a new video to the display"""
        try:
            video_item = VideoItem(
                video_id, 
                file_path, 
                self.standard_video_width, 
                self.standard_video_height
            )
            
            self.graphics_scene.addItem(video_item.video_item)
            self.videos[video_id] = video_item
            
            self.apply_transformations(video_id)
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

    def swap_video(self, video_id, new_file_path):
        """Swap the video file for an existing video"""
        try:
            if video_id in self.videos:
                video_item = self.videos[video_id]
                success = video_item.swap_video(new_file_path)
                if success:
                    print(f"Successfully swapped video {video_id} to {os.path.basename(new_file_path)}")
                return success
            else:
                print(f"Video {video_id} not found for swapping")
                return False
        except Exception as e:
            print(f"Error swapping video {video_id}: {e}")
            return False

    def apply_transformations(self, video_id):
        """Apply transformations using cached transforms for performance"""
        if video_id not in self.videos:
            return

        video_item = self.videos[video_id]
        
        if self.screen_width == 0 or self.screen_height == 0:
            self.screen_width = self.width() if self.width() > 0 else 1920
            self.screen_height = self.height() if self.height() > 0 else 1080

        # Use cached transform for better performance
        transform = video_item.get_cached_transform(
            self.screen_width, self.screen_height,
            self.standard_video_width, self.standard_video_height
        )
        
        video_item.video_item.setTransform(transform)

    def batch_update_transforms(self, video_ids):
        """Batch update multiple video transforms for better performance"""
        if not video_ids:
            return
            
        self._batch_updates = True
        
        for video_id in video_ids:
            if video_id in self.videos:
                self.videos[video_id].mark_transform_dirty()
                self._pending_updates.add(video_id)
        
        # Start batch timer (10ms delay to collect more updates)
        self.batch_timer.start(10)
    
    def process_batch_updates(self):
        """Process all pending transform updates in a batch"""
        if not self._pending_updates:
            return
        
        # Temporarily disable scene updates for better performance
        self.graphics_scene.blockSignals(True)
        
        for video_id in self._pending_updates:
            self.apply_transformations(video_id)
        
        self.graphics_scene.blockSignals(False)
        self._pending_updates.clear()
        self._batch_updates = False
        
        # Force a single scene update
        self.graphics_scene.update()
    
    def batch_update_all_transforms(self):
        """Batch update all video transforms"""
        self.batch_update_transforms(list(self.videos.keys()))

    def set_video_position(self, video_id: str, x: float, y: float):
        """Set video position with batched updates"""
        if video_id in self.videos:
            video_item = self.videos[video_id]
            video_item.x = float(x)
            video_item.y = float(y)
            video_item.mark_transform_dirty()
            
            if self._batch_updates:
                self._pending_updates.add(video_id)
            else:
                self.batch_update_transforms([video_id])

    def set_video_scale(self, video_id: str, scale_x: float, scale_y: float):
        """Set video scale with batched updates"""
        if video_id in self.videos:
            video_item = self.videos[video_id]
            video_item.scale_x = float(scale_x)
            video_item.scale_y = float(scale_y)
            video_item.mark_transform_dirty()
            
            if self._batch_updates:
                self._pending_updates.add(video_id)
            else:
                self.batch_update_transforms([video_id])

    def set_video_rotation(self, video_id: str, angle: float):
        """Set video rotation with batched updates"""
        if video_id in self.videos:
            video_item = self.videos[video_id]
            video_item.rotation = float(angle)
            video_item.mark_transform_dirty()
            
            if self._batch_updates:
                self._pending_updates.add(video_id)
            else:
                self.batch_update_transforms([video_id])

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
        """Handle window resize events with optimized updates"""
        super().resizeEvent(event)
        
        if not hasattr(self, 'graphics_scene') or self.graphics_scene is None:
            return
            
        if not hasattr(self, 'graphics_view') or self.graphics_view is None:
            return
        
        self.update_screen_dimensions()


# Test the video window independently
if __name__ == '__main__':
    # Set Qt application attributes for better performance on Raspberry Pi
    QApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
    QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings, True)
    
    app = QApplication(sys.argv)
    
    # Set application-wide performance optimizations
    app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
    
    window = VideoWindow()
    window.show()
    
    # Test adding videos after a delay
    from PyQt5.QtCore import QTimer
    
    def test_multiple_videos():
        print("Testing optimized video performance...")
        video1_path = "/home/pil/Downloads/MovingPaintings/65562-515098354_medium.mp4"
        if os.path.exists(video1_path):
            window.add_video("video1", video1_path, "video1.mp4")
            window.set_video_position("video1", 100, 100)
            window.set_video_scale("video1", 0.8, 0.8)
    
    QTimer.singleShot(2000, test_multiple_videos)
    
    sys.exit(app.exec_())