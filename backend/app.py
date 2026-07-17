"""Entry point de la aplicacion Flask - application factory."""

# pyrefly: ignore [missing-import]
from flask import Flask, jsonify

from config import get_config
from logging_config import configure_logging
from routes.review import review_bp


def create_app():
    configure_logging()

    app = Flask(__name__)
    app.config.from_object(get_config())

    app.register_blueprint(review_bp)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Recurso no encontrado."}), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "Error interno del servidor."}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    # use_reloader=False: con el reloader activo, Werkzeug corre el pipeline en un
    # proceso hijo separado en Windows, y los logs de services/llm_connector.py
    # no llegan a la terminal donde se ejecuto "python app.py".
    app.run(debug=app.config["DEBUG"], use_reloader=False)
