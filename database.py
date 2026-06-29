import psycopg2, mysql.connector
import os

# Conexão com o Banco de Usuários (PostgreSQL / Zabbix)
def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST_ZABBIX"),
        database=os.getenv("DB_NOME_ZABBIX"),
        user=os.getenv("DB_USUARIO_ZABBIX"),
        password=os.getenv("DB_SENHA_ZABBIX"),
        port=os.getenv("DB_PORTA_ZABBIX")
    )

# Conexão com o Banco de OS (MySQL / IXC)
def get_mysql_conn():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST_IXC_PROVEDOR"),
        database=os.getenv("DB_NOME_IXC_PROVEDOR"),
        user=os.getenv("DB_USUARIO_IXC_PROVEDOR"),
        password=os.getenv("DB_SENHA_IXC_PROVEDOR"),
        port=os.getenv("DB_PORTA_IXC_PROVEDOR")
    )
