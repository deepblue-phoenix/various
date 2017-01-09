#README - utility functions for the Tornado HTTP web-server for my own web-server Py library

import os,sys
import json
import urllib
import gf_error
import gf_rpc_server_meta
import gf_rpc_server_discovery
import http_tornado_session
import http_tornado_utils
#----------------------------------------------
#bert_encoder = BERTEncoder()
#bert_decoder = BERTDecoder()
#----------------------------------------------
#this is what handles the actuall HTTP request
def request_wrapper(p_handler_adt,          #:Handler_adt
		p_tornado_handler_self, #:tornado.web.RequestHandler
		p_req_type,             #:String - "GET"|"POST"
		p_sys_args_map,

		p_db_context_map,
		p_log_fun,
		p_allow_cross_domain_use_bool = True):
	p_log_fun('FUN_ENTER','http_tornado_req_handler.request_wrapper()')
	p_log_fun('INFO'     ,'request uri:%s'%(p_tornado_handler_self.request.uri))
	
	#------------------
	meta_props_map = gf_rpc_server_meta.get_meta_props(p_log_fun)
	#------------------
	
	try:
		encoding_type_str = get_encoding(p_tornado_handler_self,
					p_log_fun)
	except Exception as e:
		#-----------------------
		#ERROR HANDLING
		
		error_msg_str  = meta_props_map['unsupported_encoding_internal_error_msg']
		error_user_msg = meta_props_map['unsupported_encoding_user_error_msg']
		
		request_supplied_encoding_str = e.args[0]
		p_log_fun('INFO','request_supplied_encoding_str:%s'%(request_supplied_encoding_str))

		http_tornado_utils.tornado_handle_exception(e,                #p_exception,                         
					error_msg_str,                    #p_formated_msg_str,
					(request_supplied_encoding_str,), #p_surrounding_context_attribs_tpl,
					error_user_msg,                   #p_extern_user_msg,
					(request_supplied_encoding_str,), #p_surrounding_context_attribs_tpl,
					p_tornado_handler_self,           #p_req_hndlr_self,
					p_log_fun)
		return 
		#-----------------------
		
	try:
		#--------
		#GET HTTP REQUEST ARGS
		http_args_map = {}

		req_args_map = extract_req_args(p_handler_adt,
					encoding_type_str,
					p_tornado_handler_self,
					p_log_fun)
		
	except Exception as e:
		#-----------------------
		#ERROR HANDLING
		
		error_msg_str  = meta_props_map['invalid_request_args_internal_error_msg_str']
		error_user_msg = meta_props_map['invalid_request_args_user_error_msg_str']
		
		http_tornado_utils.tornado_handle_exception(e,              #p_exception,                         
						error_msg_str,          #p_formated_msg_str,
						(),                     #p_surrounding_context_attribs_tpl,
						error_user_msg,         #p_extern_user_msg,
						(),                     #p_user_msg_surrounding_context_attribs_tpl
						p_tornado_handler_self, #p_req_hndlr_self,
						p_log_fun)
		return 
		#-----------------------
		
	#--------	
	#run the custom user handler with decoded data
	
	try:
		#--------------------
		#SESSION HANDLING
		#Like other headers, cookies must be sent before any output from your script (this is a protocol restriction).
		
		session_id_str = http_tornado_session.get_session_id(p_tornado_handler_self,
										p_db_context_map,
										p_log_fun)
		#the extracted session_id is appended to request arguments, so that the user has access to it
		req_args_map['session_id_str'] = session_id_str
		session_info_map               = http_tornado_session.get_session_info(session_id_str,
		                                                    			p_tornado_handler_self,
																		p_db_context_map,
																		p_log_fun)
		req_args_map['session_info_map'] = session_info_map
		#--------------------
		
		#----------------------------------------------
		def onComplete_fun(p_result):
			p_log_fun('INFO','USER HANDLER COMPLETE')
			#----------------
			#HTML5 CORS - Cross-Origin Resource Sharing
			
			if p_allow_cross_domain_use_bool == True:
				
				#ADD!! - besides allowing global access to anyone, instead of '*'
				#        use a specific origin/domain to allow select clients access
				#        to services
				
				#'*' - value makes the API/URL public to anyone on the web
				p_tornado_handler_self.set_header('Access-Control-Allow-Origin','*')
			#----------------
			
			#commands are in tuple form
			if isinstance(p_result,tuple):
				if p_result[0] == 'redirect':
					handle_redirect(p_result,
							p_tornado_handler_self,
							p_log_fun)
				elif result[0] == 'no_response':
					p_tornado_handler_self.finish()
			else:	
				#if the result is not a tuple(command) then it should be a dict
				assert isinstance(p_result,dict)

				response_map = {
					'status':'OK',
					'data'  :p_result
				}
				
				#encode and send results back to client
				encoded_response = encode_usr_handler_output(response_map,
									encoding_type_str,
									p_tornado_handler_self,
									p_log_fun)
	
				p_tornado_handler_self.write(encoded_response)
				p_tornado_handler_self.finish()
				
			#--------------------
			#SESSION HANDLING
			
			p_log_fun('INFO','SETTING SESSION INFO')
			p_log_fun('INFO','session_id_str   :%s'%(session_id_str))
			p_log_fun('INFO','session_info_map:%s'%(session_info_map))

			http_tornado_session.set_session_info_in_db(session_id_str,
								session_info_map,
								p_db_context_map,
								p_log_fun)
			#--------------------
		#----------------------------------------------
		
		#p_log_fun - this passed in log_fun is the system log_fun. 
		#						 handlers can use other log_fun's which can have other log targets. '''
		p_handler_adt.usr_handler_fun(req_args_map,
					p_sys_args_map,

					p_db_context_map,
					onComplete_fun,
					p_log_fun)
		
		#--------------------
	except Exception as e:
		#-----------------------
		#ERROR HANDLING
		
		error_msg_str  = meta_props_map['user_handler_failed_internal_error_msg_str']
		error_user_msg = meta_props_map['user_handler_failed_user_error_msg_str']
		
		surrounding_context_attribs_tpl = (p_handler_adt.name_str,)
		
		http_tornado_utils.tornado_handle_exception(e,   #p_exception,                         
						error_msg_str,                   #p_formated_msg_str,
						surrounding_context_attribs_tpl,
						error_user_msg,                  #p_extern_user_msg,
						(),                              #p_user_msg_surrounding_context_attribs_tpl
						p_tornado_handler_self,          #p_req_hndlr_self,
						p_log_fun)
		return 
		#-----------------------
