import psycopg2
import threading

dbconn = None
lock = threading.Lock()

#connect to the database
def connectToDB():
  global dbconn
  try:
    conn = psycopg2.connect
    (
    database = 'postgres',
    user = 'postgres',
    password = 'postgres',
    host = '',
    port = '5432'
    )
    dbconn = conn
    return conn
  except Exception as e:
    print("Error occurs while connecting the database: ", e)
    
def clearDB():
  global dbconn
  cursor = dbconn.cursor()
  cursor.execute("DELETE FROM TRUCKS;")
  cursor.execute("DELETE FROM PACKAGES;")
  dbconn.commit()
  cursor.close()

def closeConnections():
  global dbconn
  dbconn.close()

def executeQuery(query):
  global dbconn
  lock.acquire()
  cursor = dbconn.cursor()
  cursor.execute(query)
  cursor.close()
  lock.release()
