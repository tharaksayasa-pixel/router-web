from flask import Flask, request, jsonify
import paramiko
import time
import ipaddress

app = Flask(__name__)

USERNAME = "admin"
PASSWORD = "cisco"


def run_command(router_ip, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=router_ip,
            port=22,
            username=USERNAME,
            password=PASSWORD,
            look_for_keys=False,
            allow_agent=False,
            timeout=10
        )

        channel = client.invoke_shell()

        time.sleep(1)

        if channel.recv_ready():
            channel.recv(65535)

        channel.send("terminal length 0\n")
        time.sleep(0.5)

        if channel.recv_ready():
            channel.recv(65535)

        channel.send(command + "\n")

        output = ""
        last_data = time.time()
        timeout = time.time() + 10

        while time.time() < timeout:
            if channel.recv_ready():
                data = channel.recv(65535).decode(
                    "utf-8",
                    errors="ignore"
                )
                output += data
                last_data = time.time()

            elif output and time.time() - last_data > 1:
                break

            time.sleep(0.1)

        return output.strip()

    finally:
        client.close()


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/execute", methods=["POST"])
def execute():
    data = request.get_json(silent=True) or {}

    router_ip = str(data.get("ip", "")).strip()
    command = str(data.get("command", "")).strip()

    if not router_ip or not command:
        return jsonify({
            "success": False,
            "error": "Router IP and command are required"
        }), 400

    try:
        ipaddress.ip_address(router_ip)
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid router IP"
        }), 400

    try:
        output = run_command(router_ip, command)

        return jsonify({
            "success": True,
            "output": output
        })

    except paramiko.AuthenticationException:
        return jsonify({
            "success": False,
            "error": "SSH authentication failed"
        }), 401

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )
PY
