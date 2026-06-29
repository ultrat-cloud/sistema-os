from flask import render_template, request, redirect, session, url_for
from database import get_pg_conn, get_mysql_conn
import bcrypt
from psycopg2.extras import RealDictCursor

def init_routes(app):
    
    # Rota raiz: Redireciona automaticamente para o login ou dashboard
    @app.route("/")
    def index():
        if 'user' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email")
            senha_raw = request.form.get("senha")
            
            if not email or not senha_raw:
                return "Preencha todos os campos", 400
                
            senha = senha_raw.encode('utf-8')
            
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
        if 'user' not in session: 
            return redirect(url_for('login'))
            
        os_data, diagn_list = None, []
        if request.method == "POST":
            os_id = request.form.get("os_id")
            if os_id:
                conn = get_mysql_conn()
                cur = conn.cursor(dictionary=True)
                
                # Busca dados do Zabbix (MySQL)
                query_os = """
                    SELECT su_oss_chamado.*, su_oss_assunto.assunto 
                    FROM su_oss_chamado 
                    LEFT JOIN su_oss_assunto ON su_oss_assunto.id = su_oss_chamado.id_assunto 
                    WHERE su_oss_chamado.id = %s
                """
                cur.execute(query_os, (os_id,))
                os_data = cur.fetchone()
                
                # Se finalizada, busca diagnósticos permitidos
                if os_data and os_data['status'] == 'F':
                    cur.execute("SELECT id_diagnostico FROM diagnostico_assunto WHERE id_assunto = %s AND ativo = 'S'", (os_data['id_assunto'],))
                    diagn_list = cur.fetchall()
                conn.close()
        
        return render_template("dashboard.html", os=os_data, diagn_list=diagn_list)

    @app.route("/update_os", methods=["POST"])
    def update_os():
        if 'user' not in session: 
            return redirect(url_for('login'))
        
        os_id = request.form.get("os_id")
        diag_id = request.form.get("id_diagnostico")
        
        if not os_id or not diag_id:
            return "Erro: Identificador de OS ou Diagnóstico ausente.", 400
            
        conn = get_mysql_conn()
        cur = conn.cursor()
        cur.execute("UPDATE su_oss_chamado SET id_su_diagnostico = %s WHERE id = %s", (diag_id, os_id))
        conn.commit()
        cur.close()
        conn.close()
        
        return "OS atualizada com sucesso! <a href='/dashboard'>Voltar ao Dashboard</a>"
