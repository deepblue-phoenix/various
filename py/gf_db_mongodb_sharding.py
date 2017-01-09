#README - utility functions for working with the mongodb sharding

import sys,os
import process_utils
import gf_db_mongodb
#----------------------------------------------
#->:Dict
def start_sharding_cluster(p_name_str,
		p_config_servers_static_infos_lst,
		p_shard_router_servers_static_infos_lst,
		p_shard_servers_static_infos_lst,

		p_run_cmd_fun,
		p_log_fun,
		p_locality_type_str = 'local'):
	p_log_fun('FUN_ENTER','gf_db_mongodb_sharding.start_sharding_cluster()')
	assert isinstance(p_name_str                             ,basestring)
	assert isinstance(p_config_servers_static_infos_lst      ,list)
	assert isinstance(p_shard_router_servers_static_infos_lst,list)
	assert isinstance(p_shard_servers_static_infos_lst       ,list)

	assert isinstance(p_locality_type_str,basestring)
	assert p_locality_type_str == 'local' or \
	       p_locality_type_str == 'remote'

	#---------------------------------------------------
	#->:List<:Dict>
	def start_servers(p_servers_static_infos_lst,
			p_type_str,
			p_config_servers_runtime_infos_lst = None):
		p_log_fun('FUN_ENTER','gf_db_mongodb_sharding.start_sharding_cluster().start_servers()')

		assert isinstance(p_config_servers_static_infos_lst,list)

		servers_runtime_infos_lst = [] #:List<:Dict>

		for server_info_map in p_servers_static_infos_lst:
			assert isinstance(server_info_map,dict)

			server_runtime_info_map = None

			#------------
			#CONFIG 

			if p_type_str == 'config_server':
				server_runtime_info_map = start_server(server_info_map,
									p_type_str,
									run_cmd_fun,
									p_log_fun)
			#------------
			#SHARD ROUTER

			elif p_type_str == 'shard_router_server':

				#----------------------------------------------
				#->:Dict
				def keyup_config_servers_runtime_infos():
					p_log_fun('FUN_ENTER','gf_db_mongodb_sharding.start_sharding_cluster().start_servers().keyup_config_servers_runtime_infos()')
					config_servers_runtime_infos_map = {}
					for info_map in p_config_servers_runtime_infos_lst: 
						config_servers_runtime_infos_map[info_map['name_str']] = info_map
					return config_servers_runtime_infos_map
				#----------------------------------------------
				config_servers_runtime_infos_map = keyup_config_servers_runtime_infos()

				server_runtime_info_map = start_server(server_info_map,
									p_type_str,
									run_cmd_fun,
									p_log_fun,
									p_config_servers_runtime_infos_map = config_servers_runtime_infos_map)
			#------------
			#SHARD

			elif p_type_str == 'shard_server':
				server_runtime_info_map = start_server(server_info_map,
									p_type_str,
									run_cmd_fun,
									p_log_fun)
			#------------
			servers_runtime_infos_lst.append(server_runtime_info_map)

			if p_locality_type_str == 'local':
				assert server_runtime_info_map.has_key('pid_int')
				pid_int = server_runtime_info_map['pid_int']
				assert isinstance(pid_int,int)

				process_utils.check_pid_is_running(pid_int,
								p_log_fun)

		return servers_runtime_infos_lst
	#----------------------------------------------
	#--------------
	#MAIN

	config_servers_runtime_infos_lst = start_servers(p_config_servers_static_infos_lst,
										'config_server')
	shard_router_servers_runtime_infos_lst = start_servers(p_shard_router_servers_static_infos_lst,
								'shard_router_server',
								p_config_servers_runtime_infos_lst = config_servers_runtime_infos_lst)


	shard_servers_runtime_infos_lst = start_servers(p_shard_servers_static_infos_lst,
							'shard_server')

	add_shards_to_cluster(shard_servers_runtime_infos_lst,
			shard_router_servers_runtime_infos_lst,
			run_cmd_fun,
			p_log_fun)
	#--------------

	sharding_cluster_info_map = {
		'name_str'                              :p_name_str,
		'config_servers_runtime_infos_lst'      :config_servers_runtime_infos_lst,
		'shard_router_servers_runtime_infos_lst':shard_router_servers_runtime_infos_lst,
		'shard_servers_runtime_infos_lst'       :shard_servers_runtime_infos_lst
	}

	return sharding_cluster_info_map
