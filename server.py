from flask import Flask, request
from featurization import FeaturizationThread
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


@server.route('/featurize')
def featurize():
    print ('robosat featurize!!!' , flush=True)
    if service_is_busy():
        response = {'status': get_current_status()}
        return json.dumps(response), 503
    source_images_directory = request.args.get('directory')
    biased_tiles_directory = request.args.get('biased_tiles')
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
