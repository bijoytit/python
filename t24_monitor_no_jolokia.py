
import os
from flask import Flask, jsonify, render_template_string
import subprocess
import psutil

app = Flask(__name__)

# HTML template for dashboard
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>T24 System Monitor</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; color: #333; padding: 20px; }
        h1 { color: #0057b8; }
        .section { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 0 8px rgba(0,0,0,0.1); }
        .label { font-weight: bold; }
    </style>
</head>
<body>
    <h1>T24 System Monitoring Dashboard</h1>
    <div class="section">
        <div><span class="label">System CPU Usage:</span> {{ system_metrics['cpu_percent'] }}%</div>
        <div><span class="label">System RAM Usage:</span> {{ system_metrics['memory_percent'] }}%</div>
    </div>
    <div class="section">
        <h2>JBoss Memory Stats</h2>
        <pre>{{ jboss_output }}</pre>
    </div>
    <div class="section">
        <h2>Artemis Queue Stats</h2>
        <pre>{{ artemis_output }}</pre>
    </div>
</body>
</html>
"""

def get_system_metrics():
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent
    }

def run_jboss_cli():
    cmd = [
        "/opt/jboss-eap-7.2/bin/jboss-cli.sh",
        "--connect",
        "--controller=127.0.0.1:9990",
        "--command=/core-service=platform-mbean/type=memory:read-resource(include-runtime=true)"
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        output = f"Error: {e.output}"
    return output

def run_artemis_cli():
    cmd = [
        "artemis",
        "queue",
        "stat",
        "--name", "IN.OFS.REQUEST",
        "--user", "admin",
        "--password", "admin"
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        output = f"Error: {e.output}"
    return output

@app.route("/")
def dashboard():
    system_metrics = get_system_metrics()
    jboss_output = run_jboss_cli()
    artemis_output = run_artemis_cli()
    return render_template_string(html_template, system_metrics=system_metrics, jboss_output=jboss_output, artemis_output=artemis_output)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
