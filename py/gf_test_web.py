#README - integration of QtWebKit engine with Python, 
#         for headless browser-based testing of front-end code and server API's, 
#         and for usage in browser-based scraping (on the server)

import os,sys

import PySide.QtCore    as QtCore
import PySide.QtNetwork as QtNetwork
from   PySide.QtCore   import *
from   PySide.QtGui    import *
from   PySide.QtWebKit import *

sys.path.append('%s/core/gf_error/py/src'%(gf_root))
import gf_error

sys.path.append('%s/src'%(proj_root))
import gf_test_bundle
import gf_test_utils

sys.path.append('%s/src/gf_test_web/meta'%(proj_root))
import gf_test_web_meta as meta

import gf_test_web_render
import gf_test_web_utils
import gf_test_web_init_js
import gf_test_web_net_mngr
import gf_test_web_net_filter

import inspect
import json
import datetime
import time

import multiprocessing
import logging
#--------------------------------------------------------
#http://www.pyside.org/docs/pyside/PySide/QtWebKit/QWebPage.html
#--------------------------------------------------------
#can only be done once per process
#qt_app = QApplication([])

js_received_result_sync = None

#page_done_loading_bool = False
#
#global page_done_loading_bool
#		if page_done_loading_bool == False:
#			page_done_loading_bool = True'''
#--------------------------------------------------------
#IMPORTANT!!
#each of the tests specified in p_page_tests_to_run_lst, 
#is run in the same page/JS context as the other ones in the supplied p_page_tests_to_run_lst
#which means they share global state... 
#so be careful and try not to depend on side-effects of the previous tests in the same batch
#--------------------------------------------------------	
#FINISH!! - call p_onTestStart_fun and p_onTestEnd_fun in appropriate places
#           of the test running cycle

#blocking

def run_bundle_in_separate_process(p_test_bundle_adt,
						p_io_context_map,
						p_onComplete_fun,
						p_log_fun,

						p_onTestStart_fun = None,
						p_onTestEnd_fun   = None,
						p_verbose_bool    = False,
						p_onWebRequest_user_fun  = None,
						p_onWebResponse_user_fun = None):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_in_separate_process()')
	assert isinstance(p_test_bundle_adt,gf_test_bundle.TestBundle_ADT)
	assert isinstance(p_db_context_map,dict)
	
	multiprocessing.log_to_stderr(logging.DEBUG)
	parent_conn, child_conn = multiprocessing.Pipe()
	
	#---------------------------------------------------
	def run_bundle_process(p_test_bundle_adt,
				p_onWebRequest_user_fun,
				p_onWebResponse_user_fun,
				p_verbose_bool,
				p_io_context_map,
				p_child_conn,
				p_log_fun):
		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_in_separate_process().run_bundle_process()')
		
		#---------------------------------------------------
		def onComplete_fun(p_tests_run_info_map):
			if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_in_separate_process().run_bundle_process().onComplete_fun()')
			if p_verbose_bool: p_log_fun('INFO','run_bundle_process() complete...')   
			#if p_verbose_bool: p_log_fun('INFO','p_tests_run_info_map:%s'%(p_tests_run_info_map))
			
			p_child_conn.send('complete')
			p_child_conn.send(p_tests_run_info_map)
		#---------------------------------------------------	
			   
		run_bundle(p_test_bundle_adt,
			p_io_context_map,
			onComplete_fun,
			p_log_fun,
			p_verbose_bool           = p_verbose_bool,
			p_onWebRequest_user_fun  = p_onWebRequest_user_fun,
			p_onWebResponse_user_fun = p_onWebResponse_user_fun)
	#---------------------------------------------------
	
	#:multiprocessing.Process
	server_process = multiprocessing.Process(target = run_bundle_process, 
                                           args = (p_test_bundle_adt,
												p_onWebRequest_user_fun,
												p_onWebResponse_user_fun,
												p_verbose_bool,
												p_io_context_map,
												child_conn,
												p_log_fun))
	server_process.start()
	
	#waiting for run_bundle_proces() (separate OS process) to send a 
	#'complete' message to indicate finalization of the asynchronous test bundle
	while True:
		response = parent_conn.recv()
		
		if response == 'complete':
			tests_run_info_map = parent_conn.recv()
			assert isinstance(tests_run_info_map,dict)
			
			#p_log_fun('INFO','tests_run_info_map:%s'%(tests_run_info_map))
			
			p_onComplete_fun(tests_run_info_map)
			
			#exit the loop and container function, tests were run
			return 
