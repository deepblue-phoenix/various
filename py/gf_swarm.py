#README - utility functions for working with docker swarm clusters (initial SWARM versions, not tested with post-docker1.12)

import os
import time

import gf_fabric_utils
#---------------------------------------------------
def get_run_cmd(p_container_name_str,
			p_container_image_name_str,
			p_log_fun,
			p_allow_iptables_bool = True,
			p_docker_network_str  = 'gf_staging',
			p_docker_ports_map    = None,
			p_docker_volumes_lst  = None,
			p_docker_env_vars_map = None):
	p_log_fun('FUN_ENTER','gf_swarm.get_run_cmd()')

	#---------------------
	p_log_fun('INFO','p_container_name_str - %s'%(p_container_name_str))
	assert isinstance(p_container_name_str,basestring)
	#---------------------
	#"--add-host" - Add a custom host-to-IP mapping (host:ip) in /etc/hosts

	cmd_lst = [
		'sudo',
		'docker',
		'run',
		'-d', #start a container in detached mode
	]
	#-------------
	#NETWORKING

	if p_docker_network_str:

		#IMPORTANT!! - docker 1.9 replaced experimental --publish-service with --net=
		#connects the container to user-created network 
		#using `docker network create` command
		cmd_lst.append('--net=%s'%(p_docker_network_str))
	#-------------
	#IPTABLES
	#starts up the container with sufficient privilages to run iptables inside of it

	if p_allow_iptables_bool:
		cmd_lst.append('--cap-add=NET_ADMIN')
		cmd_lst.append('--cap-add=NET_RAW')
	#-------------
	#VOLUMES
	if not p_docker_volumes_lst == None:
		assert isinstance(p_docker_volumes_lst,list)
		for host_path_str,container_path_str in p_docker_volumes_lst:
			a = '-v %s:%s'%(host_path_str,
							container_path_str)
			cmd_lst.append(a)
	#-------------
	#PORTS
	if not p_docker_ports_map == None:
		assert isinstance(p_docker_ports_map,dict)
		for k,v in p_docker_ports_map.items():
			extern_port_str   = k
			internal_port_str = v

			a = '-p %s:%s'%(extern_port_str,
							internal_port_str)
			cmd_lst.append(a)			
	#-------------
	#ENV_VARS
	if not p_docker_env_vars_map == None:
		assert isinstance(p_docker_env_vars_map,dict)
		for k,v in p_docker_env_vars_map.items():

			a = '-e %s=%s'%(k,v)
			cmd_lst.append(a)
	#-------------
	#SECURITY
	#https://docs.docker.com/reference/run/#network-settings
	
	#for containers that do not need to see the world
	#cmd_lst.append("--net='none'")
	#-------------
	#DOCKER RESTART POLICIES

	#IMPORTANT!! - 'always' - Always restart the container no matter what exit code is returned.
	#                         Docker daemon will try to restart the container indefinitely.
	#cmd_lst.append('--restart=always')
	#-------------
	cmd_lst.append('--name %s'%(p_container_name_str))
	cmd_lst.append(p_container_image_name_str)
	#-------------

	cmd_str = ' '.join(cmd_lst)
	return cmd_str
#---------------------------------------------------
#CREATE DOCKER NETWORK
#docker network create -d overlay netname
#docker network ls
#---------------------------------------------------
#->:String
def create_swarm_cluster(p_fab_api,
					p_log_fun):
	p_log_fun('FUN_ENTER','gf_swarm.create_swarm_cluster()')

	#"--rm" - remove command container after running it
	c              = 'docker run --rm swarm create'
	r_str          = p_fab_api.run(c)
	cluster_id_str = r_str

	return cluster_id_str
#---------------------------------------------------
def db_create__swarm_cluster_info(p_cluster_name_str,
						p_swarm_cluster_id_str,
						p_db_context_map,
						p_log_fun,
						p_db_name_str   = 'gf_ops',
						p_coll_name_str = 'swarm_cluster_info'):
	p_log_fun('FUN_ENTER','gf_swarm.boostrap().db_create__swarm_cluster_info()')
	assert  isinstance(p_swarm_cluster_id_str,basestring)

	mongodb_client = p_db_context_map['mongodb_client']
	gf_node_phy_db = mongodb_client[p_db_name_str]
	coll           = gf_node_phy_db[p_coll_name_str]

	swarm__cluster_info_map = {
			'obj_class_str'         :'swarm_cluster_info',
			'creation_unix_time_str':str(time.time()),
			'name_str'              :p_cluster_name_str,
			'swarm_cluster_id_str'  :p_swarm_cluster_id_str
		}
	coll.insert(swarm__cluster_info_map)
#---------------------------------------------------
#->:Map
def db_get__swarm_cluster_info(p_cluster_name_str,
						p_db_context_map,
						p_log_fun,
						p_db_name_str   = 'gf_ops',
						p_coll_name_str = 'swarm_cluster_info'):
	p_log_fun('FUN_ENTER','gf_swarm.db_get__swarm_cluster_info()')
	assert isinstance(p_cluster_name_str,basestring)

	mongodb_client = p_db_context_map['mongodb_client']
	gf_node_phy_db = mongodb_client[p_db_name_str]
	coll           = gf_node_phy_db[p_coll_name_str]

	newest__cluster_info_map = coll.find({
									'obj_class_str':'swarm_cluster_info',
									'name_str'     :p_cluster_name_str
								}).sort("creation_unix_time_str",-1)[0]

	assert newest__cluster_info_map.has_key('swarm_cluster_id_str')
	return newest__cluster_info_map
