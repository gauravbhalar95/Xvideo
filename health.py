from flask import Flask

# Create a Flask application instance
app = Flask(__name__)

# Define a health check route
@app.route('/health', methods=['GET'])
def health_check():
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)  # Run the app on port 8000
