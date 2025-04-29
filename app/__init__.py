from flask import Flask 
from flask_session import Session
from .extensions import celery_init_app
from .routes import main
import os
def create_app():
    app = Flask(__name__)
    app.config["SESSION_TYPE"] ="filesystem"
    Session(app)
   
    app.config['SECRET_KEY'] = os.urandom(64)
    app.config.from_mapping(
        CELERY=dict(
            broker_url="amqp://guest:guest@localhost:5672",
            result_backend="db+sqlite:///db.sqlite3",
        ),
    )
    app.register_blueprint(main)

    celery_init_app(app)

    return app
