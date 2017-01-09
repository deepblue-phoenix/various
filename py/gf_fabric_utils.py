#README - utility functions for working with remote servers via the Fabric library (SSH)

import sys,os
import inspect
import getpass

import cuisine

import gf_node_phy_adt
#---------------------------------------------------
#Since the env vars are checked for each task, this means that if 
#you have the need, you can actually modify env in 
#one task and it will affect all following tasks

#p_node_host_type_to_use_str - node's can have different hosts associated with them
#                              'public'|'private'

#->:List<:String(fabric_format_host_str)>
def register_node_phys_with_fabric(p_node_phys_lst,
			p_fab_api,
			p_log_fun,
			p_assign_group_name_str     = None,
			p_node_host_type_to_use_str = 'public'):
	p_log_fun('FUN_ENTER','gf_fabric_utils.register_node_phys_with_fabric()')

	fabric_hosts_lst = []
	for node_phy_adt in p_node_phys_lst:
		assert isinstance(node_phy_adt,gf_node_phy_adt.NodePhy_ADT)
			
		p_log_fun('INFO','*****************-------------------------------------*****************')
		p_log_fun('INFO','registering node [%s] - %s'%(node_phy_adt.name_str,
										node_phy_adt))
		p_log_fun('INFO','node_phy_adt.hosts_dict:%s'%(node_phy_adt.hosts_dict))

		#target_node_host_str - can be None, if that host has not been assigned to a node yet
		target_node_host_str = node_phy_adt.hosts_dict[p_node_host_type_to_use_str]
		assert not target_node_host_str == None
		
		#format expected by fabric
		#assumes a connection port 22 (ssh)
		fabric_host_str = '%s@%s'%(node_phy_adt.user_str,
					target_node_host_str)
		
		fabric_hosts_lst.append(fabric_host_str)	
		
	#ATTENTION!! - env.hosts mechanisms depends on the "fab" cmd-line tool
	#fabric checks the environment singleton dict to see who to connect to
	p_fab_api.env.hosts = fabric_hosts_lst
	
	
	if not p_assign_group_name_str == None:
		assert isinstance(p_assign_group_name_str,basestring)
		
		#"roledefs" - registers with fabric a list of hosts that is to be then
		#             referenced with fabric by a single name string (p_assign_group_name_str)
		p_fab_api.env.roledefs[p_assign_group_name_str] = hosts_lst
		
		
	return fabric_hosts_lst
#---------------------------------------------------	
def run_task_on_node_phys(p_task_fun,
		p_node_phys_adts_lst,
		p_fab_api,
		p_log_fun,

		p_run_tasks_in_parallel_bool = True,
		p_verbose_bool               = True,
		p_node_host_type_to_use_str  = 'public'):
	p_log_fun('FUN_ENTER','gf_fabric_utils.run_task_on_node_phys()')
	assert inspect.isfunction(p_task_fun)
	assert isinstance(p_node_phys_adts_lst,list)
	
	if p_run_tasks_in_parallel_bool: p_fab_api.env.parallel = True
	
	#registers these node_phy's to be connected to, 
	#:List<:String(fabric_format_host_str)>
	fabric_format_hosts_lst = register_node_phys_with_fabric(p_node_phys_adts_lst,
								p_fab_api,
								p_log_fun,
								p_node_host_type_to_use_str = p_node_host_type_to_use_str)
	assert isinstance(fabric_format_hosts_lst,list)
	
	#-------------------
	#ATTENTION!! - execute() avoids the need for using the 'fab' cmd_line tool
	#execute the profile installation task, on a series of hosts
	#all_hosts_return_vals_map - :Dict<key:String(host_str),:String(task_std_out_str)>
	#                             a dict of standard outputs of each task run, 
	#                             per host supplied in "hosts" argument
	all_hosts_return_vals_map = p_fab_api.execute(p_task_fun,
								hosts = fabric_format_hosts_lst)
	assert isinstance(all_hosts_return_vals_map,dict)
	#-------------------

	#turn off parallel execution when finished 
	#(so that other tasks that are run have a default setup)
	if p_run_tasks_in_parallel_bool: p_fab_api.env.parallel = False
	
	if p_verbose_bool == True:
		for host_str,host_std_output_str in all_hosts_return_vals_map.items():
			p_log_fun('INFO','************************************-------------------------------')
			p_log_fun('INFO','fabric task run output')
			p_log_fun('INFO','host_str           :%s'%(host_str))
			p_log_fun('INFO','host_std_output_str:%s'%(host_std_output_str))
