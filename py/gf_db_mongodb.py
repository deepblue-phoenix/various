#README - utility functions for working with the mongodb server


import sys,os
import pymongo
#----------------------------------------------
#ADD!! - figure out a smarter way to pick the right hostport from p_host_port_lst,
#        instead of just picking the first element

def get_client(p_log_fun,
	p_host_port_lst = ['127.0.0.1:27017']):
	p_log_fun('FUN_ENTER','gf_db_mongodb.get_client()')

	host_str,port_str = p_host_port_lst[0].split(':')

	mongo_client = pymongo.MongoClient(host_str,int(port_str))
	return mongo_client
#------------------------------------------------------
#this is a function of its own so that the command for mongo startup can be 
#acquired on its own, without always starting an actual mongo instance.
#so that the command string can be passed to various monitoring tools and scripts

#->:String
def get_startup_command(p_db_server_data_dir_path_str,
			p_log_file_path_str,
			p_log_fun,

			p_port_str                         = '27017',
			p_use_replication_bool             = False,
			p_replica_set_name_str             = 'rs0',
			p_is_config_server_bool            = False,
			p_mongod_bin_file_path_str         = '%s/mongo/mongodb-linux-i686-2.4.6/bin/mongod'%(installs_root),
			p_auth_for_client_connections_bool = False):
	p_log_fun('FUN_ENTER','gf_db_mongodb.get_startup_command()')

	#ADD!! --replica_set - configure this to have the master set, and others be slaves...
	#                      to test master allocation on previous master fail
	args_lst = [
		'--dbpath %s'%(p_db_server_data_dir_path_str),
		'--port %s'%(p_port_str),
		'--rest',                                #turn on REST http API interface
		'--journal',                             #turn journaling/durability on
            

		'--fork',                                #start the server as a deamon
		'--logpath %s'%(p_log_file_path_str),
        
		'--oplogSize 128'
	]

	if p_auth_for_client_connections_bool:
		#Set to true to enable database authentication for users connecting from remote hosts
		args_lst.append('--auth')

	#----------
	#IMPORTANT!! - starts a config server, which is used in mongo sharding clusters
	if p_is_config_server_bool:
		args_lst.append('--configsvr')
	else:
		if p_use_replication_bool:

			args_lst.append('--replSet %s'%(p_replica_set_name_str))

			#---------------
			#if this argument is included when mongod is run as a config_server ('--configsvr')
			#the following error is returned:
			#"replication should not be enabled on a config server"

			#each node is a part of a cluster  
			
			#---------------
	#----------

	#if in a test environment, reduce the amount of space on disk that this mongod
	#instance is using
	#args_lst.append('--smallfiles')

	args_str = reduce(lambda p_arg_str,p_accum:'%s %s'%(p_accum,p_arg_str),
				args_lst)

	cmd_str = '%s %s'%(p_mongod_bin_file_path_str,
				 args_str)

	return cmd_str
#------------------------------------------------------
#FIX!! - this command kills all mongod instances running. should there be a more targeted
#        way to just kill a particular instance?

#->:String
def get_shutdown_command(p_log_fun):
	p_log_fun('FUN_ENTER','gf_db_mongodb.get_shutdown_command()')
	cmd_str = 'kill -9 `ps -e | grep mongod | awk {print $1}`'
	return cmd_str
