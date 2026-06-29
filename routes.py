from flask import render_template, request, redirect, session, url_for, url_for, flash
from database import get_pg_conn, get_mysql_conn
import bcrypt
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(
    filename="erros_os.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def init_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for('dashboard')) if 'user' in session else redirect(url_for('login'))

    @app.route("/login", methods=["GET","POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email")
            senha = request.form.get("senha").encode("utf-8")
            try:
                conn = get_pg_conn()
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM public.users WHERE email=%s AND ativo=TRUE", (email,))
                user = cur.fetchone()
                cur.close(); conn.close()

                if user and bcrypt.checkpw(senha, user["senha_hash"].encode("utf-8")):
                    session["user"] = user["nome"]
                    return redirect(url_for("dashboard"))
                flash("Acesso negado.", "danger")
            except Exception as e:
                logging.error(f"Erro no login: {e}")
                flash("Erro na conexão com banco de autenticação.", "danger")
        return render_template("login.html")

    @app.route("/dashboard", methods=["GET","POST"])
        def dashboard(): # <-- Removi o recuo excessivo aqui
            if "user" not in session: return redirect(url_for('login'))
            
            os_data = None; diagn_list = []
            os_id = request.form.get("os_id")
            
            print(f"DEBUG: Buscando ID: {os_id}")
            
            if os_id:
                try:
                    conn = get_mysql_conn()
                    cur = conn.cursor(dictionary=True)
                    sql = """SELECT t.id, c.id AS id_cliente, c.razao AS cliente, 
                             CASE t.status WHEN 'F' THEN 'Finalizada' ELSE 'Outro' END as status_formatado,
                             t.status as status_raw, 
                             DATE_FORMAT(t.data_abertura, '%d/%m/%Y %H:%i:%s') AS data_abertura,
                             DATE_FORMAT(t.data_agenda, '%d/%m/%Y %H:%i:%s') AS data_agendamento,
                             DATE_FORMAT(t.data_fechamento, '%d/%m/%Y %H:%i:%s') AS data_finalizacao,
                             t.mensagem AS mensagem_abertura, t.mensagem_resposta, t.justificativa_sla_atrasado AS mensagem_justificativa,
                             t.id_su_diagnostico, d.descricao AS diagnostico
                             FROM su_oss_chamado t 
                             LEFT JOIN cliente c ON c.id = t.id_cliente
                             LEFT JOIN su_diagnostico d ON d.id = t.id_su_diagnostico
                             WHERE t.id = %s"""
                    cur.execute(sql, (os_id,))
                    os_data = cur.fetchone()
                    
                    if os_data and os_data["status_raw"] == "F":
                        cur.execute("SELECT id, descricao FROM su_diagnostico WHERE ativo = 'S'")
                        diagn_list = cur.fetchall()
                    cur.close(); conn.close()
                except Exception as e:
                    logging.error(f"Erro: {e}")
            return render_template("dashboard.html", os=os_data, diagn_list=diagn_list)
    
    @app.route("/update_os", methods=["POST"])
    def update_os():
        if "user" not in session: return redirect(url_for("login"))
        os_id = request.form.get("os_id")
        novo = request.form.get("id_diagnostico")
        conn = get_mysql_conn()
        cur = conn.cursor()
        try:
            cur.execute("UPDATE su_oss_chamado SET id_su_diagnostico=%s WHERE id=%s", (novo, os_id))
            conn.commit()
            flash("Atualizado com sucesso!", "success")
        except Exception as e:
            conn.rollback()
            logging.error(f"Erro ao atualizar OS {os_id}: {e}")
            flash("Erro ao salvar dados.", "danger")
        finally:
            cur.close(); conn.close()
        return redirect(url_for("dashboard"))
