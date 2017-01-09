#README - integration of QtWebKit engine with Python, 
#         for headless browser-based testing of front-end code and server API's, 
#         and for usage in browser-based scraping (on the server)

import os,sys
import envoy
import inspect

import PySide.QtCore    as QtCore
import PySide.QtNetwork as QtNetwork

sys.path.append('%s/src/gf_test_web/meta'%(proj_root))
import gf_test_web_meta as meta
import gf_test_web
#---------------------------------------------------------------      
def init_cookies(p_qt_net_mngr,
		p_cookies_file_path,
		p_log_fun,
		p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_cookies.init_cookies()')
	
	assert os.path.isdir(os.path.dirname(p_cookies_file_path))
	
	#creates the cookie file if one doesnt already exist
	if os.path.isfile(p_cookies_file_path) == False:
		envoy.run('touch %s'%(os.path.abspath(p_cookies_file_path)))
	
	cookiesjar = _ExtendedNetworkCookieJar()
	p_qt_net_mngr.setCookieJar(cookiesjar)
#---------------------------------------------------------------        
class _ExtendedNetworkCookieJar(QtNetwork.QNetworkCookieJar):
	#---------------------------------------------------------------
	def mozillaCookies(self):	
		#Return all cookies in Mozilla text format:
		# domain domain_flag path secure_connection expiration name value
		#.firefox.com TRUE / FALSE 946684799 MOZILLA_ID 100103
	
		header = ["# Netscape HTTP Cookie File", ""]
		#---------------------------------------------------------------
		def bool2str(value):
			return {True: "TRUE", False: "FALSE"}[value]
		#---------------------------------------------------------------
		def byte2str(value):
			return str(value)
		#---------------------------------------------------------------
		def get_line(cookie):
			domain_flag = str(cookie.domain()).startswith(".")
			
			return "\t".join([byte2str(cookie.domain()),
						bool2str(domain_flag),
						byte2str(cookie.path()),
						bool2str(cookie.isSecure()),
						byte2str(cookie.expirationDate().toTime_t()),
						byte2str(cookie.name()),
						byte2str(cookie.value())])
		#---------------------------------------------------------------
		lines = [get_line(cookie) for cookie in self.allCookies()]
		return "\n".join(header + lines)
	#---------------------------------------------------------------
	def setMozillaCookies(self, string_cookies):
		#---------------------------------------------------------------
		#Set all cookies from Mozilla test format string.
		#.firefox.com TRUE / FALSE 946684799 MOZILLA_ID 100103

		def str2bool(value):
			return {"TRUE": True, "FALSE": False}[value]
		#---------------------------------------------------------------
		def get_cookie(line):
			fields = map(str.strip, line.split("\t"))
			if len(fields) != 7:
				return
			domain, domain_flag, path, is_secure, expiration, name, value = fields
			cookie = QNetworkCookie(name, value)
			cookie.setDomain(domain)
			cookie.setPath(path)
			cookie.setSecure(str2bool(is_secure))
			cookie.setExpirationDate(QDateTime.fromTime_t(int(expiration)))
			return cookie
		#---------------------------------------------------------------
		cookies = [get_cookie(line) for line in string_cookies.splitlines()
			if line.strip() and not line.strip().startswith("#")]
		self.setAllCookies(filter(bool, cookies))