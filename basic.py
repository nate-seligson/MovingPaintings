import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QFileDialog, QSlider
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('PyQt5 Video Player (Windows/Linux)')
        self.setGeometry(100, 100, 600, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)

        # Title
        title = QLabel('PyQt5 Video Player')
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont('Arial', 16, QFont.Bold))
        self.layout.addWidget(title)

        # Video widget
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        self.layout.addWidget(self.video_widget, stretch=1)

        # Controls
        controls = QHBoxLayout()
        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self.open_file)

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.play_video)
        self.play_btn.setEnabled(False)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_video)
        self.stop_btn.setEnabled(False)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.set_position)

        controls.addWidget(self.open_btn)
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
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Open Video File', '',
            'Video Files (*.mp4 *.avi *.mov *.wmv *.mkv *.flv);;All Files (*)'
        )
        if not file_path:
            return

        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.video_info.setText(f"Loaded: {os.path.basename(file_path)}")
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

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


def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
