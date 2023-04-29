import psycopg2
import threading

mutex = threading.Lock()

#connect to the database
def connectToDB():
  try:
    print('before dbcon create')
    conn = psycopg2.connect(
    host = 'localhost',
    port = 5432,
    database = 'postgres',
    user = 'postgres',
    password = 'passw0rd'
    )
    print('after dbcon create')
    return conn
  except Exception as e:
    print("Error occurs while connecting the database: ", e)
    
def clearDB(conn):
  try:
    print('inclearDB')
    cur = conn.cursor()
    cur.execute("truncate table evaluations CASCADE;")
    cur.execute("truncate table packages CASCADE;")
    cur.execute("truncate table upsaccount CASCADE;")
    cur.execute("truncate table trucks CASCADE;")
    conn.commit()
    cur.close()
  except Exception as e:
    print(e)

def commitAndClose(conn, cur):
  try:
    conn.commit()
    cur.close()
    conn.close()
  except Exception as e:
    print(e)

