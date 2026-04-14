from dotenv import load_dotenv
import os
import hashlib
import MySQLdb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'))

db_host = os.getenv('DB_HOST')
db_port = int(os.getenv('DB_PORT', '3306'))
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')

if not all([db_host, db_user, db_password, db_name]):
    raise SystemExit('Missing DB env configuration')

conn = MySQLdb.connect(host=db_host, port=db_port, user=db_user, passwd=db_password, db=db_name, charset='utf8mb4')
cur = conn.cursor()
cur.execute('SELECT id, username FROM core_user WHERE role=%s', ('SELLER',))
rows = cur.fetchall()
print('SELLERS:', rows)
if not rows:
    raise SystemExit('No seller user found')

password = '921967'
salt = os.urandom(12)
iterations = 260000
hash_bytes = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations)
hash_string = f'pbkdf2_sha256${iterations}${salt.hex()}${hash_bytes.hex()}'

cur.execute('UPDATE core_user SET password=%s WHERE role=%s', (hash_string, 'SELLER'))
conn.commit()
print('UPDATED rows:', cur.rowcount)
cur.execute('SELECT id, username, password, CHAR_LENGTH(password) FROM core_user WHERE role=%s', ('SELLER',))
print('AFTER:', cur.fetchall())
conn.close()