#----------------------------------------------
def handle_redirect(p_usr_handler_result_tpl,
		p_tornado_handler_self,
		p_log_fun):
	p_log_fun('FUN_ENTER','http_tornado_req_handler.handle_redirect()')
	redirect_type = p_usr_handler_result_tpl[1]
	
	#simple general-http redirect
	#('redirect','url','http://someurl')
	if redirect_type == 'url':
		url_to_redirect_to = p_usr_handler_result_tpl[2]
		assert isinstance(url_to_redirect_to,basestring)
		
		p_tornado_handler_self.redirect(url_to_redirect_to)
	
	#IMPORTANT!! - redirecting to the current servers
	#gf_rpc_server redirect
	#('redirect','mf','server_name','module_name','fun_name',args_map)
	elif redirect_type == 'mf':
		server_name = p_usr_handler_result_tpl[2]
		module_name = p_usr_handler_result_tpl[3]
		fun_name    = p_usr_handler_result_tpl[4]
		args_map    = p_usr_handler_result_tpl[5]
		assert isinstance(args_map,dict)
		
		servers_info_lst = gf_rpc_server_discovery.get_server_info(server_name,
											p_log_fun)
		
		#FIX!! - there is no load balancing here in case multiple server info's 
		#        are returned in servers_info_lst, or any kind of performance check 
		#        (where a server on the same host, or host close by, would be picked to minimize
		#         network latency).
		server_info_map = server_info_lst[0]
		
		
		args_str  = urllib.urlencode(args_map)
		final_url = '%s:%s/%s/%s?%s'%(server_info_map['host'],
						server_info_map['port'],
						module_name,
						fun_name,
						args_str)
		
		p_tornado_handler_self.redirect(final_url)
