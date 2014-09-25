#!/usr/bin/env python
"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

from resource_management import *
import socket
import sys
import time

def hive_service(
    name,
    action='start'):

  import params

  if name == 'metastore':
    pid_file = format("{hive_pid_dir}/{hive_metastore_pid}")
    cmd = format(
      "env HADOOP_HOME={hadoop_home} JAVA_HOME={java64_home} {start_metastore_path} {hive_log_dir}/hive.out {hive_log_dir}/hive.log {pid_file} {hive_server_conf_dir} {hive_log_dir}")
  elif name == 'hiveserver2':
    pid_file = format("{hive_pid_dir}/{hive_pid}")
    cmd = format(
      "env JAVA_HOME={java64_home} {start_hiveserver2_path} {hive_log_dir}/hive-server2.out {hive_log_dir}/hive-server2.log {pid_file} {hive_server_conf_dir} {hive_log_dir}")

  process_id_exists = format("ls {pid_file} >/dev/null 2>&1 && ps `cat {pid_file}` >/dev/null 2>&1")
  
  if action == 'start':
    demon_cmd = format("{cmd}")
    
    Execute(demon_cmd,
            user=params.hive_user,
            not_if=process_id_exists
    )

    if params.hive_jdbc_driver == "com.mysql.jdbc.Driver" or \
       params.hive_jdbc_driver == "org.postgresql.Driver" or \
       params.hive_jdbc_driver == "oracle.jdbc.driver.OracleDriver":
      
      db_connection_check_command = format(
        "{java64_home}/bin/java -cp {check_db_connection_jar}:/usr/share/java/{jdbc_jar_name} org.apache.ambari.server.DBConnectionVerification '{hive_jdbc_connection_url}' {hive_metastore_user_name} {hive_metastore_user_passwd!p} {hive_jdbc_driver}")
      
      Execute(db_connection_check_command,
              path='/usr/sbin:/sbin:/usr/local/bin:/bin:/usr/bin', tries=5, try_sleep=10)
      
    # AMBARI-5800 - wait for the server to come up instead of just the PID existance
    if name == 'hiveserver2':
      SOCKET_WAIT_SECONDS = 120
      address=params.hive_server_host
      port=int(params.hive_server_port)
      
      start_time = time.time()
      end_time = start_time + SOCKET_WAIT_SECONDS
      
      s = socket.socket()
      s.settimeout(5)
            
      is_service_socket_valid = False
      print "Waiting for the Hive server to start..."
      try:
        while time.time() < end_time:
          try:
            s.connect((address, port))
            s.send("A001 AUTHENTICATE ANONYMOUS")
            is_service_socket_valid = True
            break
          except socket.error, e:          
            time.sleep(5)
      finally:
        s.close()
      
      elapsed_time = time.time() - start_time    
      
      if is_service_socket_valid == False: 
        raise Fail("Connection to Hive server %s on port %s failed after %d seconds" % (address, port, elapsed_time))
      
      print "Successfully connected to Hive at %s on port %s after %d seconds" % (address, port, elapsed_time)    
            
  elif action == 'stop':
    demon_cmd = format("kill `cat {pid_file}` >/dev/null 2>&1 && rm -f {pid_file}")
    Execute(demon_cmd,
            not_if = format("! ({process_id_exists})")
    )
