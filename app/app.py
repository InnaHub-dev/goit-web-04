import json
import logging
import mimetypes
import os
import pathlib
import socket
import urllib.parse

from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


directory = pathlib.Path()
BUFFER = 1024
IP = "127.0.0.1"
HTTP_PORT = 3000
SOCKET_PORT = 5000


class HTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        print(route.path)
        match route.path:
            case "/":
                self.send_html("index.html")
            case "/message.html":
                self.send_html("message.html")
            case _:
                file = directory / route.path[1:]
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html("error.html", 404)

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        self.send_data_to_socket(body)
        self.send_response(302)
        self.send_header("Location", "/message.html")
        self.end_headers()

    def send_data_to_socket(self, data):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (IP, SOCKET_PORT))
        client_socket.close()

    def send_static(self, filename):
        self.send_response(200)
        mimetype, *rest = mimetypes.guess_type(filename)
        if mimetype:
            self.send_header("Content-type", mimetype)
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())

    def send_html(self, filename, status_code=200):
        print(f"sending {filename}")
        filepath = directory / filename
        print(filepath)
        self.send_response(status_code)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filepath, "rb") as f:
            self.wfile.write(f.read())


socket_host = socket.gethostname()


def run_socket_server(ip, port):
    socket_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socket_server.bind((ip, port))
    try:
        while True:
            data, address = socket_server.recvfrom(BUFFER)
            save_data(data)
    except KeyboardInterrupt:
        logging.info("Socket server stopped")
    finally:
        socket_server.close()


def save_data(data):
    data = urllib.parse.unquote_plus(data.decode())
    message_time = str(datetime.now())
    try:
        payload = {
            key: value for key, value in [el.split("=") for el in data.split("&")]
        }
        payload = {message_time: payload}
        json_file_name = directory.joinpath("storage/data.json")
        if json_file_name.stat().st_size > 0:
            with open(json_file_name, "r", encoding="utf-8") as f:
                json_dict = json.load(f)
        else:
            json_dict = {}
        json_dict.update(payload)
        print(json_dict)
        with open(json_file_name, "w", encoding="utf-8") as f:
            json.dump(json_dict, f, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.error(f"Field parse data {data} with {err}")
    except OSError as err:
        logging.error(f"Field write data {data} with {err}")


def run_http_server(server=HTTPServer, handler=HTTPHandler):
    server_address = ("", HTTP_PORT)
    http_server = server(server_address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")
    tread_http_server = Thread(target=run_http_server)
    tread_http_server.start()

    thread_socket_server = Thread(target=run_socket_server, args=(IP, SOCKET_PORT))
    thread_socket_server.start()
