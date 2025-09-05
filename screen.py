import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene
from PyQt5.QtCore import Qt, QSizeF, QUrl
from PyQt5.QtGui import QTransform, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem


class VideoWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.video_file = "/home/pil/Downloads/MovingPaintings/65562-515098354_medium.mp4"

        # Transform parameters
        self.video_x = 0  # horizontal position offset in pixels
        self.video_y = 0  # vertical position offset in pixels
        self.video_rotation = 0
        self.scale_x = 1.0
        self.scale_y = 1.0

        # Initialize attributes
        self.video_item = None
        self.media_player = None

        self.initUI()

    def initUI(self):
        self.setWindowTitle('')
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")

        # Graphics view + scene
        self.graphics_view = QGraphicsView(self)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(self.graphics_view)

        self.graphics_scene = QGraphicsScene(self)
        self.graphics_scene.setBackgroundBrush(QColor("black"))
        self.graphics_view.setScene(self.graphics_scene)

        # Video item
        self.video_item = QGraphicsVideoItem()
        self.graphics_scene.addItem(self.video_item)

        # Media player + playlist
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.playlist = QMediaPlaylist()
        self.playlist.setPlaybackMode(QMediaPlaylist.Loop)
        self.media_player.setPlaylist(self.playlist)
        self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(self.video_file)))
        self.playlist.setCurrentIndex(0)

        self.media_player.setVideoOutput(self.video_item)

        # Connect metadata signal to set video size once loaded
        self.media_player.metaDataChanged.connect(self.on_metadata_changed)
        self.media_player.play()

    def on_metadata_changed(self):
        if self.video_item is None:
            return
        video_size = self.media_player.metaData("Resolution")
        if video_size:
            self.video_item.setSize(QSizeF(video_size.width(), video_size.height()))
            self.apply_transformations()

    def apply_transformations(self):
        """Apply position, scale, and rotation."""
        if self.video_item is None:
            return
        transform = QTransform()
        # Translate first to move video
        transform.translate(self.video_x, self.video_y)
        # Rotate around top-left corner
        transform.rotate(self.video_rotation)
        # Scale from top-left corner
        transform.scale(self.scale_x, self.scale_y)
        self.video_item.setTransform(transform)

    # Methods to update video properties
    def set_video_position(self, x: float, y: float):
        """Move video to pixel coordinates (x, y)."""
        self.video_x = x
        self.video_y = y
        self.apply_transformations()

    def set_video_scale(self, scale_x: float, scale_y: float):
        """Scale video independently in X and Y."""
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.apply_transformations()

    def set_video_rotation(self, angle: float):
        """Rotate video in degrees."""
        self.video_rotation = angle
        self.apply_transformations()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_transformations()