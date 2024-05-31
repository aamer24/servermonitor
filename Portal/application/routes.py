from application import *
import datetime

@app.route('/')
def home():

    hostnames = db['server_stats'].distinct('hostname')
    latest_data = {hostname: db['server_stats'].find_one({'hostname': hostname}, sort=[('timestamp', -1)]) for hostname in hostnames}
  
    return render_template('index.html', data=latest_data)

from flask import jsonify

@app.route("/dashboard")
def dashboard():
    # Retrieve server data (optional: filter by hostname or date range)
    hostname = request.args.get("hostname")
    start_date = request.args.get("start_date")  # Example format: YYYY-MM-DD
    end_date = request.args.get("end_date")

    server_data = get_server_data_hist(hostname, start_date, end_date)

    return render_template("dashboard.html", server_data=server_data)

def get_server_data(hostname=None, start_date=None, end_date=None):
  query = {}
  if hostname:
    query["hostname"] = hostname
  if start_date and end_date:
    # Convert start_date and end_date to timestamps for MongoDB query
    query["timestamp"] = {"$gte": bson.timestamp.from_datetime(start_date), "$lte": bson.timestamp.from_datetime(end_date)}

  # Fetch data from collection
  data = list(collection.find(query))

  # Handle ObjectIds (recommended approach)
  for item in data:
    # Assuming ObjectIds are stored in a property named '_id'
    item['_id'] = str(item['_id'])  # Convert ObjectId to string
    item['timestamp'] = item['timestamp'].isoformat()  # Convert to ISO format

  return data


def get_server_data_hist(hostname=None, start_date=None, end_date=None):
  query = {}
  if hostname:
    query["hostname"] = hostname
  if start_date and end_date:
    # Convert start_date and end_date to timestamps for MongoDB query
    query["timestamp"] = {"$gte": bson.timestamp.from_datetime(start_date), "$lte": bson.timestamp.from_datetime(end_date)}

  # Fetch data from collection
  data = list(hist_collection.find(query))

  # Handle ObjectIds (recommended approach)
  for item in data:
    # Assuming ObjectIds are stored in a property named '_id'
    item['_id'] = str(item['_id'])  # Convert ObjectId to string
    item['timestamp'] = item['timestamp'].isoformat()  # Convert to ISO format

  return data



@app.route('/data/<hostname>')
def data(hostname):
    latest_data = db['server_stats'].find_one({"hostname": hostname}, sort=[("timestamp", pymongo.DESCENDING)])
    if latest_data:
        latest_data["timestamp"] = latest_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    
    sent_emails_collection = db['sent_emails']

    def get_services_data():
        document = latest_data
        if document:
            return document.get('services', [])
        else:
            return []
        
    def get_previous_services_data():
        document = sent_emails_collection.find_one({"hostname": hostname}, sort=[("timestamp", pymongo.DESCENDING)])
        if document:
            return document.get('services', [])
        else:
            return []
    
    def format_status_report(data):
      report = f"Server Status Report\n"
      report += f"Hostname: {data['hostname']}\n"
      report += f"CPU Usage: {data['cpu_usage']}%\n"
      report += f"Disk Usage: {data['disk_usage']}%\n"
      report += f"IP Address: {data['ip_address']}\n"
      report += f"Memory Usage: {data['memory_usage']}%\n"
      report += f"Services:\n"
      for service in data['services']:
          status = "Up" if service['value'] == 1 else "Down"  # Translate value to Up/Down
          report += f"- {service['name']}: {status}\n"
      report += f"Timestamp: {data['timestamp']}\n"
      return report
    
    report_text = format_status_report(latest_data)
    previous_services=get_previous_services_data()
    services = get_services_data()
    if services != previous_services:
        
        msg = EmailMessage(f"Service Value Change Notification for '{hostname}'",report_text,"alghrybia@fastmail.com",["aamer.alghrybi@gmail.com"])
        msg.send()
            # Log sent email information in sent_emails collection
        sent_emails_collection.insert_one({
                'hostname': hostname,
                'services': services,  # Log the entire services list
                'timestamp': datetime.datetime.utcnow() # Add a timestamp for reference
            })
            

    return json_util.dumps(latest_data)


