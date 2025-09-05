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

        # Transform params
        self.video_x = 0
        self.video_y = 0
        self.video_rotation = 0
        self.scale_x = 1.0
        self.scale_y = 1.0

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

        # Wait for metadata to be available
        self.media_player.metaDataChanged.connect(self.on_metadata_changed)
        self.media_player.play()

    def on_metadata_changed(self):
        # Only proceed if resolution is available
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

    # Keep video pixel size constant on resize
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.apply_transformations()


def main():
    app = QApplication(sys.argv)
    window = VideoWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
