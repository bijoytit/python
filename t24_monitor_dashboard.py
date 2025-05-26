
import requests
import psutil
import subprocess
from flask import Flask

# Configurations
JBOSS_JOLOKIA_URL = "http://localhost:8778/jolokia/read/java.lang:type=Memory"
ARTEMIS_JOLOKIA_URL = "http://localhost:8779/jolokia/read/org.apache.activemq.artemis:broker=\"0.0.0.0\""
ARTEMIS_CLI_USER = "admin"
ARTEMIS_CLI_PASS = "admin"
ARTEMIS_QUEUE_NAME = "IN.OFS.REQUEST"

app = Flask(__name__)

def get_system_health():
    try:
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        return f"System RAM Usage: {mem.percent}%<br>CPU Usage: {cpu}%"
    except Exception as e:
        return f"Error fetching system health: {str(e)}"

def get_jboss_memory():
    try:
        res = requests.get(JBOSS_JOLOKIA_URL).json()
        heap = res['value']['HeapMemoryUsage']
        used = heap['used'] / (1024 * 1024)
        max_mem = heap['max'] / (1024 * 1024)
        return f"JBoss Heap Usage: {used:.1f} MB / {max_mem:.1f} MB"
    except Exception as e:
        return f"Error fetching JBoss memory: {str(e)}"

def get_artemis_memory():
    try:
        res = requests.get(ARTEMIS_JOLOKIA_URL).json()
        memory = res['value'].get('AddressMemoryUsage', 'N/A')
        return f"Artemis MQ Memory Usage: {memory}%"
    except Exception as e:
        return f"Error fetching Artemis memory: {str(e)}"

def get_queue_depth():
    try:
        cmd = [
            "artemis", "queue", "stat",
            "--name", ARTEMIS_QUEUE_NAME,
            "--user", ARTEMIS_CLI_USER,
            "--password", ARTEMIS_CLI_PASS
        ]
        output = subprocess.check_output(cmd).decode()
        return f"<pre>{output}</pre>"
    except Exception as e:
        return f"Error fetching queue depth: {str(e)}"

@app.route("/")
def dashboard():
    return f'''
    <h1>T24 System Monitor</h1>
    <p>{get_system_health()}</p>
    <p>{get_jboss_memory()}</p>
    <p>{get_artemis_memory()}</p>
    <h2>Queue Depth</h2>
    {get_queue_depth()}
    '''

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
