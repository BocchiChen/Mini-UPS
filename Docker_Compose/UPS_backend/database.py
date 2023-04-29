import psycopg2
import threading

mutex = threading.Lock()

#connect to the database
def connectToDB():
  try:
    print('before dbcon create')
    conn = psycopg2.connect(
    host = 'db',
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
    cur = conn.cursor()
    cur.execute("DELETE FROM upsaccount;")
    cur.execute("DELETE FROM trucks;")
    cur.execute("DELETE FROM packages;")
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

