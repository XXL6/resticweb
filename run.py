from resticweb.app_generator import create_app

if __name__ == "__main__":
    app = create_app()
    # app.run(debug=True, use_reloader=False)
    app.run(debug=False, host='0.0.0.0', port='8080')