#README - integration of QtWebKit engine with Python, 
#         for headless browser-based testing of front-end code and server API's, 
#         and for usage in browser-based scraping (on the server)

import os,sys
import inspect

import PySide.QtCore as QtCore
from   PySide.QtCore   import *
from   PySide.QtGui    import *
from   PySide.QtWebKit import *
#from   PyQt4.QtNetwork import *
import PySide.QtNetwork as QtNetwork

sys.path.append('%s/src/gf_test_web/meta'%(proj_root))
import gf_test_web_meta as meta

import gf_test_web
import gf_test_web_cookies
#-------------------------------------------------
def init(p_qt_webpage,
	p_cookies_file_path,

	p_on_request_handler_fun,
	p_on_reply_handler_fun,
	p_log_fun,
	p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_net_mngr.init()')
	assert inspect.isfunction(p_on_request_handler_fun)
	assert inspect.isfunction(p_on_reply_handler_fun)
	
	# Network Access Manager and cookies
	#:QtNetwork.QNetworkAccessManager
	qt_net_mngr = QtNetwork.QNetworkAccessManager()
	p_qt_webpage.setNetworkAccessManager(qt_net_mngr)
	
	set_net_mngr_event_handlers(qt_net_mngr,
				p_on_request_handler_fun,
				p_on_reply_handler_fun,
				p_log_fun)
	
	if not p_cookies_file_path == None:
		gf_test_web_cookies.init_cookies(qt_net_mngr,
						p_cookies_file_path,
						p_log_fun)
#---------------------------------------------------------------
def set_net_mngr_event_handlers(p_qt_net_mngr,
			p_on_request_handler_fun, #:Function - user-logic to be run on sending of the request
			p_on_reply_handler_fun  , #:Function - user-logic to be run on receipt of reply
			p_log_fun,
			p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_net_mngr.set_net_mngr_event_handlers()')
	
	#-------------------------------------------------
	def onRequest(p_operation, 
		p_request, 
		p_data):

		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_net_mngr.set_net_mngr_event_handlers().onRequest()')
		if p_verbose_bool: p_log_fun('EXTERN','REQUEST')
		
		#if p_verbose_bool: p_log_fun('INFO','p_operation   :%s'%(p_operation))
		#if p_verbose_bool: p_log_fun('INFO','dir(p_request):%s'%(dir(p_request)))
		if p_verbose_bool: p_log_fun('INFO','p_data:%s'%(p_data))

		url = unicode(p_request.url().toString()).encode("utf8")
		if p_verbose_bool: p_log_fun('INFO','url:%s'%(url))
		
		operation = None
		#example str(p_operation) - PySide.QtNetwork.QNetworkAccessManager.Operation.GetOperation
		if   str(p_operation).find('Get')   : operation = 'GET'
		elif str(p_operation).find('Post')  : operation = 'POST'
		elif str(p_operation).find('Put')   : operation = 'PUT'
		elif str(p_operation).find('Delete'): operation = 'DELETE' 
		
		if p_verbose_bool: p_log_fun('INFO','operation:%s'%(operation))

		#every user request handler returns Bool status
		#if its False then the request is droped and not sent out
		#if its True the request is repassed to QtNetworkManager
		user_handler_status = p_on_request_handler_fun(url,
							operation,
							p_request,
							p_data)
		assert isinstance(user_handler_status,bool)
		
		if p_verbose_bool:
			#print all headers
			for h in p_request.rawHeaderList():
				p_log_fun('INFO',"request header: %s:%s" % (h,p_request.rawHeader(h)))
			
		if p_verbose_bool: p_log_fun('EXTERN','REQUEST ++++++++++++++*******************')
			
		#---------------
		#this allows for request filtering of some sort
		
		#QtNetwork.QNetworkAccessManager.createRequest()
		#Returns a new PySide.QtNetwork.QNetworkReply object to handle the operation op and request req
		
		if user_handler_status == False:
			p_request.setUrl(QUrl("about:blank"))
			
			#:PySide.QtNetwork.QNetworkReply
			reply = QtNetwork.QNetworkAccessManager.createRequest(p_qt_net_mngr,
									p_operation, 
									p_request, 
									p_data)
			return reply
		else:
			#:PySide.QtNetwork.QNetworkReply
			reply = QtNetwork.QNetworkAccessManager.createRequest(p_qt_net_mngr,
									p_operation, 
									p_request, 
									p_data)
			return reply
	#-------------------------------------------------
	def onSslErrors(p_q_net_request):
		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_net_mngr.set_net_mngr_event_handlers().onSslErrors()')
	#-------------------------------------------------	
	def onReply(p_q_net_reply):

		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_net_mngr.set_net_mngr_event_handlers().onReply()')
		if p_verbose_bool: p_log_fun('EXTERN','REPLY')
		
		#if p_verbose_bool: p_log_fun('INFO','dir(p_q_net_reply):%s'%(dir(p_q_net_reply)))
		#if p_verbose_bool: p_log_fun('INFO',p_q_net_reply.error())
		#if p_verbose_bool: p_log_fun('INFO',p_q_net_reply.errorString())
		
		#if p_verbose_bool:
		#	print all headers
		#	for h in p_q_net_reply.rawHeaderList():
		#		p_log_fun('INFO',"request header: %s:%s" % (h, 
		#		                                            p_q_net_reply.rawHeader(h)))
			
		p_on_reply_handler_fun(p_q_net_reply)
	#-------------------------------------------------
	def onAuthRequired_handler():
		if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_net_mngr.set_net_mngr_event_handlers().onAuthRequired_handler()')
	#-------------------------------------------------
	#initialize network event managers
	p_qt_net_mngr.createRequest = onRequest
	
	p_qt_net_mngr.connect(p_qt_net_mngr,
                        SIGNAL("sslErrors(QNetworkReply *, const QList<QSslError> &)"),
                        onSslErrors)
	p_qt_net_mngr.connect(p_qt_net_mngr,
                        SIGNAL('finished(QNetworkReply *)'),
                        onReply)
	p_qt_net_mngr.connect(p_qt_net_mngr,
                        SIGNAL('authenticationRequired(QNetworkReply *, QAuthenticator *)'),
                        onAuthRequired_handler)
