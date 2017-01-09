#README - utility functions for dumping mongodb data to row-based text files

import os
import datetime
import cuisine
import gf_fabric_utils
#-------------------------------------------------------------
#->:Dict
def get_remote_db_dump(p_target_node_phys_lst,
		p_fab_api,
		p_log_fun,
		p_parallel_bool = False):
	p_log_fun('FUN_ENTER','gf_ops_data_dump.get_remote_db_dump()')
	
	meta_props_map       = gf_ops_meta.get_meta_props(p_log_fun)
	results_per_host_map = {}
	#-------------------------------------------------------------
	def task():
		p_log_fun('FUN_ENTER','gf_ops_data_dump.get_remote_db_dump().task()')
		
		current_host_str = str(p_fab_api.env.host_string.split('@')[1])
		p_log_fun('INFO','current_host_str:%s'%(current_host_str))
			
		current_datetime_str         = datetime.datetime.now().isoformat()
		remote_db_dump_file_path_str = '%s/db_dump.txt+%s+%s'%(meta_props_map['remote_db_data_root_dir_path_str'],
										current_datetime_str,
										current_host_str)
		#------------
		#DOWNLOAD DB DUMP FILE

		args_lst = [
			'-run=dump_db_to_file',
			'-db_file_path=%s'%(remote_db_dump_file_path_str)
		]
		args_str = reduce(lambda p_accum_str,p_arg_str:'%s %s'%(p_accum_str,p_arg_str),
				args_lst)
		
		#"gf_data_tool_cmdline" - is a part of the gf_common application server modules
		remote_gf_data_tool_py_module_path_str = '%s/gf_common/gf_data_tool_cmdline.pyc'%(meta_props_map['remote_apps_server_code_root_dir_path_str'])
		cuisine.file_is_file(remote_gf_data_tool_py_module_path_str)
		
		remote_command_str = 'python %s %s'%(remote_gf_data_tool_py_module_path_str,
								args_str)
		
		p_fab_api.run(remote_command_str)
		p_fab_api.get(remote_db_dump_file_path_str,
				meta_props_map['local_db_data_root_dir_path_str'])
		#------------
		
		local_db_dump_file_path_str = '%s/%s'%(meta_props_map['local_db_data_root_dir_path_str'],
										os.path.basename(remote_db_dump_file_path_str))
		
		
		results_per_host_map[current_host_str] = {
			'local_db_dump_file_path_str':local_db_dump_file_path_str
		}
	#-------------------------------------------------------------
	
	gf_fabric_utils.run_task_on_node_phys(task,        #p_task_fun,
					p_target_node_phys_lst, #p_node_phys_adts_lst,
					p_fab_api,
					p_log_fun,

					p_run_tasks_in_parallel_bool = p_parallel_bool,
					p_verbose_bool               = True)
	return results_per_host_map
#-------------------------------------------------------------
#->:Dict
def get_latest_date_archived_db_dumps(p_local_db_data_root_dir_path_str,
						p_log_fun):
	p_log_fun('FUN_ENTER','gf_ops_data_dump.get_latest_date_archived_db_dumps()')

	#:List<:Dict>
	db_dumps_infos_lst = list_all_archived_remote_db_dumps(p_local_db_data_root_dir_path_str,
									p_log_fun,
									p_count_dump_file_lines_bool = False,
									p_vis_bool                   = False)
	assert isinstance(db_dumps_infos_lst,list)
	assert len(db_dumps_infos_lst) > 0

	#-------------------------------------------------------------
	def group_dumps_by_ip():
		dumps_by_ip_map = {}
		for dump_map in db_dumps_infos_lst:
			assert dump_map.has_key('db_server_ip_str')
			ip_str = dump_map['db_server_ip_str']

			if dumps_by_ip_map.has_key(ip_str):
				dumps_by_ip_map[ip_str].append(dump_map)
			else:
				dumps_by_ip_map[ip_str] = [dump_map]
		return dumps_by_ip_map
	#-------------------------------------------------------------
	dumps_by_ip_map = group_dumps_by_ip()


	results_map = {}
	for ip_str,dumps_lst in dumps_by_ip_map.items():

		#sort all dumps (per node) by date
		sorted_by_date_lst = sorted(dumps_lst,
						key     = lambda p_dump_info_map:p_dump_info_map['dump_creation_date_str'],
						reverse = True)
		latest_dump_map = sorted_by_date_lst[0]

		assert isinstance(latest_dump_map,dict)
		assert latest_dump_map.has_key('file_path_str')
		latest_dump_file_path_str = latest_dump_map['file_path_str']

		#------------
		#IMPORTANT!!
		#this is the same formated as results of get_remote_db_dump(), 
		#so that they can be used interchangably in other places

		results_map[ip_str] = {
			'local_db_dump_file_path_str':latest_dump_file_path_str
		}
		#------------

	return results_map
