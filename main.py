from flask import Flask, jsonify

server = Flask(__name__, static_folder="frontend/dist", static_url_path="")

@server.route("/api/hello")
def hello():
    return jsonify({"message": "API Working!"})

@server.route("/", defaults={"path": ""})
@server.route("/<path:path>")
def spa(path):
    if path.startswith("api"):
        return jsonify({"error": "API route not found"}), 404

    return server.send_static_file("index.html")


if __name__ == '__main__':
    server.run(port=8080)