def update_data():
  pipeline = [
    {"$sort": {"timestamp": -1}},  # Sort by timestamp (descending)
    {"$group": {
      "_id": "$hostname",
      "documents": {"$push": "$$ROOT"}
    }},
    {"$project": {
      "_id": 0,
      "hostname": "$_id",
      "latest_docs": {"$slice": ["$documents", -10]}  # Limit to 10 latest per hostname
    }}
  ]

  # Get the latest documents grouped by hostname
  grouped_data = list(hist_collection.aggregate(pipeline))

  # No need to flatten data structure as we already have latest per hostname

  # Iterate through each group and delete excess documents
  for group in grouped_data:
    hostname = group["hostname"]
    latest_docs = group["latest_docs"]
    latest_doc_ids = [doc["_id"] for doc in latest_docs]

    # Filter to delete documents older than the latest 10 for this hostname
    delete_filter = {"hostname": hostname, "_id": {"$nin": latest_doc_ids}}
    hist_collection.delete_many(delete_filter)

sched.add_job(update_data, 'interval', minutes=1)
def trigger_update_job():
  update_data()


# Load Server Information
with open('servers.json') as f:  # Assuming servers.json holds the data
    server_data = json.load(f)
# Check if server_data is a dictionary and has the 'servers' key
if isinstance(server_data, dict) and 'servers' in server_data:
    servers = server_data['servers']  # Access the list using the key
else:
    print("Error: Invalid data format in servers.json")

# Sample allowed actions (replace with your specific actions)
ALLOWED_ACTIONS = {
  "get cpu usage": "wmic cpu get LoadPercentage /format:value",
  "get memory usage": "wmic OS get FreePhysicalMemory /format:value",
  "get ip": "ipconfig"
}

def connect_to_server(hostname):
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

  for server in servers:
    if server['hostname'].lower() == hostname.lower():  # Case-insensitive comparison
      client.connect(server['hostname'], username=server['username'], password=server['password'])
      return client

  # If no matching server found, raise an exception
  raise Exception(f"Server with hostname '{hostname}' not found")

def is_authenticated():

  return True

def handle_remote_command(command, client):
  try:
    stdin, stdout, stderr = client.exec_command(command)
    output = stdout.read().decode().strip()
    client.close()
    return output
  except Exception as e:
    return f"Error: {str(e)}"

def handle_request(action, args, client):
  if action not in ALLOWED_ACTIONS:
    return jsonify({"error": "Invalid action"}), 400

  command = ALLOWED_ACTIONS[action]
  output = handle_remote_command(command, client)
  return jsonify({"output": output})


def parse_message(message):
  # Extract hostname and command with a more flexible format
  words = message.lower().split()  # convert to lowercase for easier parsing
  if len(words) < 2:
    return None, None

  # Check if "on" is present anywhere in the message (not just at the beginning)
  server_index = words.index("on") if "on" in words else None
  if not server_index:
    return None, None  # No "on" found

  # Extract hostname and command based on the "on" index
  hostname = words[server_index + 1]
  command = " ".join(words[:server_index] + words[server_index+2:])
  return hostname, command

@socketio.on('chat message')
def handle_chat_message(data):
  if not is_authenticated():
    emit('chat message', "Unauthorized access. Please authenticate first.")
    return

  hostname, command = parse_message(data)
  if not hostname or not command:
    emit('chat message', "Invalid command format. Please specify hostname and command.")
    return

  try:
    client = connect_to_server(hostname)
    response = handle_request(command, {}, client)
    if response.status_code != 200:
      emit('chat message', "Error: " + response.json['error'])
      return

    output = response.json['output']
    emit('chat message', f"Server {hostname} response: {output}")
  except Exception as e:
    emit('chat message', f"Error: {str(e)}")
    return