#--------------------------------------------------------	
def run_bundle(p_test_bundle_adt,
		p_io_context_map,
		p_onComplete_fun,
		p_log_fun,
		p_verbose_bool           = False,
		p_onWebRequest_user_fun  = None,
		p_onWebResponse_user_fun = None):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle()')
	assert isinstance(p_test_bundle_adt,gf_test_bundle.TestBundle_ADT)
	
	#----------------
	#REQUEST FILTERING
	
	filter_context_map = gf_test_web_net_filter.get_filter_context(p_io_context_map,
															p_log_fun,
															p_verbose_bool           = p_verbose_bool,
															p_onWebRequest_user_fun  = p_onWebRequest_user_fun,
															p_onWebResponse_user_fun = p_onWebResponse_user_fun)
	assert isinstance(filter_context_map,dict)
	
	on_net_mngr_request_handler_fun = filter_context_map['on_net_mngr_request_handler_fun']
	on_net_mngr_reply_handler_fun   = filter_context_map['on_net_mngr_reply_handler_fun']
	#----------------
		
	qt_app = QApplication([])
	
	#--------------------------------------------------------
	def onComplete_fun(p_tests_run_info_map):
		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle().onComplete_fun()')
		
		if not p_test_bundle_adt.bundle_cleanup_fun == None:
			p_test_bundle_adt.bundle_cleanup_fun()
			
		#ATTENTION!! - without this it causes a Segmentation Fault
		#REMOVE THIS - app should be reused between scraping of different pages
		qt_app.quit()
		
		#filter_context_map's logged_requests_lst/logged_responses_lst vars are populated
		#by on_net_mngr_request_handler_fun/on_net_mngr_reply_handler_fun (since those two funs are closures)
		p_tests_run_info_map['logged_requests_lst']  = filter_context_map['logged_requests_lst']
		p_tests_run_info_map['logged_responses_lst'] = filter_context_map['logged_responses_lst']
		
		p_onComplete_fun(p_tests_run_info_map)
	#--------------------------------------------------------	
	
	if not p_test_bundle_adt.bundle_setup_fun == None:
		bundle_setup_fun_result = p_test_bundle_adt.bundle_setup_fun()
	else:
		bundle_setup_fun_result = None
		
	init_page_and_run_bundle(p_test_bundle_adt, 
						qt_app,

						onComplete_fun,
						on_net_mngr_request_handler_fun,
						on_net_mngr_reply_handler_fun,
						p_io_context_map,
						p_log_fun,
						p_bundle_setup_fun_result = bundle_setup_fun_result,
						p_verbose_bool            = p_verbose_bool)
