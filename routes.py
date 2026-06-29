from flask import render_template, request, redirect, session, url_for, flash
from database import get_pg_conn, get_mysql_conn
import bcrypt
from psycopg2.extras import RealDictCursor
import logging

# Configuração de logs
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
    def dashboard():
        if "user" not in session: return redirect(url_for('login'))
        
        os_data = None; diagn_list = []
        os_id = request.values.get("os_id")
        
        if os_id:
            try:
                conn = get_mysql_conn()
                cur = conn.cursor(dictionary=True)
                sql = """SELECT t.id, c.id AS id_cliente, c.razao AS cliente, 
                         CASE t.status WHEN 'F' THEN 'Finalizada' ELSE 'Outro' END as status_formatado,
                         t.status as status_raw, 
                         t.data_abertura, t.data_agenda, t.data_fechamento,
                         t.mensagem AS mensagem_abertura, 
                         t.mensagem_resposta, 
                         t.justificativa_sla_atrasado AS mensagem_justificativa,
                         t.id_su_diagnostico, 
                         d.descricao AS diagnostico
                         FROM su_oss_chamado t 
                         LEFT JOIN cliente c ON c.id = t.id_cliente
                         LEFT JOIN su_diagnostico d ON d.id = t.id_su_diagnostico
                         WHERE t.id = %s"""
                cur.execute(sql, (os_id,))
                os_data = cur.fetchone()
                
                # Tratamento de dados (Blindagem)
                if os_data:
                    # Função para formatar datas: retorna vazio se não for data válida ou se for data "zero"
                    def fmt_date(d):
                        if d and hasattr(d, 'strftime') and d.year > 1900:
                            return d.strftime('%d/%m/%Y %H:%M:%S')
                        return ""
                    
                    os_data['data_abertura'] = fmt_date(os_data['data_abertura'])
                    os_data['data_agendamento'] = fmt_date(os_data['data_agenda'])
                    os_data['data_finalizacao'] = fmt_date(os_data['data_fechamento'])
                    
                    # Trata campos de texto para evitar 'None'
                    os_data['mensagem_abertura'] = os_data['mensagem_abertura'] if os_data['mensagem_abertura'] else "Sem mensagem."
                    os_data['mensagem_resposta'] = os_data['mensagem_resposta'] if os_data['mensagem_resposta'] else "Sem resposta."
                    os_data['mensagem_justificativa'] = os_data['mensagem_justificativa'] if os_data['mensagem_justificativa'] else "Nenhuma."
                
                # Carregar diagnósticos apenas se for OS finalizada
                if os_data and os_data["status_raw"] == "F":
                    cur.execute("SELECT id, descricao FROM su_diagnostico WHERE ativo = 'S'")
                    diagn_list = cur.fetchall()
                cur.close(); conn.close()
            except Exception as e:
                logging.error(f"Erro ao processar ID {os_id}: {str(e)}")
                flash("Erro técnico: Esta OS possui dados inconsistentes.", "danger")
                
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
            flash("Erro ao salvar dados no banco.", "danger")
        finally:
            cur.close(); conn.close()
        return redirect(url_for("dashboard"))
