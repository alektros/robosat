from flask import Flask, request
import os
server = Flask(__name__)

@server.route('/status')
def status():
    return 'STATUS2', 200

def main():
    global server
    server.run(host=os.environ['FLASK_RUN_HOST'],
               port=os.environ['FLASK_RUN_PORT'], debug=True)
    print('Robosat server is started...')


if __name__ == '__main__':
    main()