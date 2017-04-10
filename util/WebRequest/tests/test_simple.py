
import unittest
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from .. import WebGetRobust

class TestPlainCreation(unittest.TestCase):

	def test_plain_instantiation_1(self):
		wg = WebGetRobust()
		self.assertTrue(wg is not None)
	def test_plain_instantiation_2(self):
		wg = WebGetRobust(cloudflare=True)
		self.assertTrue(wg is not None)
	def test_plain_instantiation_3(self):
		wg = WebGetRobust(use_socks=True)
		self.assertTrue(wg is not None)



class MockServerRequestHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		# Process an HTTP GET request and return a response with an HTTP 200 status.
		print("Path: ", self.path)

		if self.path == "/":
			self.send_response(200)
			self.end_headers()
			self.wfile.write(b"Root OK?")

		elif self.path == "/html-decode":
			self.send_response(200)
			self.send_header('Content-type',"text/html")
			self.end_headers()
			self.wfile.write(b"Root OK?")




def get_free_port():
	s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
	s.bind(('localhost', 0))
	address, port = s.getsockname()
	s.close()
	return port


class TestSimpleFetch(unittest.TestCase):
	def setUp(self):

		# Configure mock server.
		self.mock_server_port = get_free_port()
		self.mock_server = HTTPServer(('localhost', self.mock_server_port), MockServerRequestHandler)

		# Start running mock server in a separate thread.
		# Daemon threads automatically shut down when the main process exits.
		self.mock_server_thread = Thread(target=self.mock_server.serve_forever)
		self.mock_server_thread.setDaemon(True)
		self.mock_server_thread.start()
		self.wg = WebGetRobust()
	def tearDown(self):
		self.mock_server.shutdown()

	def test_fetch_1(self):

		page = self.wg.getpage("http://localhost:{}".format(self.mock_server_port))
		self.assertEqual(page, b'Root OK?')

	def test_fetch_decode_1(self):
		# text/html content should be decoded automatically.
		page = self.wg.getpage("http://localhost:{}/html-decode".format(self.mock_server_port))
		self.assertEqual(page, 'Root OK?')
