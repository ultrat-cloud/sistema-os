from flask import render_template, request, redirect, session, url_for
from database import get_pg_conn, get_mysql_conn
import bcrypt
from psycopg2.extras import RealDictCursor

def init_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for('dashboard')) if 'user' in session else redirect(url_for('login'))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email")
            senha = request.form.get("senha").encode('utf-8')
            conn = get_pg_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM public.users WHERE email = %s AND ativo = TRUE", (email,))
            user = cur.fetchone()
            cur.close(); conn.close()
            if user and bcrypt.checkpw(senha, user['senha_hash'].encode('utf-8')):
                session['user'] = user['nome']
                return redirect(url_for('dashboard'))
            return "Acesso negado", 401
        return render_template("login.html")

    @app.route("/dashboard", methods=["GET", "POST"])
    def dashboard():
        if 'user' not in session: return redirect(url_for('login'))
        os_data, diagn_list = None, []
        if request.method == "POST":
            os_id = request.form.get("os_id")
            conn = get_mysql_conn()
            cur = conn.cursor(dictionary=True)
            # Busca OS principal
            cur.execute("SELECT id, id_assunto, status FROM su_oss_chamado WHERE id = %s", (os_id,))
            os_data = cur.fetchone()
            
            # Busca diagnósticos permitidos (Usando colunas reais: id, descricao)
            if os_data and os_data['status'] == 'F':
                cur.execute("""SELECT d.id, d.descricao 
                               FROM diagnostico_assunto da
                               JOIN su_diagnostico d ON d.id = da.id_diagnostico
                               WHERE da.id_assunto = %s AND da.ativo = 'S'""", (os_data['id_assunto'],))
                diagn_list = cur.fetchall()
            conn.close()
        return render_template("dashboard.html", os=os_data, diagn_list=diagn_list)

    @app.route("/update_os", methods=["POST"])
    def update_os():
        if 'user' not in session: return redirect(url_for('login'))
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute("UPDATE su_oss_chamado SET id_su_diagnostico = %s WHERE id = %s", 
                    (request.form.get("id_diagnostico"), request.form.get("os_id")))
        conn.commit(); conn.close()
        return "OS atualizada com sucesso! <a href='/dashboard'>Voltar</a>"
