from flask import render_template, request, redirect, session, url_for, flash
from database import get_pg_conn, get_mysql_conn
import bcrypt
from psycopg2.extras import RealDictCursor

def init_routes(app):
    @app.route("/")
    def index():
        return redirect(url_for('dashboard')) if 'user' in session else redirect(url_for('login'))

    @app.route("/login", methods=["GET","POST"])
    def login():
        if request.method=="POST":
            email=request.form.get("email")
            senha=request.form.get("senha").encode("utf-8")
            conn=get_pg_conn()
            cur=conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT * FROM public.users WHERE email=%s AND ativo=TRUE",(email,))
            user=cur.fetchone()
            cur.close(); conn.close()
            if user and bcrypt.checkpw(senha,user["senha_hash"].encode("utf-8")):
                session["user"]=user["nome"]
                return redirect(url_for("dashboard"))
            flash("Acesso negado.","danger")
        return render_template("login.html")

    @app.route("/dashboard", methods=["GET","POST"])
    def dashboard():
        if "user" not in session:
            return redirect(url_for("login"))
        os_data=None
        diagn_list=[]
        os_id=request.values.get("os_id")
        if os_id:
            conn=get_mysql_conn()
            cur=conn.cursor(dictionary=True)
            cur.execute("""SELECT t.id,
            CASE t.status WHEN 'A' THEN 'Aberta' WHEN 'AN' THEN 'Análise' WHEN 'EN' THEN 'Encaminhada'
            WHEN 'AS' THEN 'Assumida' WHEN 'AG' THEN 'Agendada' WHEN 'DS' THEN 'Deslocamento'
            WHEN 'EX' THEN 'Execução' WHEN 'F' THEN 'Finalizada' WHEN 'RAG' THEN 'Aguardando Reagendamento'
            ELSE 'Outro' END status_formatado,
            t.status status_raw,t.data_abertura,t.data_agenda,t.data_fechamento,
            t.mensagem mensagem_abertura,t.mensagem_resposta,
            t.justificativa_sla_atrasado mensagem_justificativa,
            t.id_su_diagnostico,d.descricao diagnostico
            FROM su_oss_chamado t
            LEFT JOIN su_diagnostico d ON d.id=t.id_su_diagnostico
            WHERE t.id=%s""",(os_id,))
            os_data=cur.fetchone()
            if os_data and os_data["status_raw"]=="F":
                cur.execute("SELECT id,descricao FROM su_diagnostico WHERE ativo='S'")
                diagn_list=cur.fetchall()
            cur.close(); conn.close()
        return render_template("dashboard.html",os=os_data,diagn_list=diagn_list)

    @app.route("/update_os", methods=["POST"])
    def update_os():
        if "user" not in session:
            return redirect(url_for("login"))
        os_id=request.form.get("os_id")
        novo=request.form.get("id_diagnostico")
        conn=get_mysql_conn()
        cur=conn.cursor()
        try:
            cur.execute("UPDATE su_oss_chamado SET id_su_diagnostico=%s WHERE id=%s",(novo,os_id))
            conn.commit()
            if cur.rowcount:
                flash("Diagnóstico atualizado com sucesso!","success")
            else:
                flash("Nenhuma OS encontrada.","warning")
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao salvar diagnóstico: {e}","danger")
        finally:
            cur.close(); conn.close()
        return redirect(url_for("dashboard",os_id=os_id))
