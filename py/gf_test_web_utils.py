#README - integration of QtWebKit engine with Python, 
#         for headless browser-based testing of front-end code and server API's, 
#         and for usage in browser-based scraping (on the server)

import os,sys
import os
import time
import datetime

import gf_test_web
#-------------------------------------------------
def history_go_back(p_qt_webpage,
		p_log_fun,
		p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_utils.history_go_back()')
	
	#:PySide.QtWebKit.QWebHistory
	qt_history = p_qt_webpage.history()
	qt_history.back()
#-------------------------------------------------
def scroll_page(p_vertical_pixels_num_to_scroll,
		p_horizontal_pixels_num_to_scroll,

		p_qt_page_frame,
		p_log_fun,
		p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_utils.scroll_page()')
	
	p_qt_page_frame.scroll(p_horizontal_pixels_num_to_scroll,
			p_vertical_pixels_num_to_scroll)
#-------------------------------------------------
#NOT TESTED YET!! - for asynchronous calls there are no tests written for it
#                   and it was shown not to work for JS ajax calls

def pause_event_loop_fun(p_seconds,
			p_qt_app,
			p_log_fun,
			p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_utils.pause_event_loop_fun()')
	
	interupt_sleep = .05
	start_time     = time.time()
	current_time   = None
	
	while True:
		time.sleep(interupt_sleep)
		
		current_time = time.time()
		elapsed      = current_time - start_time
		
		if elapsed > p_seconds:
			return
		else:
			#while the py thread is sleeping, qtwebkit thread is adding new events
			#which need to be processed (one of those events it the return of the asyc function)
			p_qt_app.processEvents()
#-------------------------------------------------
#blocking

#->:Any
def eval_sync_js_fun(p_script_code_str,
		p_qt_page_frame,
		p_log_fun,
		p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_utils.eval_sync_js_fun()')
	if p_verbose_bool: p_log_fun('INFO'     ,'p_script_code_str:%s'%(p_script_code_str))
	
	p_qt_page_frame.evaluateJavaScript(p_script_code_str)

	results                             = gf_test_web.js_received_result_sync
	gf_test_web.js_received_result_sync = None #reset results
	
	return results
#-------------------------------------------------
#p_callback_id - this is the string ID used for this async operation.
#                when the async JS function calls async_return_to_py() it has to 
#                supply the same callback_id as an argument as the one supplied here 
#                to eval_async_js_fun()
	
#blocking

#->:Any
def eval_async_js_fun(p_async_script_code_str,
		p_callback_id,
		p_timeout_seconds,

		p_async_callbacks_tracker_map,
		p_qt_app,
		p_qt_page_frame,
		p_log_fun,
		p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_utils.eval_async_js_fun()')
	assert isinstance(p_callback_id,basestring)
	
	#register this functions callback 
	p_qt_page_frame.evaluateJavaScript('async_callbacks_tracker_map["%s"] = "waiting"'%(p_callback_id))
	p_async_callbacks_tracker_map[p_callback_id] = 'waiting'
	
	#this is assumed to be asynchronous (since its in eval_js_async_fun())
	#however it does return immediatelly by qt
	p_qt_page_frame.evaluateJavaScript(p_async_script_code_str)

	start_t = datetime.datetime.now()

	while True:

		#this only pasuses the current thread (other threads continue 
		#without interuption, including the qtwebkit thread)
		time.sleep(0.2)
		
		#while the py thread is sleeping, qtwebkit thread is adding new events
		#which need to be processed (one of those events it the return of the asyc function)
		p_qt_app.processEvents()

		current_callback_returned_data = p_async_callbacks_tracker_map[p_callback_id]
		
		#ATTENTION!! 
		#check on each event loop iteration if the result has 
		#been registered for the 
		#our callback_id. if yes exit the loop before the timeout is reached
		if not current_callback_returned_data == 'waiting':
			return current_callback_returned_data
		else:
			current_t = datetime.datetime.now()			
			delta     = current_t - start_t

			if delta.seconds > p_timeout_seconds:		
				return current_callback_returned_data
#-------------------------------------------------
#p_timeout_seconds - this is the timeout since the last request that was detected
#                    to have been sent out. 

#->:Dict(response_infos_map)
def check_all_requests_returned(p_since_last_request_timeout_seconds,
			p_on_timeout_handler_fun,
			p_log_fun,
			p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_utils.check_all_requests_returned()')
	
	#:datetime
	time_since_last_request_issued = datetime.datetime.now()

	while True:
		#this only pasuses the current thread (other threads continue 
		#without interuption, including the qtwebkit thread)
		time.sleep(0.2)
		
		#while the py thread is sleeping, qtwebkit thread is adding new events
		#which need to be processed (one of those events it the return of the asyc function)
		p_qt_app.processEvents()

		current_t = datetime.datetime.now()			
		delta     = current_t - time_since_last_request_issued

		if delta.seconds > p_timeout_seconds: 
			p_on_timeout_handler_fun()	
#-------------------------------------------------
def inject_scripts_into_page(p_scripts_to_inject_paths_lst,
			p_qt_page_frame,
			p_log_fun,
			p_verbose_bool = False): 
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_utils.inject_scripts_into_page()')
	
	for script_path in p_scripts_to_inject_paths_lst:
		if p_verbose_bool: p_log_fun('INFO','injecting script_path:%s'%(script_path))
		assert isinstance(script_path,basestring)
		assert os.path.isfile(script_path)
		assert script_path.endswith('.js')
		
		f = open(script_path)
		script_code_scr = f.read()
		f.close()
		
		#p_log_fun('INFO','script_code_scr:%s'%(script_code_scr))
		
		#BLOCKING - until the javascript returns, but leaves the 
		#           new JS state intact after it returns
		p_qt_page_frame.evaluateJavaScript(script_code_scr)