#-------------------------------------------------------------
#->:List<:Dict>
def list_all_archived_remote_db_dumps(p_local_db_data_root_dir_path_str,
				p_log_fun,
				p_count_dump_file_lines_bool = True,
				p_vis_bool                   = False):
	p_log_fun('FUN_ENTER','gf_ops_data_dump.list_all_archived_remote_db_dumps()')
	assert os.path.isdir(p_local_db_data_root_dir_path_str)

	#-------------------------------------------------------------
	#->:Dict
	def process_db_dump_file(p_file_path_str):
		#p_log_fun('FUN_ENTER','gf_ops_data_dump.list_all_archived_remote_db_dumps().process_db_dump_file()')

		file_name_str = os.path.basename(p_file_path_str)
		dump_info_lst = file_name_str.split('+')

		assert isinstance(dump_info_lst,list)

		#-------------------------------------------------------------
		#ATTENTION!! - time consuming operation

		def count_file_lines(p_file_path_str):
			p_log_fun('INFO','counting file lines of [%s]'%(os.path.basename(p_file_path_str)))

			#'i' var accumulates the (index,file_line) index value enumerated 
			# by the enumerate() generator
			with open(p_file_path_str) as f:
				
				#enumerate(sequence, start=0) - Return an enumerate object
				#next() - method of the iterator returned by enumerate() returns a tuple 
				#         containing a count (from start which defaults to 0) and the values 
				#         obtained from iterating over sequence:
				for i, l in enumerate(f):
					pass

			return i + 1
		#-------------------------------------------------------------

		#new db_dump format
		if (len(dump_info_lst) == 3):
			dump_creation_date_str = dump_info_lst[1]
			db_server_ip_str       = dump_info_lst[2]
			dump_file_size_bytes   = os.path.getsize(p_file_path_str)
			
			dump_file_info_map = {
				'file_path_str'         :p_file_path_str,
				'dump_creation_date_str':dump_creation_date_str,
				'db_server_ip_str'      :db_server_ip_str,
				'dump_file_size_bytes'  :dump_file_size_bytes
			}

			if p_count_dump_file_lines_bool:
				dump_file_lines_num                       = count_file_lines(p_file_path_str)
				dump_file_info_map['dump_file_lines_num'] = dump_file_lines_num

			return dump_file_info_map
		else:
			return None
	#-------------------------------------------------------------

	valid_db_dumps_infos_lst = [] #:List<:Dict>
	for f_str in os.listdir(p_local_db_data_root_dir_path_str):
		full_file_path_str = os.path.join(p_local_db_data_root_dir_path_str,f_str)

		if os.path.isfile(full_file_path_str) and f_str.startswith('db_dump.txt'):
			db_dump_info_map = process_db_dump_file(full_file_path_str)

			if isinstance(db_dump_info_map,dict):
				valid_db_dumps_infos_lst.append(db_dump_info_map)

	if p_vis_bool:
		gf_ops_db_vis.view_db_dumps_stats(valid_db_dumps_infos_lst,
					p_log_fun)

	return valid_db_dumps_infos_lst
#-------------------------------------------------------------
def load_db_dump_into_remote_db(p_log_fun):
	p_log_fun('FUN_ENTER','gf_ops_data_dump.load_db_dump_into_remote_db()')