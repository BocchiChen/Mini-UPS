import psycopg2
import threading

#connect to the database
def connectToDB():
  try:
    conn = psycopg2.connect(
    host = 'db',
    port = 5432,
    database = 'postgres',
    user = 'postgres',
    password = 'passw0rd'
    )
    return conn
  except Exception as e:
    print("Error occurs while connecting the database: ", e)
    
def clearDB(conn):
  try:
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

