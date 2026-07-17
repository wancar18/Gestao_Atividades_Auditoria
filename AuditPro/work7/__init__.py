import pymysql

# PyMySQL é puro Python, então o Railway não precisa compilar nenhuma
# biblioteca C para conseguir falar com o MySQL.
pymysql.install_as_MySQLdb()
