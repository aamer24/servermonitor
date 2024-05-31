import psutil
import pymongo
import datetime
import subprocess
import socket
import time


# MongoDB connection details
MONGO_URI = "mongodb://192.168.1.1:27017"
DATABASE_NAME = "server_monitoring"
COLLECTION_NAME = "server_stats"

def check_service_status_print(service_name):
  output=subprocess.call(["systemctl", "is-active","--quiet", service_name])
  print(output)

def check_service_status(service_name):
  try:
    output=subprocess.call(["systemctl", "is-active","--quiet", service_name])
    # Check if second element is "active" (running)
    if output == 0:
      return 1  # Service is running
    else:
      return 0  # Service is not running
  except subprocess.CalledProcessError:
    # Error occurred, return unknown status
    return "Unknown"



def get_server_info():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent

    # Define your list of services
    service_names = ["apache2", "mysql"]
    services = []
    for service_name in service_names:
      # Call function for each service and append to list
      services.append({"name": service_name, "value": check_service_status(service_name)})

    return {
        "hostname": hostname,
        "ip_address": ip_address,
        "cpu_usage": cpu_usage,
        "memory_usage": memory_usage,
        "disk_usage": disk_usage,
        "services": services,
        "timestamp": datetime.datetime.utcnow()
    }


def send_to_mongodb(data):
        try:
          client = pymongo.MongoClient(MONGO_URI)
          database = client[DATABASE_NAME]
          collection = database[COLLECTION_NAME]

          update_filter = {"hostname": data["hostname"]}  # Filter by hostname
          update_document = {"$set": data}                 # Update all fields

          # **Upsert**: Update or insert based on filter match
          update_result = collection.update_one(update_filter, update_document, upsert=True)
            
        except pymongo.errors.ConnectionFailure as e:
          print(f"Error connecting to MongoDB: {e}")
        except Exception as e:
          print(f"An unexpected error occurred: {e}")
        finally:
          client.close()

def send_to_mongodb_hist(data):
        try:
          client = pymongo.MongoClient(MONGO_URI)
          database = client[DATABASE_NAME]
          collection = database['server_stats_hist']
          update_result = collection.insert_one(data)

        except pymongo.errors.ConnectionFailure as e:
          print(f"Error connecting to MongoDB: {e}")
        except Exception as e:
          print(f"An unexpected error occurred: {e}")
        finally:
          client.close()

if __name__ == "__main__":
    while True:
        server_data = get_server_info()
        send_to_mongodb(server_data)
        send_to_mongodb_hist(server_data)
        # Replace 10 with your desired data collection interval in seconds
        time.sleep(10)
