#README - utility functions for working with the docker

import os

import json
import subprocess

import envoy
import fabric.contrib.files
#---------------------------------------------------
#->:String
def get_cont_ip(p_container_name_str,
	p_log_fun,
	p_docker_net_name_str = 'gf_staging'):
	p_log_fun('FUN_ENTER','gf_docker.get_cont_ip()')
	p_log_fun('INFO'     ,p_container_name_str)
	
	cont_info_map = json.loads(envoy.run('sudo docker inspect %s'%(p_container_name_str)).std_out)
	nets_info_map = cont_info_map[0]['NetworkSettings']['Networks']
	assert nets_info_map.has_key(p_docker_net_name_str)

	cont_ip_str = nets_info_map[p_docker_net_name_str]['IPAddress']
	return cont_ip_str
#---------------------------------------------------
def cont_is_running(p_cont_image_name_str,
		p_db_context_map,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_docker.cont_is_running()')
	p_log_fun('INFO'     ,'p_cont_image_name_str - %s'%(p_cont_image_name_str))

	r = envoy.run('sudo docker ps -a | grep %s'%(p_cont_image_name_str))

	if r.std_out == '':
		print 'CONTAINER NOT RUNNING -----------------------'
		return False
	else:
		print 'CONTAINER RUNNING -----------------------'
		return True
#---------------------------------------------------
def build_image(p_dockerfile_path_str,
		p_cont_image_name_str,
		p_db_context_map,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_docker.build_image()')
	p_log_fun('INFO'     ,'dockerfile_path_str - %s'%(p_dockerfile_path_str))

	assert os.path.isfile(p_dockerfile_path_str)

	context_dir_path_str = os.path.dirname(p_dockerfile_path_str)

	p_log_fun('INFO','====================+++++++++++++++=====================')
	p_log_fun('INFO','        BUILDING [%s] IMAGE'%(p_cont_image_name_str))
	p_log_fun('INFO','Dockerfile     - %s'%(p_dockerfile_path_str))
	p_log_fun('INFO','image_name_str - %s'%(p_cont_image_name_str))
	p_log_fun('INFO','====================+++++++++++++++=====================')

	cmd_lst = [
		'sudo',
		'docker',
		'build',
		'-f %s'%(p_dockerfile_path_str),
		'--tag=%s'%(p_cont_image_name_str),
		context_dir_path_str
	]

	cmd_str = ' '.join(cmd_lst)
	p_log_fun('INFO',' - %s'%(cmd_str))

	#change to the dir where the Dockerfile is located, for the 'docker'
	#tool to have the proper context
	old_cwd = os.getcwd()
	os.chdir(context_dir_path_str)
	
	r = subprocess.Popen(cmd_str,
			shell   = True,
			stdout  = subprocess.PIPE,
			bufsize = 1)

	#---------------------------------------------------
	def get_image_id_from_line(p_stdout_line_str):
		p_lst = p_stdout_line_str.split(' ')

		assert len(p_lst) == 3
		image_id_str = p_lst[2]

		#IMPORTANT!! - check that this is a valid 12 char Docker ID
		assert len(image_id_str) == 12
		return image_id_str
	#---------------------------------------------------

	for line in r.stdout:
		line_str = line.strip() #strip() - to remove '\n' at the end of the line

		#------------------
		#display the line, to update terminal display
		print line_str
		#------------------

		if line_str.startswith('Successfully built'):
			image_id_str = get_image_id_from_line(line_str)
			return image_id_str

	#change back to old dir
	os.chdir(old_cwd)
#---------------------------------------------------
def save_image_to_file(p_image_name_str,
		p_file_name_str,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_docker.save_image_to_file()')
	assert isinstance(p_image_name_str,basestring)
	cmd_lst = [
		'sudo',
		'docker',
		'save',
		'-o %s'%(p_file_name_str),
		p_image_name_str
	]
	cmd_str = ' '.join(cmd_lst)

	p_log_fun('INFO','cmd_str - %s'%(cmd_str))

	r = envoy.run(cmd_str)
	p_log_fun('INFO',r.std_out)
#---------------------------------------------------
#->:Map
def get_container_info(p_container_id_str,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_docker.get_container_info()')

	cmd_str = 'sudo docker inspect %s'%(p_container_id_str)
	r       = envoy.run(cmd_str)

	container_infos_str = r.std_out
	container_infos_lst = json.loads(container_infos_str)
	assert isinstance(container_infos_lst,list)

	container_info_map = container_infos_lst[0]
	assert isinstance(container_info_map,dict)


	assert container_info_map['State']['Running'] == True
	volumes_map = container_info_map['Volumes']
	host_str    = container_info_map['NetworkSettings']['IPAddress']

	return {
		'host_str':host_str
	}
#---------------------------------------------------
def config_remote__docker_deamon(p_fab_api,
			p_log_fun,
			p_docker_port_str                      = '2375',
			p_docker_host_labels_lst               = None,
			p_docker_kv_store__etcd__host_port_str = '127.0.0.1:2379',
			p_docker_config_path_str               = '/etc/default/docker'):
	p_log_fun('FUN_ENTER','gf_docker.config_remote__docker_deamon()')
	
	#IMPORTANT!! - CHECK DOCKER_OPTS IS UNCOMMENTED
	#IMPORTANT!! - "^DOCKER_OPTS" - check if there is a line in p_docker_config_path_str file,
	#                               that starts with this literal, indicating that
	#                               this is not a fresh config file, and there is already 
	#                               something configured.
	#                               By default the DOCKER_OPTS line is commented out
	#'escape=False' - If escape is False, no extra regular expression related escaping is 
	#                 performed (this includes overriding exact so that no ^/$ is added.)
	if fabric.contrib.files.contains(p_docker_config_path_str,
					'^DOCKER_OPTS',
					escape = False):

		p_log_fun('INFO','DOCKER CONFIG FILE - "DOCKER_OPTS=..." - ALREADY PRESENT - skip config')
		p_fab_api.run('service docker start') #start docker if not started

		return
	else:

		deamon_startup_options_lst = get_deamon__startup_options(p_log_fun,
								p_docker_port_str                      = p_docker_port_str,
								p_docker_host_labels_lst               = p_docker_host_labels_lst,
								p_docker_kv_store__etcd__host_port_str = p_docker_kv_store__etcd__host_port_str)
		assert isinstance(deamon_startup_options_lst,list)

		deamon_startup_options_str = ' '.join(deamon_startup_options_lst)
		#store Docker startup options, for the docker deamon to pick up on its startup (when the node boots up)
		#IMPORTANT!! - '\\"' - in python to escape '"' you have to use a double slash '\\'
		s = r'''echo DOCKER_OPTS=\\"%s\\" >> %s'''%(deamon_startup_options_str,
						p_docker_config_path_str)

		p_fab_api.run('service docker stop') #docker is running by default
		p_fab_api.run(s)
		p_fab_api.run('service docker start')
#---------------------------------------------------
def install_base_docker(p_fab_api,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_docker.install_base_docker()')

	p_fab_api.run('apt-key adv --keyserver hkp://pgp.mit.edu:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D')
	p_fab_api.run('sh -c "echo deb https://apt.dockerproject.org/repo ubuntu-vivid main > /etc/apt/sources.list.d/docker.list"')
	p_fab_api.run('apt-get update')
	#p_fab_api.run('apt-get purge lxc-docker*')
	p_fab_api.run('apt-get install -y docker-engine')
#---------------------------------------------------
def start_deamon(p_log_fun):
	p_log_fun('FUN_ENTER','gf_docker.start_deamon()')

	cmd_str = get_deamon__startup_cmd(p_log_fun)
#---------------------------------------------------
#->:String
def get_deamon__startup_cmd(p_log_fun):
	p_log_fun('FUN_ENTER','gf_docker.get_deamon__startup_cmd()')

	c_lst = [
		'sudo',
		'docker',
		'-d',
	]
	startup_options_lst = get_deamon__startup_options(p_log_fun)
	c_lst.extend(startup_options_lst)

	c_str = ' '.join(c_lst)
	return c_str
#---------------------------------------------------
#->:List<:String>
def get_deamon__startup_options(p_log_fun,
			p_docker_port_str                      = '2375',
			p_docker_host_labels_lst               = None,
			p_docker_kv_store__etcd__host_port_str = '127.0.0.1:2379'):
	p_log_fun('FUN_ENTER','gf_docker.get_deamon__startup_options()')

	args_lst = [
		#DOCKER HOST LISTEN ON
		#IMPORTANT!! - "-H 0.0.0.0:x" - this makes th docker installed on this node accessible 
		#                               by a SWARM master (for example, or any external Docker client).
		'-H 0.0.0.0:%s'%(p_docker_port_str),
		'-H unix://var/run/docker.sock',

		#IMPORTANT!! - used for docker networkking 'overlay' driver
		'--cluster-store=etcd://%s'%(p_docker_kv_store__etcd__host_port_str),

		'--cluster-advertise=etcd://%s'%(p_docker_kv_store__etcd__host_port_str)
	]

	#-------------------
	#DEAMON_LABELS
	if p_docker_host_labels_lst:
		assert isinstance(p_docker_host_labels_lst,list)
		docker_label_args_lst = ['--label %s=%s'%(k,v) for k,v in p_docker_host_labels_lst]
		args_lst.extend(docker_label_args_lst)
	#-------------------

	return args_lst