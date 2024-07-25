from flask import Flask, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from logging.handlers import RotatingFileHandler
import logging
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from flask_login import LoginManager, current_user
from urllib.parse import urlparse

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    # Регистрация blueprint'ов
    from app.routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    from app.partner import bp as partner_bp
    app.register_blueprint(partner_bp)

    from app.admin.routes import bp as admin_bp
    app.register_blueprint(admin_bp)

    # Настройка логирования
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/sarafan.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Sarafan startup')

    # Инициализация Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'partner.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User  # Импортируем User здесь, чтобы избежать циклического импорта
        return User.query.get(int(user_id))

    def get_login_view(request):
        """Определяет маршрут входа в зависимости от запрошенного URL."""
        path = urlparse(request.url).path
        if path.startswith('/admin/'):
            return 'admin.login'
        elif path.startswith('/partner/'):
            return 'partner.login'
        else:
            # По умолчанию перенаправляем на вход для партнеров
            return 'partner.login'

    @login_manager.unauthorized_handler
    def unauthorized():
        """Перенаправляет неавторизованных пользователей на нужную страницу входа."""
        return redirect(url_for(get_login_view(request), next=request.path))

    return app

# Инициализация Google Sheets API
credentials = Credentials.from_service_account_file(
    os.environ.get("SERVICE_ACCOUNT_FILE"),
    scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
)
service = build('sheets', 'v4', credentials=credentials)