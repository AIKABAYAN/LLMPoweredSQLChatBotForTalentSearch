import os  
import datetime as dt  
  
def ensure_logs_dir():  
    os.makedirs("logs", exist_ok=True)  
  
def append_sql_log(header, queries):  
    ensure_logs_dir()  
    with open("logs/sql_queries.txt", "a", encoding="utf-8") as f:  
        f.write(f"-- {dt.datetime.now().isoformat()}\n")  
        f.write(header + "\n")  
        for q in queries:  
            f.write(q + "\n")  
        f.write("\n") 