#---------------------------------------------------
#setting passwords on a per-host basis
#env.hosts     = ['user1@host1:port1', 'user2@host2.port2']
#env.passwords = {'user1@host1:port1': 'password1', 'user2@host2.port2': 'password2'}
#---------------------------------------------------
def switch_to_user(p_fab_api,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_fabric_utils.switch_to_user()')
	user_str = raw_input('user name:')
	pass_str = getpass.getpass()

	p_fab_api.env.user     = user_str
	p_fab_api.env.password = pass_str
#---------------------------------------------------
def switch_and_prompt_to_user(p_node_phys_lst,
					p_fab_api,
					p_log_fun):
	p_log_fun('FUN_ENTER','gf_fabric_utils.switch_and_prompt_to_user()')
	assert isinstance(p_node_phys_lst,list)
	
	user_str = raw_input('user name:')
	pass_str = getpass.getpass()
	
	switch_fab_to_user(p_node_phys_lst,
				user_str,
				pass_str,
				p_fab_api,
				p_log_fun)
#---------------------------------------------------
#all local

def switch_fab_to_user(p_node_phys_lst,
		p_user_str,
		p_pass_str,
		p_fab_api,
		p_log_fun):
	p_log_fun('FUN_ENTER','gf_fabric_utils.switch_fab_to_user()')
	
	p_fab_api.env.user     = p_user_str
	p_fab_api.env.password = p_pass_str
	
	for node_phy_adt in p_node_phys_lst:
		assert isinstance(node_phy_adt,gf_node_phy_adt.NodePhy_ADT)
		
		node_phy_adt.user_str = p_user_str
		node_phy_adt.pass_str = p_pass_str
#---------------------------------------------------	
def kill_remote_processes(p_fab_api,
			p_process_name,
			p_log_fun):
	p_log_fun('FUN_ENTER','gf_fabric_utils.kill_remote_processes()')
	p_log_fun('INFO'     ,'p_process_name:%s'%(p_process_name))
	
	proc_killed_bool = False
	output_str       = p_fab_api.run('ps -ef')
	
	for line in output_str.split('\n'):
		
		if p_process_name in line: 

			#"line"                 - example - "root     20161     1  0 Aug29 ?        00:07:57 gf_publisher_posts_service  "
			#"line.strip().split()" - example - ['root','20161','1','0','Aug29','?','00:07:57','gf_publisher_posts_service']
			pid = line.strip().split()[1]
			p_log_fun('INFO','found %s process with pid:%s'%(p_process_name,pid))
			
			p_fab_api.sudo('kill -9 %s'%(pid))
			proc_killed_bool = True
			
	if proc_killed_bool: p_log_fun('INFO','SUCCESS - remote process [%s] killed'%(p_process_name))
	else               : p_log_fun('INFO','WARNING - no remote process [%s] found'%(p_process_name))
#---------------------------------------------------
def run_remote_background_process(p_fab_api,
		p_command_to_run, 
		p_out_file, 
		p_err_file,
		p_log_fun,
		p_shell    = True, 
		p_pty      = False):
	p_log_fun('FUN_ENTER','gf_fabric_utils.run_remote_background_process()')
	p_log_fun('INFO'     ,'p_command_to_run:%s'%(p_command_to_run))
	

	cuisine.dir_ensure(os.path.dirname(p_out_file),recursive=True)
	cuisine.file_ensure(p_out_file)

	cuisine.dir_ensure(os.path.dirname(p_err_file),recursive=True)
	cuisine.file_ensure(p_err_file)
	
	#nohup is a POSIX command to ignore the HUP (hangup) signal, 
	#enabling the command to keep running after the user who 
	#issues the command has logged out. The HUP (hangup) signal is 
	#by convention the way a terminal warns depending processes of logout.
	
	#streams stdout/stderr to the out_file/err_file
	
	command_str = 'nohup %s >%s 2>%s </dev/null &' % (p_command_to_run, 
									p_out_file, 
									p_err_file or '&1')
	out = p_fab_api.run(command_str, 
				p_shell, 
				p_pty)
	return out
#---------------------------------------------------
def setup_user(p_user_name_str,
	p_user_home_dir_path_str,
	p_user_pass_str,
	p_log_fun):
	p_log_fun('FUN_ENTER','gf_fabric_utils.setup_user()')
	
	#Ensures that the given users exists, optionally updating their
	#passwd/home/uid/gid/shell.
	cuisine.user_ensure(p_user_name_str,
			home   = p_user_home_dir_path_str,
			passwd = p_user_pass_str)
#-------------------------------------------------------------
def set_ownergroup_and_readexec_privilages_on_dir(p_user_name_str,
									p_group_name_str,
									p_remote_dir_path_str,
									p_fab_api,
									p_log_fun):
	p_log_fun('FUN_ENTER','gf_fabric_utils.set_ownergroup_and_readexec_privilages_on_dir()')
	
	#updating of code files happens as "root" user, so here we have to set privilages for the 
	#actual user which will read the files
	p_fab_api.run('chown -R %s:%s %s'%(p_user_name_str,
									   p_group_name_str,
									   p_remote_dir_path_str))
	p_fab_api.run('chmod a-rwx -R %s'%(p_remote_dir_path_str)) #first remove all privilages for everyone
	p_fab_api.run('chmod u+rx -R %s'%(p_remote_dir_path_str))  #then add readexecut-only privilages only for the owner
#-------------------------------------------------------------
def set_ownergroup_and_readexec_privilages_on_file(p_user_name_str,
						p_group_name_str,
						p_remote_file_path_str,
						p_fab_api,
						p_log_fun):
	p_log_fun('FUN_ENTER','gf_fabric_utils.set_ownergroup_and_readexec_privilages_on_file()')
	
	#updating of code files happens as "root" user, so here we have to set privilages for the 
	#actual user which will read the files
	p_fab_api.run('chown %s:%s %s'%(p_user_name_str,
								    p_group_name_str,
								    p_remote_file_path_str))
	p_fab_api.run('chmod a-rwx %s'%(p_remote_file_path_str)) #first remove all privilages for everyone
	p_fab_api.run('chmod u+rx %s'%(p_remote_file_path_str))  #then add readexecut-only privilages only for the owner