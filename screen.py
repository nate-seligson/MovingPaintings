import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene
from PyQt5.QtCore import Qt, QSizeF, QUrl
from PyQt5.QtGui import QTransform, QColor
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem


class VideoWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- EDIT THIS to set the video file path ---
        self.video_file = "/home/pil/Downloads/MovingPaintings/65562-515098354_medium.mp4"
        # ------------------------------------------------------------------

        # --- EDIT THESE to set transform in code ---
        self.video_x = 0
        self.video_y = 0
        self.video_rotation = 0
        self.scale_x = 1.0
        self.scale_y = 1.0
        # ------------------------------------------------------------------

        self.initUI()

    def initUI(self):
        self.setWindowTitle('')
        self.showFullScreen()  # fullscreen window
        self.setStyleSheet("background-color: black;")

        # Graphics view + scene
        self.graphics_view = QGraphicsView(self)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(self.graphics_view)

        self.graphics_scene = QGraphicsScene(self)
        self.graphics_scene.setBackgroundBrush(QColor("black"))
        self.graphics_view.setScene(self.graphics_scene)

        # Media player + playlist
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.playlist = QMediaPlaylist()
        self.playlist.setPlaybackMode(QMediaPlaylist.Loop)
        self.media_player.setPlaylist(self.playlist)
        self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(self.video_file)))
        self.playlist.setCurrentIndex(0)

        # Video item
        self.video_item = QGraphicsVideoItem()
        self.graphics_scene.addItem(self.video_item)
        self.media_player.setVideoOutput(self.video_item)

        # Wait for media to load to get pixel size
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.play()

    def on_media_status_changed(self, status):
        if status == QMediaPlayer.LoadedMedia:
            # Set the video to its native pixel size
            video_size = self.media_player.metaData("Resolution")
            if video_size is not None:
                self.video_item.setSize(QSizeF(video_size.width(), video_size.height()))
                self.apply_transformations()

    def apply_transformations(self):
        transform = QTransform()
        transform.translate(self.video_x, self.video_y)
        transform.rotate(self.video_rotation)
        transform.scale(self.scale_x, self.scale_y)
        self.video_item.setTransform(transform)

    # Override resizeEvent but do nothing to prevent scaling with window
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep the video pixel size constant
        self.apply_transformations()


def main():
    app = QApplication(sys.argv)
    window = VideoWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
