from flask import Flask, send_file, render_template_string
import requests
from screen import VideoWindow
import sys
from PyQt5.QtWidgets import QApplication
app = Flask(__name__)

q_app = QApplication(sys.argv)
window = VideoWindow()
window.show()

# Example of moving the video after startup
# Moves it 200 pixels right and 100 pixels down
window.set_video_position(200, 100)
# Example of scaling
window.set_video_scale(0.5, 0.5)
# Example of rotating
window.set_video_rotation(15)

sys.exit(q_app.exec_())
# Option 1: Serve a local HTML file
@app.route('/local')
def local_html():
    return send_file('example.html')  # Make sure example.html exists

# Option 2: Serve an external HTML file via URL
@app.route('/external')
def external_html():
    url = 'https://example.com/index.html'  # Replace with your external URL
    response = requests.get(url)
    return render_template_string(response.text)

if __name__ == '__main__':
    host_ip = '0.0.0.0'  # Replace with desired IP
    port = 5000           # Replace with desired port
    app.run(host=host_ip, port=port)