#--------------------------------------------------------
def init_page_and_run_bundle(p_test_bundle_adt,
						p_qt_app,

						p_onComplete_fun,
						p_on_net_mngr_request_handler_fun,
						p_on_net_mngr_reply_handler_fun,

						p_io_context_map,
						p_log_fun,
						p_bundle_setup_fun_result = None,
						p_verbose_bool            = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.init_page_and_run_bundle()')
	p_log_fun('INFO','page_url_str:%s'%(p_test_bundle_adt.page_url_str)) 
	assert inspect.isfunction(p_on_net_mngr_request_handler_fun)
	
	#-------------------            
	#IMPORTANT!!
	#this is whats checked to see if a particular JS async function finished its operation
	#(by calling the sync/async version of the sync_return_to_py/async_return_to_py JS API)
	#key   - is the name of callback (callback_id)
	#value - is the data returned by that function via the 
	#        return_async_to_py() Javascript Py extension
	async_callbacks_tracker_map = {}
	
	failed_requests_lst = []
	#-------------------
	#sys.argv)
	qt_webpage = QWebPage() 
	#-------------------------------------------------
	#->:Bool(allow_bool)
	def on_net_mngr_request_handler_fun(p_url,
								p_operation,
								p_qt_net_request,
								p_data):
		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle().on_net_mngr_request_handler_fun()')
		p_log_fun('EXTERN','p_url:%s'%(p_url))

		allow_bool = p_on_net_mngr_request_handler_fun(p_url,
												p_operation,
												p_qt_net_request,
												p_log_fun)
		assert isinstance(allow_bool,bool)
		
		return allow_bool
	#-------------------------------------------------
	#this is run when the net_mngr receives an http response
	def on_net_mngr_reply_handler_fun(p_q_net_reply):
		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle().on_net_mngr_reply_handler_fun()')
		
		url = unicode(p_q_net_reply.url().toString()).encode("utf8")
		
		p_on_net_mngr_reply_handler_fun(url,
			                              p_q_net_reply,
			                              p_log_fun)
		#----------------------
		#ERROR-HANDLING
		
		#error() -> QtNetwork.QNetworkReply.NetworkError.NoError if there is no error
		error_type = str(p_q_net_reply.error()).split('.')[-1:]
		if error_type == 'NoError':
			error_msg = p_q_net_reply.errorString()
			
			error_info_map = {
				'time'     :datetime.datetime.now(),
				'url'      :url,
				'error_msg':error_msg
			}
			failed_requests_lst.append(error_info_map)
			
			p_log_fun('EXTERN','FAIL:%s'%(url))
		#----------------------
		
		else:	
			p_log_fun('EXTERN','SUCCESS:%s'%(url))
	#-------------------------------------------------
	def on_pageLoad_finished():
		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle().on_pageLoad_finished()')

		qt_frame = qt_webpage.mainFrame()
		
		#FINISH!! - use this (received_bytes) and log it
		received_bytes = qt_webpage.bytesReceived()
		p_log_fun('INFO','received_bytes:%s'%(received_bytes))
		
		#--------------------------
		#always add the javascript helpers, to each page
		#these scripts are added at the end of the user supplied list of scripts to inject 
		#the use case is that they will potentially overwrite 
		#other page javascript objects, if they're encoutered
		#these new clone methods contain extension API's that only work inside of 
		#this gf_test_web container
		
		scripts_to_inject_paths_lst = meta.js_helpers_to_inject_lst
		scripts_to_inject_paths_lst.extend(p_test_bundle_adt.js_scripts_to_inject_paths_lst)
		#--------------------------
		
		gf_test_web_utils.inject_scripts_into_page(scripts_to_inject_paths_lst,
												qt_frame,
												p_log_fun,
												p_verbose_bool = p_verbose_bool)

		tests_run_info_map = run_bundle_tests(p_test_bundle_adt,
									async_callbacks_tracker_map,
									p_qt_app,
									qt_webpage,
									p_log_fun,
									p_bundle_setup_fun_result = p_bundle_setup_fun_result,
									p_verbose_bool            = p_verbose_bool)
		
		#all tests have finished, so signal to the external user that its done
		p_onComplete_fun(tests_run_info_map) 
	#-------------------------------------------------
	gf_test_web_init_js.init_js(qt_webpage,
	                            async_callbacks_tracker_map,
	                            p_log_fun,
	                            p_verbose_bool = p_verbose_bool)
	
	#this initializes net_mngr event handlers and the cookies sub-system
	gf_test_web_net_mngr.init(qt_webpage,
						p_test_bundle_adt.cookies_file_path_str, #p_cookies_file_path
						on_net_mngr_request_handler_fun,         #p_on_request_handler_fun
						on_net_mngr_reply_handler_fun,           #p_on_reply_handler_fun
						p_log_fun,
						p_verbose_bool = p_verbose_bool)
	
	qt_webpage.connect(qt_webpage, SIGNAL("loadFinished(bool)"), on_pageLoad_finished)
	#qt_net_mngr.connect(qt_net_mngr, SIGNAL("finished(QNetworkReply* reply)"), on_net_mngr_request_done)
	
	p_log_fun('INFO','p_page_url_str:%s'%(p_test_bundle_adt.page_url_str))
	qt_webpage.mainFrame().load(QUrl(p_test_bundle_adt.page_url_str))
		
	p_qt_app.exec_()
#-------------------------------------------------
#->:Dict(tests_run_info_map)
def run_bundle_tests(p_test_bundle_adt,
			p_async_callbacks_tracker_map,
			p_qt_app,
			p_qt_webpage, 
			p_log_fun,
			p_bundle_setup_fun_result = None,
			p_verbose_bool            = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_tests()')
	assert isinstance(p_test_bundle_adt,gf_test_bundle.TestBundle_ADT)
	
	failed_tests_lst    = [] 
	completed_tests_lst = []
	
	#ATTENTION!!
	#its a list in order to avoid Python closures innability to modify variables in its surrounding context
	total_asserts_num = [0] 
	
	qt_page_frame = p_qt_webpage.mainFrame()
	#-------------------------------------------------
	#PY GF_TEST_WEB API - supplied to each test to interact
	#                     with the embedded browser environment
	#-------------------------------------------------
	#->:Dict(web_funs_map)
	def get_web_funs():
		#-------------------------------------------------
		#blocking
		
		#->:Any
		def eval_async_js_fun(p_script_code_str,
						p_callback_id,
						p_timeout_seconds = 3):
			if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_page_tests().eval_async_js_fun()')
			assert isinstance(p_callback_id    ,basestring)
			assert isinstance(p_timeout_seconds,int)
			
			return gf_test_web_utils.eval_async_js_fun(p_script_code_str,
												p_callback_id,
												p_timeout_seconds,

												p_async_callbacks_tracker_map,
												p_qt_app,
												qt_page_frame,
												p_log_fun,
												p_verbose_bool = p_verbose_bool)
		#-------------------------------------------------	
		def eval_sync_js_fun(p_script_code_str):
			if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_tests().eval_sync_js_fun()')
			
			return gf_test_web_utils.eval_sync_js_fun(p_script_code_str,
											qt_page_frame,
											p_log_fun,
											p_verbose_bool = p_verbose_bool)
		#-------------------------------------------------
		def inject_script_fun(p_script_path):
			if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_tests().inject_script_fun()')
			gf_test_web_utils.inject_scripts_into_page([p_script_path],
												qt_page_frame,
												p_log_fun,
												p_verbose_bool = p_verbose_bool)
		#-------------------------------------------------
		def pause_event_loop_fun(p_seconds):
			if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_tests().pause_event_loop_fun()')
			gf_test_web_utils.pause_event_loop_fun(p_seconds,
											p_qt_app,
											p_log_fun,
											p_verbose_bool = p_verbose_bool)
		#-------------------------------------------------	
		def scroll_page_fun(p_horizontal_pixels_num_to_scroll):
			if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_tests().scroll_page_fun()')
			gf_test_web_utils.scroll_page(p_horizontal_pixels_num_to_scroll,
									qt_page_frame,
									p_log_fun,
									p_verbose_bool = p_verbose_bool)
		#-------------------------------------------------	
		def history_go_back_fun():
			if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_tests().history_go_back()')
			gf_test_web_utils.history_go_back(p_qt_webpage,
										p_log_fun,
										p_verbose_bool = p_verbose_bool)
		#-------------------------------------------------	
		web_funs_map = {
			'eval_async_js_fun'   :eval_async_js_fun,
			'eval_sync_js_fun'    :eval_sync_js_fun,
			'inject_script_fun'   :inject_script_fun,
			'pause_event_loop_fun':pause_event_loop_fun,
			'scroll_page_fun'     :scroll_page_fun,
			'history_go_back_fun' :history_go_back_fun
		}
		
		return web_funs_map
	#------------------------------------------------
	#->:Dict(assert_funs_map)
	def get_assert_funs():
		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_bundle_tests().get_assert_funs()')
		#-------------------------------------------------
		def assert_true(p_condition_bool):
			total_asserts_num[0] += 1
			gf_test_utils.assert_true(p_condition_bool,
								p_log_fun)
		#-------------------------------------------------
		
		assert_funs_map = {
			'assert_true':assert_true
		}
		return assert_funs_map
	#------------------------------------------------
	
	web_funs_map    = get_web_funs()
	assert_funs_map = get_assert_funs()
	
	for page_test_info_map in p_test_bundle_adt.tests_lst:
		assert isinstance(page_test_info_map,dict)
		
		test_run_info_map = run_single_test(page_test_info_map,
									p_qt_webpage,
									p_qt_app,
									web_funs_map,
									assert_funs_map,
									p_bundle_setup_fun_result,
									p_log_fun,
									p_verbose_bool = p_verbose_bool)
		assert isinstance(test_run_info_map,dict)
		
		if test_run_info_map['status_str'] == 'error':
			failed_tests_lst.append(test_run_info_map)
		else:
			completed_tests_lst.append(test_run_info_map)
	
	tests_run_info_map = {
		'total_asserts_num'  :total_asserts_num[0],
		'completed_tests_lst':completed_tests_lst,
		'failed_tests_lst'   :failed_tests_lst
	}
	
	return tests_run_info_map
#-------------------------------------------------	
#->:Dict(test_run_info_map)
def run_single_test(p_test_info_map,
			p_qt_webpage,
			p_qt_app,

			p_web_funs_map,
			p_assert_funs_map,

			p_bundle_setup_fun_result,
			p_log_fun,
			p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_single_test()')
	assert isinstance(p_test_info_map,dict)
	
	test_name = p_test_info_map['name_str']
	test_fun  = p_test_info_map['test_fun']
	
	p_log_fun('INFO','#################################################')
	p_log_fun('INFO','running test: %s'%(test_name))
	p_log_fun('INFO','#################################################')

	#-------------------------------------------------
	#->:Dict
	def run_test_fun():
		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web.run_single_test().run_test_fun()')
		
		try:
			
			#:Any|:None
			output = test_fun(p_web_funs_map,
						p_assert_funs_map,
						p_bundle_setup_fun_result,
						p_log_fun)

			test_run_info_map = {
				'test_name_str'  :test_name,
				'status_str'     :'ok',
				'test_fun_output':output,
			}
			return test_run_info_map
				
		except Exception as e:    
			msg_str = 'test %s failed'
			gf_error.handle_exception(e,
								msg_str,
								(test_name,),
								p_log_fun)
			
			test_run_info_map = {
				'test_name_str'  :test_name,
				'status_str'     :'error',
				'test_fun_output':None,
				'error_msg_str'  :msg_str%(test_name)
			}
				
			return test_run_info_map
	#-------------------------------------------------

	test_run_info_map = gf_test_web_render.with_screenshots(test_name,
													run_test_fun,
													p_test_info_map,
													p_qt_webpage,
													p_qt_app,
													p_log_fun,
													p_verbose_bool = p_verbose_bool)
	assert isinstance(test_run_info_map,dict)
	
	return test_run_info_map
