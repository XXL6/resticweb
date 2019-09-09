from .app_generator import create_app

def main():
    app = create_app()
    app.run(debug=False, host='0.0.0.0', port='8080')