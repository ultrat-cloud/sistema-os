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
                sql = """
                SELECT
                    CASE tabela_os.tipo
                        WHEN 'C' THEN tabela_cliente.id
                        WHEN 'E' THEN tabela_estrutura.id
                        ELSE NULL
                    END										AS id_cliente_estrutura,
                    tabela_os.id							AS id_os,
                    CASE tabela_os.tipo
                        WHEN 'C' THEN tabela_cliente.razao
                        WHEN 'E' THEN tabela_estrutura.descricao
                        ELSE NULL
                    END										AS cliente_estrutura,
                    CASE tabela_os.status
                        WHEN 'A'  THEN 'Aberta'
                        WHEN 'AN' THEN 'Análise'
                        WHEN 'EN' THEN 'Encaminhada'
                        WHEN 'AS' THEN 'Assumida'
                        WHEN 'AG' THEN 'Agendada'
                        WHEN 'DS' THEN 'Deslocamento'
                        WHEN 'EX' THEN 'Execução'
                        WHEN 'F'  THEN 'Finalizada'
                        WHEN 'RAG' THEN 'Aguardando Reagendamento'
                        ELSE NULL
                    END										AS status_os,
                    tabela_os.data_abertura,
                    tabela_os.data_agenda					AS data_agendamento_os,
                    tabela_os.data_fechamento,
                    tabela_os.mensagem						AS mensagem_abertura_os,
                    tabela_os.mensagem_resposta,
                    tabela_os.justificativa_sla_atrasado	AS mensagem_justificativa_os,
                    tabela_os.id_su_diagnostico,
                    tabela_diagnostico.descricao			AS diagnostico_os
                FROM
                	su_oss_chamado							AS tabela_os
                LEFT JOIN
                	cliente									AS tabela_cliente
                    	ON tabela_cliente.id = tabela_os.id_cliente
                LEFT JOIN
                	estrutura								AS tabela_estrutura
                    	ON tabela_estrutura.id = tabela_os.id_estrutura
                LEFT JOIN
                	su_oss_assunto							AS tabela_assunto
                    	ON tabela_assunto.id = tabela_os.id_assunto
                LEFT JOIN
                	su_diagnostico							AS tabela_diagnostico
                    	ON tabela_diagnostico.id = tabela_os.id_su_diagnostico
                WHERE
                    tabela_os.id = %s
                """
                cur.execute(sql, (os_id,))
                                os_data = cur.fetchone()
                                
                                if os_data:
                                    def fmt_date(d):
                                        return d.strftime('%d/%m/%Y %H:%M:%S') if d and hasattr(d, 'strftime') and d.year > 1900 else ""
                                    
                                    os_data['data_abertura'] = fmt_date(os_data['data_abertura'])
                                    os_data['data_agendamento_os'] = fmt_date(os_data['data_agendamento_os'])
                                    os_data['data_fechamento'] = fmt_date(os_data['data_fechamento'])
                                    
                                    # Padronização de mensagens
                                    msg_padrao = "Sem informações disponíveis."
                                    os_data['mensagem_abertura_os'] = os_data['mensagem_abertura_os'] or msg_padrao
                                    os_data['mensagem_resposta'] = os_data['mensagem_resposta'] or msg_padrao
                                    os_data['mensagem_justificativa_os'] = os_data['mensagem_justificativa_os'] or msg_padrao
                                    
                                    # CRÍTICO: Criamos o status_raw baseando-se no status retornado pelo SELECT
                                    os_data['status_raw'] = 'F' if os_data['status_os'] == 'Finalizada' else 'Outro'
                                    
                                    if os_data["status_raw"] == "F":
                                        cur.execute("SELECT id, descricao FROM su_diagnostico WHERE ativo = 'S'")
                                        diagn_list = cur.fetchall()
                                cur.close(); conn.close()
                            except Exception as e:
                                logging.error(f"Erro: {e}")
                                flash("Erro técnico: Dados inconsistentes.", "danger")
                        
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
