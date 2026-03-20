from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import sys
import threading
import os
import queue
import time

app = Flask(__name__)
CORS(app)

# Global state
batch_status = {
    "is_running": False,
    "current_logs": "",
    "last_output": ""
}

# Queue to communicate between threads
log_queue = queue.Queue()

def run_batch_task():
    global batch_status
    batch_status["is_running"] = True
    batch_status["current_logs"] = ""
    
    try:
        # Start main.py and capture output in real-time
        process = subprocess.Popen(
            [sys.executable, "-u", "main.py"], # -u for unbuffered output
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Read output line by line as it happens
        for line in iter(process.stdout.readline, ''):
            if line:
                batch_status["current_logs"] += line
                print(f"DEBUG: {line.strip()}") # Server-side debug
        
        process.stdout.close()
        process.wait()
        
        batch_status["last_output"] = batch_status["current_logs"]
    except Exception as e:
        batch_status["current_logs"] += f"\nERROR: {str(e)}"
        batch_status["last_output"] = batch_status["current_logs"]
    finally:
        batch_status["is_running"] = False

@app.route('/run-batch', methods=['POST'])
def run_batch():
    if batch_status["is_running"]:
        return jsonify({"message": "Batch is already running"}), 400
    
    # Reset status
    batch_status["current_logs"] = "> Initializing batch process...\n"
    batch_status["last_output"] = ""
    
    thread = threading.Thread(target=run_batch_task)
    thread.start()
    
    return jsonify({"message": "Batch started successfully"}), 200

@app.route('/batch-status', methods=['GET'])
def get_status():
    # Return accumulated logs for real-time display
    return jsonify({
        "is_running": batch_status["is_running"],
        "logs": batch_status["current_logs"],
        "last_output": batch_status["last_output"]
    }), 200

if __name__ == '__main__':
    app.run(port=5000)
