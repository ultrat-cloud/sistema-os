import os
import logging
from datetime import timedelta
from flask import Flask, redirect, url_for, flash
from routes import init_routes
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# --- CONFIGURAÇÕES PROFISSIONAIS DE SESSÃO ---
# Define que a sessão expira após 2 horas de inatividade total
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
# Protege o cookie contra acessos via scripts (XSS)
app.config['SESSION_COOKIE_HTTPONLY'] = True
# Se estiver em HTTPS, descomente a linha abaixo:
# app.config['SESSION_COOKIE_SECURE'] = True 

# Tratador de erro global
@app.errorhandler(500)
def internal_error(error):
    logging.error(f"Erro 500 no servidor: {error}")
    flash("Ocorreu um erro interno. Tente novamente mais tarde.", "danger")
    return redirect(url_for("dashboard"))

init_routes(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
