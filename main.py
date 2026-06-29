import os
from flask import Flask
from routes import init_routes
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

app = Flask(__name__)

# Usa a chave que definimos no arquivo .env para maior segurança
app.secret_key = os.getenv('FLASK_SECRET_KEY')

init_routes(app)

if __name__ == "__main__":
    # Mantém na porta 5000 interna do container
    app.run(host="0.0.0.0", port=5000)