#---------------------------------------------------
def join_node_to_cluster(p_cluster_id_str,
					p_member_host_str,

					p_fab_api,
					p_log_fun,
					p_docker_port_str                      = '2375',
					p_docker_kv_store__etcd__host_port_str = '127.0.0.1:2379'):
	p_log_fun('FUN_ENTER','gf_swarm.join_node_to_cluster()')
	assert isinstance(p_cluster_id_str,basestring)
	
	c_lst = [
		'docker',
		'run',
		'-d',   #run detached
		'--rm', #remove container after done running
		'swarm',
		'join',
		'token://%s'%(p_cluster_id_str),
		'--addr=%s:%s'%(p_member_host_str,p_docker_port_str),
		'etcd://%s'%(p_docker_kv_store__etcd__host_port_str)
	]

	cmd_str = ' '.join(c_lst)
	p_log_fun('INFO','++++++++++  MEMBER JOIN SWARM - Docker Host %s:%s'%(p_member_host_str,
																p_docker_port_str))
	p_log_fun('INFO',cmd_str)

	r = p_fab_api.run(cmd_str)
#---------------------------------------------------
def view_swarm_info__remote(p_master__node_phy_adt,
					p_fab_api,
					p_db_context_map,
					p_log_fun,
					p_cluster_name_str = 'public_cluster'):
	p_log_fun('FUN_ENTER','gf_swarm.view_swarm_info__remote()')
	assert isinstance(p_master__node_phy_adt,gf_node_phy_adt.NodePhy_ADT)

	#---------------------------------------------------
	def task():
		p_log_fun('FUN_ENTER','gf_swarm.view_swarm_info__remote().task()')
	
		swarm_cluster_info_map = db_get__swarm_cluster_info(p_cluster_name_str,
													p_db_context_map,
													p_log_fun)
		assert isinstance(swarm_cluster_info_map,dict)
		swarm_cluster_id_str = swarm_cluster_info_map['swarm_cluster_id_str']

		#----------------
		#SWARM COMMAND
		#list all nodes to see what was added
		list_str = 'docker run --rm swarm list token://%s'%(swarm_cluster_id_str)
		p_fab_api.run(list_str)
		#----------------
	#---------------------------------------------------
	p_log_fun('INFO','========= RUNNING TASK ON NODE [%s] - user [%s]'%(p_master__node_phy_adt.name_str,
																		p_master__node_phy_adt.user_str))
	gf_fabric_utils.run_task_on_node_phys(task,       #p_task_fun,
							[p_master__node_phy_adt], #p_target_node_phys_lst, #p_node_phys_adts_lst,
							p_fab_api,
							p_log_fun,
							p_verbose_bool = True)	
#---------------------------------------------------
def init_swarm_manager(p_cluster_id_str,
					p_fab_api,
					p_log_fun,
					p_swarm_manager_host_str     = '127.0.0.1',
					p_swarm_manager_port_str     = '5001',
					p_os_startup_script_path_str = '/etc/rc.local'):
	p_log_fun('FUN_ENTER','gf_swarm.init_swarm_manager()')
	assert isinstance(p_cluster_id_str,basestring)

	#START MANAGER - to which the docker client will connect to, to issue docker commands
	c_lst = [
		'docker',
		'run',
		'--rm', #remove container after done running
		'-p %s:%s'%(p_swarm_manager_port_str,p_swarm_manager_port_str),
		'swarm',
		'manage',

		#IMPORTANT!! - host/port on which this manger is going to listen
		'--host=%s:%s'%(p_swarm_manager_host_str,p_swarm_manager_port_str),

		'token://%s'%(p_cluster_id_str)
	]

	c_str = ' '.join(c_lst)
	#---------------------------------------------------
	#make swarm_manager start on system boot

	def init_startup__on_boot(p_deamon__cmd_str):
		p_log_fun('FUN_ENTER','gf_swarm.init_swarm_manager().init_startup__on_boot()')

		fab_file = fabric.contrib.files

		#----------------
		#cleanup
		fab_file.comment(p_os_startup_script_path_str,'^exit 0')         #'exit 0' - anything after this line is not exectuced, so comment it out
		fab_file.comment(p_os_startup_script_path_str,'^docker run -p ') #comment out if any previous docker startup commands exist
		#----------------
		#add config
		fab_file.append(p_os_startup_script_path_str ,p_deamon__cmd_str)
		fab_file.append(p_os_startup_script_path_str ,'exit 0')
	#---------------------------------------------------
	init_startup__on_boot(c_str)

	#--------------------
	#START MANAGER ON MASTER

	p_fab_api.run('apt-get install dtach') #REMOVE!! - dont 'apt-get install' do it every time here
	p_fab_api.run('dtach -n `mktemp -u /tmp/dtach.XXXX` %s'%(c_str))
	#--------------------