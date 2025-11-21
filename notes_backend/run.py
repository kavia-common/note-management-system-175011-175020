from app import create_app

app = create_app()

if __name__ == "__main__":
    # Host/port can be controlled by environment in deployment; this is simple dev server
    app.run()
