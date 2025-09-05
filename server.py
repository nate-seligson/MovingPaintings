from flask import Flask, send_file, render_template_string
import requests

app = Flask(__name__)

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
