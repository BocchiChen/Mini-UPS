import psycopg2
import threading

mutex = threading.Lock()

#connect to the database
def connectToDB():
  try:
    conn = psycopg2.connect
    (
    host = '',
    port = 5432,
    database = 'postgres',
    user = 'postgres',
    password = 'postgres',
    charset = 'utf8'
    )
    return conn
  except Exception as e:
    print("Error occurs while connecting the database: ", e)
    
def clearDB(conn):
  try:
    cur = conn.cursor()
    cur.execute("DELETE FROM TRUCKS;")
    cur.execute("DELETE FROM PACKAGES;")
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

