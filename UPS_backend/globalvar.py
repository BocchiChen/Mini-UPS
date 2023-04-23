import database

def _init():
  global _global_conn
  _global_conn = database.connectToDB()

def getDBConn(defValue = None):
  try:
    return _global_conn
  except Exception as e:
    return defValue
