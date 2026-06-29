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
            
            # Query completa incluindo campos técnicos conforme a estrutura da tabela
            cur.execute("""
                SELECT 
                    t.id, 
                    CASE t.status 
                        WHEN 'A' THEN 'Aberta' WHEN 'AN' THEN 'Análise' WHEN 'EN' THEN 'Encaminhada'
                        WHEN 'AS' THEN 'Assumida' WHEN 'AG' THEN 'Agendada' WHEN 'DS' THEN 'Deslocamento'
                        WHEN 'EX' THEN 'Execução' WHEN 'F' THEN 'Finalizada' WHEN 'RAG' THEN 'Aguardando Reagendamento'
                        ELSE 'Outro'
                    END AS status_formatado,
                    t.status AS status_raw,
                    t.data_abertura, t.data_agenda, t.data_fechamento,
                    t.mensagem AS mensagem_abertura, 
                    t.mensagem_resposta,
                    t.justificativa_sla_atrasado AS mensagem_justificativa,
                    t.id_su_diagnostico,
                    d.descricao AS diagnostico
                FROM su_oss_chamado AS t
                LEFT JOIN su_diagnostico AS d ON d.id = t.id_su_diagnostico
                WHERE t.id = %s
            """, (os_id,))
            os_data = cur.fetchone()
            
            if os_data and os_data['status_raw'] == 'F':
                cur.execute("SELECT id, descricao FROM su_diagnostico WHERE ativo = 'S'")
                diagn_list = cur.fetchall()
            conn.close()
        return render_template("dashboard.html", os=os_data, diagn_list=diagn_list)

    @app.route("/update_os", methods=["POST"])
    def update_os():
        # 1. Verifica autenticação
        if 'user' not in session: 
            return redirect(url_for('login'))
        
        # 2. Captura os dados do formulário
        os_id = request.form.get("os_id")
        novo_diagnostico = request.form.get("id_diagnostico")
        
        # 3. Executa a atualização no banco
        conn = get_mysql_conn()
        cur = conn.cursor()
        try:
            # A coluna no banco é 'id_su_diagnostico' conforme seu DESCRIBE
            sql = "UPDATE su_oss_chamado SET id_su_diagnostico = %s WHERE id = %s"
            cur.execute(sql, (novo_diagnostico, os_id))
            conn.commit()
        except Exception as e:
            print(f"Erro ao salvar diagnóstico: {e}")
        finally:
            cur.close()
            conn.close()
            
        # 4. Retorna para o dashboard (ou para a mesma OS)
        return redirect(url_for('dashboard'))
