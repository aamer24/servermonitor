import win32serviceutil
import win32service
import win32event
import servicemanager
import socket


class AppServerSvc (win32serviceutil.ServiceFramework):
  _svc_name_ = "AamerServerMonitor"
  _svc_display_name_ = "Aamer's Server Monitor"

  def __init__(self, args):
    win32serviceutil.ServiceFramework.__init__(self, args)
    self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
    socket.setdefaulttimeout(60)

  def SvcStop(self):
    self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
    win32event.SetEvent(self.hWaitStop)

  def SvcDoRun(self):
    servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                          servicemanager.PYS_SERVICE_STARTED,
                          (self._svc_name_, ''))
    while True:
      
      import psutil
      import socket
      import pymongo
      import datetime
      from win32serviceutil import QueryServiceStatus

      #MongoDB connection details
      MONGO_URI = "mongodb://192.168.1.1:27017"
      DATABASE_NAME = "server_monitoring"
      COLLECTION_NAME = "server_stats"

      def get_server_info():
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        cpu_usage = psutil.cpu_percent(interval=1)  # Get CPU usage over 1 second interval
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent  # Adjust path if needed

        def get_service(name):
          service = None
          try:
            service = psutil.win_service_get(name)
            service = service.as_dict()
          except Exception as ex:
            print(str(ex))
          return service

        services = []
        try:

          # List of services to check
          service_names = ['AxInstSV', 'AnyDesk']

          for service_name in service_names:
              # Check service status
              service = get_service(service_name)
              if service and service['status'] == 'running':
                  services.append({"name": service_name, "value": 1})
              else:
                  services.append({"name": service_name, "value": 0})
        except Exception as e:
          print(f"Error checking service: {e}")
          services.append({"name": service_name, "value": -1})  # Indicate error


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

          if update_result.matched_count > 0:
            print(f"Server stats for hostname '{data['hostname']}' successfully updated.")
          else:
            print(f"Server stats for hostname '{data['hostname']}' inserted.")
            
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

          if update_result.matched_count > 0:
            print(f"Server stats for hostname '{data['hostname']}' successfully updated.")
          else:
            print(f"Server stats for hostname '{data['hostname']}' inserted.")
            
        except pymongo.errors.ConnectionFailure as e:
          print(f"Error connecting to MongoDB: {e}")
        except Exception as e:
          print(f"An unexpected error occurred: {e}")
        finally:
          client.close()

      server_data = get_server_info()
      send_to_mongodb(server_data)
      send_to_mongodb_hist(server_data)

      # data collection cycle every 10 seconds
      if not win32event.WaitForSingleObject(self.hWaitStop, 10 * 1000):
        break  # Break out of loop if service is stopped

if __name__ == '__main__':
  win32serviceutil.HandleCommandLine(AppServerSvc)
