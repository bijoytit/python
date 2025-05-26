import os
from flask import Flask, render_template_string
import subprocess
import psutil
import shutil

app = Flask(__name__)

html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>T24 Full System Monitor</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; color: #333; padding: 20px; }
        h1 { color: #0057b8; }
        .section { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 0 8px rgba(0,0,0,0.1); }
        .label { font-weight: bold; }
        pre { background: #f0f0f0; padding: 10px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>T24 System Monitoring Dashboard</h1>

    <div class="section">
        <h2>System Metrics</h2>
        <div><span class="label">CPU Usage:</span> {{ system_metrics['cpu_percent'] }}%</div>
        <div><span class="label">RAM Usage:</span> {{ system_metrics['memory_percent'] }}%</div>
        <div><span class="label">Disk Usage:</span> {{ disk['used_gb'] }} GB used / {{ disk['total_gb'] }} GB total ({{ disk['percent_used'] }}%)</div>
    </div>

    <div class="section">
        <h2>JBoss Memory Stats (Primary Host)</h2>
        <pre>{{ jboss_output_primary }}</pre>
    </div>
    <div class="section">
        <h2>JBoss Memory Stats (Secondary Host)</h2>
        <pre>{{ jboss_output_secondary }}</pre>
    </div>

    <div class="section">
        <h2>Artemis Queue Stats</h2>
        <pre>{{ artemis_output }}</pre>
    </div>

    <div class="section">
        <h2>T24 Process Snapshot</h2>
        <pre>{{ t24_processes }}</pre>
    </div>

    <div class="section">
        <h2>Recent COB Log Warnings</h2>
        <pre>{{ cob_logs }}</pre>
    </div>
</body>
</html>
"""

def get_system_metrics():
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent
    }

def get_disk_usage():
    total, used, free = shutil.disk_usage("/")
    return {
        "total_gb": total // (2**30),
        "used_gb": used // (2**30),
        "free_gb": free // (2**30),
        "percent_used": int((used / total) * 100)
    }

def run_jboss_cli(host_ip):
    cmd = [
        "/opt/jboss-eap-7.2/bin/jboss-cli.sh",
        "--connect",
        f"--controller={host_ip}:9990",
        "--command=/core-service=platform-mbean/type=memory:read-resource(include-runtime=true)"
    ]
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        return f"JBoss ({host_ip}) Error: {e.output}"

def run_artemis_cli():
    cmd = [
        "artemis", "queue", "stat",
        "--name", "IN.OFS.REQUEST",
        "--user", "admin", "--password", "admin"
    ]
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        return f"Artemis Error: {e.output}"

def get_t24_processes():
    try:
        output = subprocess.check_output(["ps", "aux"], text=True)
        lines = [line for line in output.splitlines() if any(proc in line for proc in ["tSS", "jBoss", "arserver", "OFS"])][:10]
        return "\n".join(lines)
    except Exception as e:
        return str(e)

def get_cob_logs():
    try:
        log_path = "/data/t24/BNK/COB.LOG"  # ⚠️ Change this if your log is elsewhere
        if os.path.exists(log_path):
            with open(log_path, "r") as f:
                lines = f.readlines()
                error_lines = [line for line in lines if any(word in line for word in ["ERROR", "ABORT", "FAILED"])]
                return "".join(error_lines[-10:])
        return "COB log not found."
    except Exception as e:
        return str(e)

@app.route("/")
def dashboard():
    return render_template_string(
        html_template,
        system_metrics=get_system_metrics(),
        disk=get_disk_usage(),
        jboss_output_primary=run_jboss_cli("100.100.97.55"),
        jboss_output_secondary=run_jboss_cli("100.100.97.56"),
        artemis_output=run_artemis_cli(),
        t24_processes=get_t24_processes(),
        cob_logs=get_cob_logs()
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