#------------------------------------------------------
#->:Dict
def start_server(p_server_info_map,
		p_type_str,
		p_run_cmd_fun,
		p_log_fun,
		p_config_servers_runtime_infos_map = None):
	p_log_fun('FUN_ENTER','gf_db_mongodb_sharding.start_server()')
	assert p_type_str == 'config_server' or \
	       p_type_str == 'shard_router_server' or \
	       p_type_str == 'shard_server'

	p_log_fun('INFO','----------------------------------------------------')
	p_log_fun('INFO','STARTING NEW SERVER')
	p_log_fun('INFO','----------------------------------------------------')

	name_str                = p_server_info_map['name_str']
	host_str                = p_server_info_map['host_str']
	port_str                = p_server_info_map['port_str']
	data_dir_path_str       = p_server_info_map['data_dir_path_str']
	log_file_path_str       = p_server_info_map['log_file_path_str']
	server_runtime_info_map = None

	#--------------
	if p_type_str == 'config_server':

		#for config_server's info on other config servers is not necessary,
		#is it is checked that the called did not pass that in
		#(this parameter has a value for shard_server's)
		assert p_config_servers_runtime_infos_map == None

		server_runtime_info_map = gf_db_mongodb.start_db_server(name_str,                              
										data_dir_path_str, #p_db_server_data_dir_path_str,
										log_file_path_str,
										p_run_cmd_fun,
										p_log_fun,
										p_host_str              = host_str,
										p_port_str              = port_str,
										p_is_config_server_bool = True)
		assert isinstance(server_runtime_info_map,dict)
	#--------------
	elif p_type_str == 'shard_router_server':
		assert isinstance(p_config_servers_runtime_infos_map,dict)

		server_runtime_info_map = start_shard_router_server(name_str,
										host_str,
										port_str,
										p_config_servers_runtime_infos_map,
										log_file_path_str,
										p_run_cmd_fun,
										p_log_fun)
		assert isinstance(server_runtime_info_map,dict)	
	#--------------
	elif p_type_str == 'shard_server':
		server_runtime_info_map = gf_db_mongodb.start_db_server(name_str,
										data_dir_path_str, #p_db_server_data_dir_path_str,
										log_file_path_str,
										p_run_cmd_fun,
										p_log_fun,
										p_host_str = host_str,
										p_port_str = port_str)		
		assert isinstance(server_runtime_info_map,dict)
	#--------------

	return server_runtime_info_map
