from resticweb.app_generator import create_app

def main():
    app = create_app()
    # app.run(debug=True, use_reloader=False)
    app.run(debug=True, host='0.0.0.0', port='8080')