#README - integration of QtWebKit engine with Python, 
#         for headless browser-based testing of front-end code and server API's, 
#         and for usage in browser-based scraping (on the server)

import os,sys
import json

import PySide.QtCore as QtCore
from   PySide.QtCore   import *
from   PySide.QtGui    import *
from   PySide.QtWebKit import *

import gf_test_web
#-------------------------------------------------
def init_js(p_qt_web_page,
		p_async_callbacks_tracker_map,
		p_log_fun,
		p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_init_js.init_js()')
	
	init_js_sys_event_handlers(p_qt_web_page,
						p_log_fun,
						p_verbose_bool = p_verbose_bool)
	init_py_api_to_js(p_qt_web_page,
			p_async_callbacks_tracker_map,
			p_log_fun,
			p_verbose_bool = p_verbose_bool)
#-------------------------------------------------
def init_js_sys_event_handlers(p_qt_web_page,
						p_log_fun,
						p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_init_js.init_js_sys_event_handlers()')
	
	#-------------------------------------------------	
	def js_alert_handler(p_webframe, p_message):
		if p_verbose_bool: p_log_fun('EXTERN','alert message box:%s'%(p_message))
	#-------------------------------------------------
	def js_console_msg_handler(p_message, p_line, p_sourceid):
		msg = 'JS_CONSOLE - line:%s - %s - %s'%(p_line,
											p_sourceid,
											p_message)
		p_log_fun('ERROR',msg)
	#-------------------------------------------------
	def js_confirm_handler(webframe, message):
		p_log_fun('ERROR','JS CONFIRM HANDLER not implemented yet')
	#-------------------------------------------------
	def js_prompt_handler(webframe, message, defaultvalue, result):
		p_log_fun('ERROR','JS PROMPT HANDLER not implemented yet')
	#-------------------------------------------------
	p_qt_web_page.javaScriptAlert          = js_alert_handler
	p_qt_web_page.javaScriptConsoleMessage = js_console_msg_handler
	p_qt_web_page.javaScriptConfirm        = js_confirm_handler
	p_qt_web_page.javaScriptPrompt         = js_prompt_handler
  
#-------------------------------------------------	
def init_py_api_to_js(p_qt_web_page,
			p_async_callbacks_tracker_map,
			p_log_fun,
			p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_init_js.init_py_api_to_js()')
	assert isinstance(p_async_callbacks_tracker_map,dict)
	
	#-------------------------------------------------
	class Extensions(QObject):
		#-------------------------------------------------
		#p :QString - JSON string of data from the Javascript VM

		@QtCore.Slot(str)
		def pass_sync_result_to_py(self,
							p_result_json_str):
			if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_init_js.init_py_api_to_js().pass_sync_result_to_py()')
			#p_log_fun('INFO'     ,'p_result_json_str:%s'%(p_result_json_str))
			
			result_decoded = json.loads(p_result_json_str.encode('ascii','ignore'))
			#p_log_fun('INFO'     ,'result_decoded:%s'%(result_decoded))
			#p_log_fun('INFO'     ,type(result_decoded))
			assert not result_decoded == None
			
			#-----------------
			#FIX!! - js_received_result_sync is a module global variable
			#        get rid of it and get this passing done only via mutable function arguments,
			#        or some sort of callback (onComplete or other)
			
			gf_test_web.js_received_result_sync = result_decoded
			#-----------------
			
		#-------------------------------------------------	
		@QtCore.Slot(str)
		def pass_async_result_to_py(self,
							p_result_json_str):
			if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_init_js.init_py_api_to_js().pass_async_result_to_py()')
			
			result_decoded = json.loads(p_result_json_str.encode('ascii','ignore'))
			assert not result_decoded == None                      
			
			callback_id   = result_decoded['callback_id']
			response_data = result_decoded['data']
			
			#make sure an asynchronous call registered this callback_id in the first place
			assert p_async_callbacks_tracker_map.has_key(callback_id)
			assert p_async_callbacks_tracker_map[callback_id] == 'waiting'
			
			#register response for this particular callback_id
			p_async_callbacks_tracker_map[callback_id] = response_data
		#-------------------------------------------------
		@QtCore.Slot(str,str)
		def py_log_fun(self,              
					p_group_str,
					p_msg_str):
			
			group_str = p_group_str.encode('ascii','ignore')
			msg_str   = p_msg_str.encode('ascii','ignore')
			
			new_group_str = 'JS:'+group_str
			new_msg_str   = msg_str
			
			p_log_fun(new_group_str,new_msg_str)
	#-------------------------------------------------
	e = Extensions();
	p_qt_web_page.mainFrame().addToJavaScriptWindowObject("extensions", e);
	
	#If you want to ensure that your QObjects remain accessible after 
	#loading a new URL, you should add them in a slot 
	#connected to the javaScriptWindowObjectCleared() signal.
	#webpage.connect(webpage.mainFrame(), 
	#	              QtCore.SIGNAL("javaScriptWindowObjectCleared"), 
	#	              add_extensions_fun)
