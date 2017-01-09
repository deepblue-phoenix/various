#README - getting basic stats on DB dumps

import json
#---------------------------------------------------
#FIX!! - change from 'view' to 'list'

def view_db_dumps_stats(p_db_dumps_infos_lst,
						p_log_fun):
	p_log_fun('INFO','gf_ops_db_stats.view_db_dumps_stats()')

	#---------------------------------------------------
	#->:Dict
	def group_dump_creation_dates_by_ip():
		p_log_fun('INFO','gf_ops_db_stats.view_db_dumps_stats().group_dump_creation_dates_by_ip()')

		db_dumps_by_ip_map = {}
		for db_dump_info_map in p_db_dumps_infos_lst:
			assert isinstance(db_dump_info_map,dict)

			dump_ip_str        = db_dump_info_map['db_server_ip_str']
			db_dumps_of_ip_lst = db_dumps_by_ip_map.get(dump_ip_str,[])

			db_dumps_of_ip_lst.append(db_dump_info_map)
			db_dumps_by_ip_map[dump_ip_str] = db_dumps_of_ip_lst

		return db_dumps_by_ip_map
	#---------------------------------------------------
	def show(p_dumps_infos_by_ip_map):
		p_log_fun('INFO','gf_ops_db_stats.view_db_dumps_stats().show()')

		for k,v in p_dumps_infos_by_ip_map.items():
			dumps_ip_str               = k
			dumps_infos_lst            = v #:List<:Dict>

			assert isinstance(dumps_ip_str   ,basestring)
			assert isinstance(dumps_infos_lst,list)

			db_dumps_infos_by_date_lst = sorted(dumps_infos_lst,
												key    =lambda p_dump_info_map:p_dump_info_map['dump_creation_date_str'],
												reverse=True)

			p_log_fun('INFO','DB SERVER IP - [%s] ***********'%(dumps_ip_str))
			for db_dump_info_map in db_dumps_infos_by_date_lst:
				
				assert isinstance(db_dump_info_map,dict)
				assert db_dump_info_map.has_key('dump_creation_date_str')
				assert db_dump_info_map.has_key('dump_file_size_bytes')
				assert db_dump_info_map.has_key('dump_file_lines_num')

				#full format: "2014-04-14T02:12:27.142911"
				date_str,time_str       = db_dump_info_map['dump_creation_date_str'].split('T')
				short_time_str          = time_str.split('.')[0]
				short_creation_date_str = '%s - %s'%(date_str,short_time_str)

				p_log_fun('INFO','%s -- lines # [%s] -- size KB [%s]'%(short_creation_date_str,
																	   db_dump_info_map['dump_file_lines_num'],
																	   db_dump_info_map['dump_file_size_bytes']/1024))

	#---------------------------------------------------
	dump_creation_dates_by_ip_map = group_dump_creation_dates_by_ip()
	show(dump_creation_dates_by_ip_map)
#---------------------------------------------------	
def list_local_prod_db_stats(p_db_context_map,
						p_log_fun,
						p_db_type_str          = 'mongo',
						p_log_cmd_updates_bool = False):
	p_log_fun('INFO','gf_ops_db_stats.list_local_prod_db_stats()')

	#---------------------------------------------------
	def run_mongo():
		p_log_fun('INFO','gf_ops_db_stats.list_local_prod_db_stats().run_mongo()')

		#production DB
		data_coll = p_db_context_map['mongodb_client']['prod_db']['data']

		prefix_counts_map = {}
		i                  = 0

		#GET ALL DOCUMENTS
		#data_coll.find({},{"_id":1}) - lazily get only keys of all documents in the collection
		for doc_map in data_coll.find({},{"_id":1}):
			assert doc_map.has_key('_id')

			key_str        = doc_map['_id']
			key_prefix_str = key_str.split(':')[0]

			prefix_count_int                  = prefix_counts_map.get(key_prefix_str,0)
			prefix_counts_map[key_prefix_str] = prefix_count_int + 1

			#----------------
			#CMD_UPDATE

			#IMPORTANT!! - there are potentially huge number of docs. 
			#              for every so many docs this will emit a log message
			#              that will be used by some command runner user/tool. 

			#'%' returns 0 when the first operator is divisible by the second
			block_size_int = 1000
			if i%block_size_int == 0:
				
				if p_log_cmd_updates_bool:
					cmd_update_map = {
						#this is a STATUS update
						'status_map':{
							'current_doc_block_int':i/block_size_int
						}
					}
					p_log_fun('CMD_UPDATE',json.dumps(cmd_update_map))
			#----------------

			i+=1

		p_log_fun('INFO','-------------------------------------------------')
		p_log_fun('INFO','key_prefix counts:')
		p_log_fun('INFO','')
		
		sorted_kv_prefix_counts_lst = sorted(prefix_counts_map.items(),
											key     = lambda p_kv:p_kv[1],
											reverse = True)

		#reverse=True - so larger numbers are first
		for key_prefix_str,keys_count_int in sorted_kv_prefix_counts_lst:

			p_log_fun('INFO','%s - %s'%(key_prefix_str,keys_count_int))

			#----------------
			#CMD_UPDATE

			if p_log_cmd_updates_bool:
				cmd_update_map = {
					#this is a DATA update
					'data_map':{
						'key_prefix_str':key_prefix_str,
						'keys_count_int':keys_count_int
					}
				}
				p_log_fun('CMD_UPDATE',json.dumps(cmd_update_map))
			#----------------
	#---------------------------------------------------

	if p_db_type_str == 'mongo':
		run_mongo()