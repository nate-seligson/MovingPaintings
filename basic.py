import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QFileDialog, QSlider, QGraphicsView, QGraphicsScene
)
from PyQt5.QtCore import Qt, QUrl, QSizeF
from PyQt5.QtGui import QFont, QTransform
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- EDIT THESE to change video transform in code (not via GUI) ---
        self.video_x = 50             # x position in scene
        self.video_y = 30             # y position in scene
        self.video_rotation = 15      # rotation in degrees
        self.scale_x = 1.2            # horizontal scale
        self.scale_y = 0.8            # vertical scale
        # ------------------------------------------------------------------

        self.initUI()

    def initUI(self):
        self.setWindowTitle('PyQt5 Video Player (Windows/Linux)')
        self.setGeometry(100, 100, 800, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)

        # Title
        title = QLabel('PyQt5 Video Player')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 16, QFont.Bold))
        self.layout.addWidget(title)

        # Graphics view + scene + video item
        self.graphics_view = QGraphicsView()
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view.setScene(self.graphics_scene)
        self.layout.addWidget(self.graphics_view, stretch=1)

        # Media player + playlist (loop)
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.playlist = QMediaPlaylist()
        self.playlist.setPlaybackMode(QMediaPlaylist.Loop)
        self.media_player.setPlaylist(self.playlist)

        # Video item
        self.video_item = QGraphicsVideoItem()
        self.video_item.setSize(QSizeF(640, 360))
        self.graphics_scene.addItem(self.video_item)
        self.media_player.setVideoOutput(self.video_item)

        # Controls
        controls = QHBoxLayout()
        self.upload_btn = QPushButton("Upload")
        self.upload_btn.clicked.connect(self.upload_file)

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_video)
        self.play_btn.setEnabled(False)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_video)
        self.stop_btn.setEnabled(False)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)

        controls.addWidget(self.upload_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.position_slider)
        self.layout.addLayout(controls)

        # Info
        self.video_info = QLabel("No video loaded")
        self.video_info.setStyleSheet('color: gray; font-style: italic;')
        self.layout.addWidget(self.video_info)

        # Signals
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)

    # === Video methods ===
    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Upload Video File', '',
            'Video Files (*.mp4 *.avi *.mov *.wmv *.mkv *.flv);;All Files (*)'
        )
        if not file_path:
            return

        self.playlist.clear()
        self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.playlist.setCurrentIndex(0)

        self.video_info.setText(f"Loaded: {os.path.basename(file_path)}")
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

        self.update_video_item_size()
        self.apply_transformations()

        self.media_player.play()
        self.play_btn.setText("Pause")

    def play_video(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("Play")
        else:
            self.media_player.play()
            self.play_btn.setText("Pause")

    def stop_video(self):
        self.media_player.stop()
        self.play_btn.setText("Play")

    def media_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setText("Pause")
        else:
            self.play_btn.setText("Play")

    def position_changed(self, position):
        self.position_slider.setValue(position)

    def duration_changed(self, duration):
        self.position_slider.setRange(0, duration)

    def set_position(self, position):
        self.media_player.setPosition(position)

    def apply_transformations(self):
        """
        Apply position, rotation, and independent scale_x/scale_y.
        """
        transform = QTransform()
        transform.translate(self.video_x, self.video_y)
        transform.rotate(self.video_rotation)
        transform.scale(self.scale_x, self.scale_y)
        self.video_item.setTransform(transform)

    def update_video_item_size(self):
        viewport_size = self.graphics_view.viewport().size()
        if viewport_size.width() > 0 and viewport_size.height() > 0:
            self.video_item.setSize(QSizeF(viewport_size.width(), viewport_size.height()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.KeepAspectRatio)
        self.update_video_item_size()
        self.apply_transformations()


def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