#----------------------------------------------
#->:Dict
def start_shard_router_server(p_name_str,
		p_host_str,
		p_port_str,
		p_config_servers_runtime_infos_map,
		p_log_file_path_str,
		p_run_cmd_fun,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_db_mongodb_sharding.start_shard_router_server()')
	assert isinstance(p_name_str                        ,basestring)
	assert isinstance(p_host_str                        ,basestring)
	assert isinstance(p_config_servers_runtime_infos_map,dict)

	#------------------------------------------------------
	#->:String
	def serialize_config_servers_hostnames(p_config_servers_runtime_infos_map):
		p_log_fun('FUN_ENTER','gf_db_mongodb_sharding.start_shard_router_server().serialize_config_servers_hostnames()')

		servers_str = ''
		for server_name_str,server_info_map in p_config_servers_runtime_infos_map.items():
			assert isinstance(server_name_str ,basestring)
			assert isinstance(server_info_map,dict)

			host_str = server_info_map['host_str']
			port_str = server_info_map['port_str']

			hostport_str = '%s:%s'%(host_str,port_str)
			servers_str += hostport_str

		servers_str.strip(',')

		return servers_str
	#------------------------------------------------------

	#-------
	#list of all possible shell arguments
	#http://docs.mongodb.org/manual/reference/program/mongos/#bin.mongos

	config_servers_hostnames_str = serialize_config_servers_hostnames(p_config_servers_runtime_infos_map)
	args_lst = [
		'--configdb %s'%(config_servers_hostnames_str), #'--configdb <config server hostnames>',
		'--port %s'%(p_port_str),
		'--logpath %s'%(p_log_file_path_str),
		'--fork'] #start the shard server as a deamon
	#-------

	args_str = reduce(lambda p_arg_str,p_accum:'%s %s'%(p_accum,p_arg_str),
			args_lst)

	cmd_str = 'sudo mongos %s'%(args_str)
	p_log_fun('INFO','cmd_str:%s'%(cmd_str))

	results_map = p_run_cmd_fun(cmd_str)
	std_out_str  = results_map['std_out_str']
	assert isinstance(std_out_str,basestring)

	#-------
	#IMPORTANT!! - because of '--fork' passed to mongos, the pid thats returned by 
	#              p_run_cmd_fun is not the pid of the demon. this is returned in the std_out
	#              of the mongos call.
	#              name startup_process_pid_int indicates that this is only the startup process,
	#              not deamon
	#startup_process_pid_int = resulst_map['pid_int']
	deamon_pid_int = gf_db_mongodb.get_forked_deamon_pid_from_std_out(std_out_str,
										p_log_fun)
	assert isinstance(deamon_pid_int,int)
	#-------

	server_info_map = {
		'name_str':p_name_str,
		'host_str':p_host_str,
		'port_str':p_port_str,
		'pid_int' :deamon_pid_int
	}

	return server_info_map
#----------------------------------------------
def add_shards_to_cluster(p_shard_servers_runtime_infos_lst,
		p_shard_router_servers_runtime_infos_lst,
		p_run_cmd_fun,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_db_mongodb_sharding.add_shards_to_cluster()')
	assert isinstance(p_shard_servers_runtime_infos_lst       ,list)
	assert isinstance(p_shard_router_servers_runtime_infos_lst,list)

	#----------------------------------------------
	def register_with_shard_router(p_shard_router_server_runtime_info_map):
		p_log_fun('FUN_ENTER','gf_db_mongodb_sharding.add_shards_to_cluster().register_with_shard_router()')

		#register each shard with the shard router
		for shard_server_runtime_info_map in p_shard_servers_runtime_infos_lst:
			isinstance(shard_server_runtime_info_map,dict)

			add_shard_to_cluster(shard_router_server_runtime_info_map,
				shard_server_runtime_info_map,
				p_run_cmd_fun,
				p_log_fun)
	#----------------------------------------------

	#for each shard-router register all shards with it
	for shard_router_server_runtime_info_map in p_shard_router_servers_runtime_infos_lst:
		assert isinstance(shard_router_server_runtime_info_map,dict)

		register_with_shard_router(shard_router_server_runtime_info_map)
#----------------------------------------------
def add_shard_to_cluster(p_shard_router_runtime_info_map,
		p_shard_server_runtime_info_map,
		p_run_cmd_fun,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_db_mongodb_sharding.add_shard_to_cluster()')
	assert isinstance(p_shard_router_runtime_info_map,dict)
	assert isinstance(p_shard_server_runtime_info_map,dict)

	#shard server (mongod) thats being registered to become a part of the cluster
	shard_host_str       = p_shard_server_runtime_info_map['host_str']
	shard_port_str       = p_shard_server_runtime_info_map['port_str']
	shard_host_port_str  = '%s:%s'%(shard_host_str,shard_port_str)

	#each shard is registered manually with the shard_router (mongos) 
	shard_router_host_str = p_shard_router_runtime_info_map['host_str']
	shard_router_port_str = p_shard_router_runtime_info_map['port_str']

	#example:"sh.addShard( "rs1/mongodb0.example.net:27017" )"
	mongo_js_command_str = '''sh.addShard('%s')'''%(shard_host_port_str)


	cmd_str = '''mongo --host %s --port %s --eval "%s"'''%(shard_router_host_str,
											shard_router_port_str,
											mongo_js_command_str)

	result_map = p_run_cmd_fun(cmd_str)
	assert isinstance(result_map,dict)