from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import sys
import threading
import os

app = Flask(__name__)
CORS(app) # Allow admin.html to call this

# Status to keep track of running batch
batch_status = {
    "is_running": False,
    "last_run_time": None,
    "last_output": ""
}

def run_batch_task():
    global batch_status
    batch_status["is_running"] = True
    try:
        # Run main.py as a subprocess
        result = subprocess.run([sys.executable, "main.py"], capture_output=True, text=True)
        batch_status["last_output"] = result.stdout + "\n" + result.stderr
    except Exception as e:
        batch_status["last_output"] = str(e)
    finally:
        batch_status["is_running"] = False

@app.route('/run-batch', methods=['POST'])
def run_batch():
    if batch_status["is_running"]:
        return jsonify({"message": "Batch is already running"}), 400
    
    # Run in background thread
    thread = threading.Thread(target=run_batch_task)
    thread.start()
    
    return jsonify({"message": "Batch started successfully"}), 200

@app.route('/batch-status', methods=['GET'])
def get_status():
    return jsonify(batch_status), 200

if __name__ == '__main__':
    # Run API on port 5000
    app.run(port=5000)
