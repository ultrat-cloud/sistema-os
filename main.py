from flask import Flask
from routes import init_routes
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

init_routes(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