#------------------------------------------------------
#->:Dict(server_info_dict)
def start_db_server(p_name_str,
		p_db_server_data_dir_path_str,
		p_log_file_path_str,
		p_run_cmd_fun,
		p_log_fun,
		p_host_str                 = '127.0.0.1', 
		p_port_str                 = '27017',
		p_use_replication_bool     = False,
		p_replica_set_name_str     = 'rs0',
		p_wait_time_seconds        = 3,
		p_is_config_server_bool    = False,
		p_mongod_bin_file_path_str = '%s/mongo/mongodb-linux-i686-2.4.6/bin/mongod'%(installs_root),
		p_remote_bool              = False,

		p_auth_for_client_connections_bool = False):
	p_log_fun('FUN_ENTER','gf_db_mongodb.start_db_server()')
	p_log_fun('INFO'     ,'p_name_str                   :%s'%(p_name_str))
	p_log_fun('INFO'     ,'p_host_str                   :%s'%(p_host_str))
	p_log_fun('INFO'     ,'p_port_str                   :%s'%(p_port_str))
	p_log_fun('INFO'     ,'p_db_server_data_dir_path_str:%s'%(p_db_server_data_dir_path_str))
	p_log_fun('INFO'     ,'p_log_file_path_str          :%s'%(p_log_file_path_str))

	if p_remote_bool == False:
		os_ref = os
		if not os_ref.path.isdir(p_db_server_data_dir_path_str):
			envoy.run('sudo mkdir %s'%(p_db_server_data_dir_path_str))
	
	cmd_str = get_startup_command(p_db_server_data_dir_path_str,
				p_log_file_path_str,
				p_log_fun,

				p_port_str                         = p_port_str,
				p_use_replication_bool             = p_use_replication_bool,
				p_replica_set_name_str             = p_replica_set_name_str,
				p_is_config_server_bool            = p_is_config_server_bool,
				p_mongod_bin_file_path_str         = p_mongod_bin_file_path_str,
				p_auth_for_client_connections_bool = p_auth_for_client_connections_bool)

	sudo_cmd_str = 'sudo %s'%(cmd_str)
	p_log_fun('INFO','cmd_str:%s'%(sudo_cmd_str))
	
	#---------
	result_dict = p_run_cmd_fun(sudo_cmd_str)
	assert isinstance(result_dict,dict)

	server_pid_int = result_dict['pid_int']
	std_out_str    = result_dict['std_out_str']
	assert isinstance(std_out_str,basestring)
	assert len(std_out_str) > 0

	deamon_pid_int = None

	#---------
	#LOCAL
	if p_remote_bool == False:

		#IMPORTANT!! - because of '--fork' passed to mongos, the pid thats returned by 
		#              p_run_cmd_fun is not the pid of the demon. this is returned in the std_out
		#              of the mongos call.
		#              name startup_process_pid_int indicates that this is only the startup process,
		#              not deamon
		#startup_process_pid_int = resulst_dict['pid_int']
		deamon_pid_int = get_forked_deamon_pid_from_std_out(std_out_str,
			                                        	p_log_fun)
		assert isinstance(deamon_pid_int,int)
		#---------

		time.sleep(p_wait_time_seconds)
		
		#VERIFICATION
		gf_net_utils.check_port_is_listening(p_port_str,
						p_log_fun)
	#---------

	server_info_map = {
		'name_str'         :p_name_str,
		'host_str'         :p_host_str,
		'port_str'         :p_port_str,
		'data_dir_path_str':p_db_server_data_dir_path_str,
		'pid_int'          :deamon_pid_int,

		#used for restarting of the mongod instance in case it crashes,
		#by other automated monitoring tools
		'startup_command_str':cmd_str
	}

	return server_info_map
#----------------------------------------------
#->:int
def get_forked_deamon_pid_from_std_out(p_std_out_str,
					p_log_fun):
	p_log_fun('FUN_ENTER','gf_db_mongodb.get_forked_deamon_pid_from_std_out()')

	#print '---------------------------------------------------'
	#print p_std_out_str.split('\n')[1]
	#print p_std_out_str.split('\n')[1].split(':')
	#print p_std_out_str.split('\n')[1].split(':')[1]
	#print p_std_out_str.split('\n')[1].split(':')[1].strip()

	#"std_out_str.split('\n')[1]" - gets the second line
	#second line is: "forked process: 13313"
	#split(':')[1].strip() - gets the number at the end of that line

	#print '======================================='
	#print p_std_out_str
	#print p_std_out_str.split('\n')
	#print p_std_out_str.split('\n')[1]

	deamon_pid_int = int(p_std_out_str.split('\n')[1].split(':')[1].strip())
	assert isinstance(deamon_pid_int,int)

	p_log_fun('INFO','>>>>> deamon_pid_int - %s'%(deamon_pid_int))
	return deamon_pid_int
#----------------------------------------------
#its more efficient to insert documents into an empty collection 
#that is already sharded, then it is to shard a fully populated collection
#so this is a utility function

def create_sharded_empty_collection(p_log_fun):
	p_log_fun('FUN_ENTER','gf_db_mongodb.create_sharded_empty_collection()')