#----------------------------------------------
#->:Dict
def extract_req_args(p_handler_adt,
		p_encoding_type_str,
		p_tornado_handler_self,
		p_log_fun):
	p_log_fun('FUN_ENTER','http_tornado_req_handler.extract_req_args()')
	
	#user handlers can access the encoding type
	args_map = {'e':p_encoding_type_str}
	
	#print dir(p_tornado_handler_self.request)
	#print p_tornado_handler_self.request.method
	#print p_tornado_handler_self.cookies.values()
	#print p_tornado_handler_self.request.version #http version used
	#print p_tornado_handler_self.request.body
	#print p_tornado_handler_self.request.arguments
	#print p_tornado_handler_self.get_argument('e')
	#print p_tornado_handler_self.request.headers

	#GET puts all user data in the 'd' url argument
	if p_tornado_handler_self.request.method == 'GET':
		data = p_tornado_handler_self.get_argument('d',None)
		p_log_fun('INFO','HTTP GET - data [%s]'%(data))
		
	#POST puts all user data in its body, while the gf_rpc_server related
	#arguments still go into the url arguments
	elif p_tornado_handler_self.request.method == 'POST':
		#data = p_tornado_handler_self.get_argument('d',None)
		data = p_tornado_handler_self.request.body
		p_log_fun('INFO','HTTP POST - data [%s]'%(data))
		
	else:
		data = None
		
	if not data == None:
		decoded_data_map = decode_data(p_encoding_type_str,
				data,
				p_tornado_handler_self,
				p_log_fun)
		
		p_log_fun('INFO','decoded_data_map:%s'%(decoded_data_map))
		
		#argument extraction
		for (arg_name,arg_default_value) in p_handler_adt.args_spec_lst:
			
			#first try to extract the argument via tornado, either from 
			#url arguments, or post body arguments
			arg_val = p_tornado_handler_self.get_argument(arg_name,
														None)
			if arg_val == None:
				 
				#if the arg does not exist as a standard GET/POST argument, then 
				#its looked for in the decoded data-argument
				if decoded_data_map.has_key(arg_name):
					arg_val = decoded_data_map[arg_name]
				else: 
					#if the arg is not supplied in the decode data-argument 
					#then the default user supplied value is assigned
					arg_val = arg_default_value
	
			args_map[arg_name] = arg_val
			
	#if the data-argument is not supplied in the request, then arguments are only extracted
	#from standard GET/POST arguments
	else:
		for (arg_name,arg_default_value) in p_handler_adt.args_spec_lst:
			 arg_val = p_tornado_handler_self.get_argument(arg_name,
													arg_default_value)		
			 args_map[arg_name] = arg_val
		 
	return args_map
#----------------------------------------------
#:String
def get_encoding(p_tornado_handler_self,
		p_log_fun):
	p_log_fun('FUN_ENTER','http_tornado_req_handler.get_encoding()')
	
	#in the erl/js rpc_server the encoding is not extracted in the http backend
	#(like it is here - this is done because in tornado the arguments are extracted from the 
	# self instance of the request handler, which is best encapsulated in the http backend.
	#I havent found a way to get all arguments and then iterate ver these in general rpc_server)'''
	#IMPORTANT!! - encoding is always specified as a URL argument
	encoding_type = p_tornado_handler_self.get_argument('e', 
						'json') #p_default_encoding   
	
	#-----------------------
	#ERROR HANDLING
		
	meta_props_map = gf_rpc_server_meta.get_meta_props(p_log_fun)
	
	#throw Exception if an unsupported encoding is specified by the client
	if not encoding_type in meta_props_map['supported_encodings_lst']:				 
		raise Exception(encoding_type)
	#-----------------------
	
	return encoding_type
#----------------------------------------------
#decodes the p_args_map['d'] argument and places the result back into p_args_map['d']

#->:Dict|:String('error')
def decode_data(p_encoding_type,
		p_encoded_data,
		p_tornado_handler_self,
		p_log_fun):
	p_log_fun('FUN_ENTER','http_tornado_req_handler.decode_data()')
	p_log_fun('INFO'     ,'p_encoded_data:%s'%(p_encoded_data))
	
	try:
		if p_encoding_type == 'json':			
			decoded_data_map = json.loads(str(p_encoded_data))
			return decoded_data_map
			
		#elif p_encoding_type == 'bert':
		#	decoded_data_map = bert_encoder.decode(p_encoded_data)
		#	return decoded_data_map
	except Exception as e:
		#-----------------------
		#ERROR HANDLING
		
		#FIX!! - calling get_meta_props() for each request is innefficient
		error_msg_str = gf_rpc_server_meta.get_meta_props(p_log_fun)['decoding_error_msg']

		gf_error.handle_exception(e,       #p_exception,
				error_msg_str, #p_formated_msg_str,
				(),            #p_surrounding_context_attribs_tpl,
				p_log_fun)
		raise #throw the exception last cought
		#-----------------------
#----------------------------------------------
#encoding is always done, regardles of if 'data' HTTP argument is passed in or not

#->:String('error'|encoded_result_str(json_data))|:Binary(encoded_result_bin(bert_data))
def encode_usr_handler_output(p_result,
		p_encoding_type,
		p_tornado_handler_self,
		p_log_fun):
	p_log_fun('FUN_ENTER','http_tornado_req_handler.encode_usr_handler_output()')
	try:
		if p_encoding_type == 'json':
			
			encoded_result_str = json.dumps(p_result)
			return encoded_result_str
			
		#elif p_encoding_type == 'bert':
		#	encoded_result_bin = bert_decoder.encode(p_result)
		#	return encoded_result_bin
			
	except Exception as e:
		#-----------------------
		#ERROR HANDLING
		
		error_msg_str = gf_rpc_server_meta.encoding_error_msg

		gf_error.handle_exception(e,   #p_exception,
			error_msg_str, #p_formated_msg_str,
			(),            #p_surrounding_context_attribs_tpl,
			p_log_fun)
		raise #throw the exception last cought
		#-----------------------
