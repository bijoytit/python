import os
import json
import datetime
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template_string, request
import subprocess
import psutil
import shutil
import threading

app = Flask(__name__)

# --- Configuration ---
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/xxx/yyy/zzz"  # Replace with your Slack webhook URL
ALERT_EMAIL_FROM = "your_email@example.com"
ALERT_EMAIL_TO = "alert_recipient@example.com"
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587
SMTP_USERNAME = "smtp_user"
SMTP_PASSWORD = "smtp_password"

MEMORY_ALERT_THRESHOLD = 80  # % memory usage to trigger alert

LOGS_DIR = "./logs"
os.makedirs(LOGS_DIR, exist_ok=True)

alert_sent = False  # global flag to prevent alert spamming

# --- HTML Template with auto-refresh and dark mode ---
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>T24 Full System Monitor</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; color: #333; padding: 20px; transition: background-color 0.5s, color 0.5s;}
        body.dark { background: #121212; color: #e0e0e0; }
        h1 { color: #0057b8; }
        body.dark h1 { color: #87cefa; }
        .section { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 0 8px rgba(0,0,0,0.1); transition: background-color 0.5s, color 0.5s;}
        body.dark .section { background: #222; }
        .label { font-weight: bold; }
        pre { background: #f0f0f0; padding: 10px; border-radius: 5px; overflow-x: auto; }
        body.dark pre { background: #333; }
        #darkModeToggle { margin-bottom: 20px; padding: 8px 15px; cursor: pointer; }
    </style>
    <script>
        // Auto refresh every 30 seconds
        setTimeout(function(){
            window.location.reload(1);
        }, 30000);

        // Dark mode toggle with localStorage
        function setDarkMode(enabled) {
            if(enabled){
                document.body.classList.add("dark");
                localStorage.setItem("darkMode", "true");
            } else {
                document.body.classList.remove("dark");
                localStorage.setItem("darkMode", "false");
            }
        }
        window.onload = function(){
            const darkMode = localStorage.getItem("darkMode");
            if(darkMode === "true") {
                setDarkMode(true);
                document.getElementById("darkModeToggle").innerText = "Switch to Light Mode";
            } else {
                setDarkMode(false);
                document.getElementById("darkModeToggle").innerText = "Switch to Dark Mode";
            }
        }
        function toggleDarkMode() {
            const enabled = document.body.classList.contains("dark");
            setDarkMode(!enabled);
            document.getElementById("darkModeToggle").innerText = enabled ? "Switch to Dark Mode" : "Switch to Light Mode";
        }
    </script>
</head>
<body>
    <button id="darkModeToggle" onclick="toggleDarkMode()">Switch to Dark Mode</button>
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

# --- Functions ---

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

def send_slack_alert(message):
    import requests
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        return response.status_code == 200
    except Exception as e:
        print("Slack alert error:", e)
        return False

def send_email_alert(subject, message):
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = ALERT_EMAIL_FROM
        msg["To"] = ALERT_EMAIL_TO

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Email alert error:", e)
        return False

def log_to_file(data: dict):
    # Append JSON lines to daily log file
    log_file = os.path.join(LOGS_DIR, datetime.date.today().isoformat() + ".log")
    with open(log_file, "a") as f:
        f.write(json.dumps(data) + "\n")

def check_and_alert(system_metrics):
    global alert_sent
    mem_pct = system_metrics["memory_percent"]

    # Log metrics always
    log_to_file({
        "timestamp": datetime.datetime.now().isoformat(),
        "cpu_percent": system_metrics["cpu_percent"],
        "memory_percent": mem_pct
    })

    if mem_pct >= MEMORY_ALERT_THRESHOLD:
        if not alert_sent:
            msg = f"⚠️ Memory usage alert! Current RAM usage at {mem_pct}%"
            send_slack_alert(msg)
            send_email_alert("T24 Memory Usage Alert", msg)
            alert_sent = True
    else:
        if alert_sent:
            # Memory back to normal, reset alert
            msg = f"✅ Memory usage back to normal: {mem_pct}%"
            send_slack_alert(msg)
            send_email_alert("T24 Memory Usage Normalized", msg)
            alert_sent = False

@app.route("/")
def dashboard():
    system_metrics = get_system_metrics()
    check_and_alert(system_metrics)  # check alert and log every page load

    return render_template_string(
        html_template,
        system_metrics=system_metrics,
        disk=get_disk_usage(),
        jboss_output_primary=run_jboss_cli("100.100.97.55"),
        jboss_output_secondary=run_jboss_cli("100.100.97.56"),
        artemis_output=run_artemis_cli(),
        t24_processes=get_t24_processes(),
        cob_logs=get_cob_logs()
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
