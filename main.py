import os
import logging
from flask import Flask, redirect, url_for, flash
from routes import init_routes
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Tratador de erro global para capturar falhas e não exibir a página técnica
@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Erro 500 no servidor: {error}")
    flash("Ocorreu um erro interno. Tente novamente mais tarde.", "danger")
    return redirect(url_for("dashboard"))

init_routes(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
