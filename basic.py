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
        self.video_file = "path/to/your/video.mp4"  # <--- change this
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
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("background-color: black;")  # make background black

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

        # Apply transform and play
        self.update_video_item_size()
        self.apply_transformations()
        self.media_player.play()

    def apply_transformations(self):
        transform = QTransform()
        transform.translate(self.video_x, self.video_y)
        transform.rotate(self.video_rotation)
        transform.scale(self.scale_x, self.scale_y)
        self.video_item.setTransform(transform)

    def update_video_item_size(self):
        viewport_size = self.graphics_view.viewport().size()
        self.video_item.setSize(QSizeF(viewport_size.width(), viewport_size.height()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.KeepAspectRatio)
        self.update_video_item_size()
        self.apply_transformations()


def main():
    app = QApplication(sys.argv)
    window = VideoWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
