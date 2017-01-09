#README - integration of QtWebKit engine with Python, 
#         for headless browser-based testing of front-end code and server API's, 
#         and for usage in browser-based scraping (on the server)

import os,sys
import datetime
import PySide.QtCore as QtCore
from   PySide.QtCore   import *
from   PySide.QtGui    import *
from   PySide.QtWebKit import *
#-------------------------------------------------
#->:Any
def with_screenshots(p_test_name,
		p_test_to_wrap_fun,
		p_test_info_map,
		p_qt_webpage,
		p_qt_app,
		p_log_fun,
		p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_render.with_screenshots()')
	
	#TEST START SCREENSHOT
	if p_test_info_map.has_key('screenshot_dir_path'):
		take_screenshot(p_test_name,
				p_test_info_map['screenshot_dir_path'],
				p_qt_webpage,
				p_qt_app,
				'init_state',
				p_log_fun,
				p_verbose_bool = p_verbose_bool)

	result = p_test_to_wrap_fun()
	
	#TEST END SCREENSHOT 
	if p_test_info_map.has_key('screenshot_dir_path'):
		take_screenshot(p_test_name,
				p_test_info_map['screenshot_dir_path'],
				p_qt_webpage,
				p_qt_app,
				'post_state',
				p_log_fun,
				p_verbose_bool = p_verbose_bool)
		
	return result
#-------------------------------------------------		
def take_screenshot(p_test_name,
		p_page_test_screenshot_dir_path,
		p_qt_webpage,
		p_qt_app,
		p_state_type_str, #'init_state'|'post_state'
		p_log_fun,
		p_verbose_bool = False):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_render.take_screenshot()')	
	
	try:
		assert isinstance(p_page_test_screenshot_dir_path,basestring)
		assert os.path.isdir(p_page_test_screenshot_dir_path)
		assert p_state_type_str == 'init_state' or \
		       p_state_type_str == 'post_state'
	except Exception as e:
		if p_verbose_bool: p_log_fun('INFO','p_page_test_screenshot_dir_path:%s'%(p_page_test_screenshot_dir_path))
		raise
		
	#each test has its own screenshot taken 
	test_screenshot_file_path = '%s/%s:%s:%s.png'%(p_page_test_screenshot_dir_path, 
						p_test_name,
						datetime.datetime.now().isoformat(),
						p_state_type_str)
	render_page(p_qt_webpage,
		p_qt_app,
		test_screenshot_file_path,
		p_log_fun,
		p_verbose_bool = p_verbose_bool)

#-------------------------------------------------
#saves the screenshot to the filesystem

def render_page(p_webpage,
		p_qt_app,
		p_target_file_path,
		p_log_fun,
		p_verbose_bool        = False,
		p_viewport_widht_num  = 1024,
		p_viewport_height_num = 768):
	if p_verbose_bool: p_log_fun('FUN_ENTER','gf_test_web_render.render_page()')
	assert isinstance(p_webpage,QWebPage)
	
	#---------------
	#SET VIEWPORT SIZE
	#QtWebKit seems to be having trouble with frames that are too large in 
	#their dimensions (width or height), so here the frame size is being decreased
	
	target_size = QSize(p_viewport_widht_num, 
		p_viewport_height_num)
	
	#:QSize
	contents_size = p_webpage.mainFrame().contentsSize()
	p_log_fun('INFO','contents_size:%s'%(contents_size))
	
	#contents_size.setHeight(contents_size.width() * target_size.height() / target_size.width())
	contents_size.setWidth(p_viewport_widht_num)
	contents_size.setHeight(p_viewport_height_num)
	
	p_webpage.setViewportSize(contents_size)

	p_log_fun('INFO','p_webpage.viewportSize():%s'%(p_webpage.viewportSize()))
	
	image = QImage(p_webpage.viewportSize(), 
			QImage.Format_ARGB32) #.Format_ARGB32_Premultiplied)
	
	painter = QPainter(image)
	p_log_fun('INFO','rendering the webpage main frame to file [%s]'%(p_target_file_path))
	
	p_webpage.mainFrame().render(painter)
	painter.end()
	image.save(p_target_file_path)
##----------------z--------------------------------	
##FINISH!!
#def validate_screenshot():
#	import cv #Import functions from OpenCV
#	cv.NamedWindow('a_window', cv.CV_WINDOW_AUTOSIZE)
#	image = cv.LoadImage('picture.png', cv.CV_LOAD_IMAGE_COLOR) #Load the image
#	font  = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 1, 1, 0, 3, 8) #Creates a font
#	x     = x position of text
#	y     = y position of text
#	cv.PutText(frame,"Hello World!!!", (x,y),font, 255) #Draw the text
#	cv.ShowImage('a_window', image) #Show the image
#	cv.Waitkey(10000)
#	cv.SaveImage('image.png', image) #Saves the image