#----------------------------------------------
#REPLICA_SET
#----------------------------------------------
def configure_replica_set(p_replica_set_name_str,
			p_dbs_servers_infos_lst,
			p_run_cmd_fun,
			p_log_fun,
			p_remote_mongo_client_bin_file_path_str = '%s/mongo/mongodb-linux-i686-2.4.6/bin/mongo'%(installs_root)):
	p_log_fun('FUN_ENTER','gf_db_mongodb.configure_replica_set()')
	
	#----------------------------------------------
	#->:String
	def init_primary_node():
		p_log_fun('FUN_ENTER','gf_db_mongodb.configure_replica_set().init_primary_node()')

		primary_node_info_dict = p_dbs_servers_infos_lst[0]
		assert isinstance(primary_node_info_dict,dict)

		assert primary_node_info_dict.has_key('port_str')
		primary_node_port_str = primary_node_info_dict['port_str']
		
		#makes the configuration object for the replica-set cluster.
		#only one master is declared, and that member is the master
		replica_sets_config_json_obj_str = '''
			rsconf = {
				_id: '%s',`
				members: [{_id:0,host:'localhost:%s'}]}
			'''%(p_replica_set_name_str,
				 primary_node_port_str)
		
		cmd_str = '''%s --port %s --eval "rs.initiate(%s)"'''%(p_remote_mongo_client_bin_file_path_str,
											primary_node_port_str,
											replica_sets_config_obj_str)
		
		result_dict = p_run_cmd_fun(cmd_str)
		result_str  = result_dict['std_out_str']
		assert isinstance(result_str,basestring)

		return primary_node_port_str
	#----------------------------------------------
	def add_secondary_nodes_to_replica_set(p_primary_node_port_str):
		p_log_fun('FUN_ENTER','gf_db_mongodb.configure_replica_set().add_secondary_nodes_to_replica_set()')

		secondary_servers_infos_lst = p_dbs_servers_infos_lst[1:]

		#add each one of the slave nodes to the replica set
		#New replica sets elect a primary within a few seconds.
		for secondary_db_server_info_dict in secondary_servers_infos_lst:
			assert isinstance(secondary_db_server_info_dict,dict)

			secondary_db_server_host_str = secondary_db_server_info_dict['host_str']
			secondary_db_server_port_str = secondary_db_server_info_dict['port_str']
			
			p_log_fun('INFO','adding secondary server [%s:%s] to the replica set'%(secondary_db_server_host_str,
														secondary_db_server_port_str))
			
			cmd_str = '''%s --port %s --eval "rs.add('%s:%s')"'''%(p_remote_mongo_client_bin_file_path_str,
												p_primary_node_port_str,
												secondary_db_server_host_str,
												secondary_db_server_port_str)
			result_str = p_run_cmd_fun(cmd_str)
	#----------------------------------------------

	primary_node_port_str = init_primary_node()
	add_secondary_nodes_to_replica_set(primary_node_port_str)

	#pause this thread briefly, to give the mongodb cluster time to set up its replica set
	time.sleep(3)
#----------------------------------------------
def view_repl_set_info(p_mongodb_host_str,
			p_log_fun):
	p_log_fun('FUN_ENTER','gf_db_mongodb.view_repl_set_info()')
	p_log_fun('INFO','p_mongodb_host_str - %s'%(p_mongodb_host_str))
	assert isinstance(p_mongodb_host_str,basestring)

	host_ip_str = p_mongodb_host_str.split('/')[0]
	p_log_fun('INFO','host_ip_str - %s'%(host_ip_str))

	c = pymongo.MongoClient(host=host_ip_str)
	#'admin' - DB name
	repl_set_status_map = c.admin.command('replSetGetStatus')

	p_log_fun('INFO','>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> -------------------- +++++++++++')
	p_log_fun('INFO',"repl_set_status_map.keys() - %s"%(repl_set_status_map.keys()))
	p_log_fun('INFO',"repl_set_status_map['set'] - %s"%(repl_set_status_map['set']))
	p_log_fun('INFO',"repl_set members:")
	p_log_fun('INFO',"members # - %s"%(len(repl_set_status_map['members'])))

	for m in repl_set_status_map['members']:

		p_log_fun('INFO','\t%s - %s'%(m['name'],m['stateStr']))
		for k,v in m.items():
			p_log_fun('INFO','\t\t%s - %s'%(k,v))