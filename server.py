from flask import Flask, request
from featurization import FeaturizationThread
import urllib
import os
import json

server = Flask(__name__)

current_thread = None


def service_is_busy():
    global current_thread
    if current_thread is None:
        return False

    return current_thread.is_alive()


def get_current_status():
    return "busy" if service_is_busy() else "available"


@server.route('/status')
def status():
    response = {'status': get_current_status()}
    return json.dumps(response)


def get_params_from_request(request_query_string):
    query_string = request_query_string.decode("utf-8")
    query_string = urllib.parse.unquote(query_string)
    parsed_query = urllib.parse.parse_qs(query_string)
    directory = parsed_query['directory'][0]
    biased_tiles = parsed_query['biased_tiles'][0]
    return directory, biased_tiles


@server.route('/featurize')
def featurize():
    print ('robosat featurize!!!' , flush=True)
    if service_is_busy():
        response = {'status': get_current_status()}
        return json.dumps(response), 503
    source_images_directory , biased_tiles_directory = get_params_from_request(request.query_string)
    print ('{} {}'.format(source_images_directory, biased_tiles_directory), flush=True)
    global current_thread
    current_thread = FeaturizationThread(source_images_directory, biased_tiles_directory)
    current_thread.start()
    response = {'status': get_current_status()}
    return json.dumps(response), 200


def main():
    global server
    server.run(host=os.environ['FLASK_RUN_HOST'],
               port=os.environ['FLASK_RUN_PORT'], debug=True)
    print('Robosat server is started...')


if __name__ == '__main__':
    main()
