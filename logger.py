import datetime, time, secrets, platform, os, sys, set_time, csv, shutil, re, inspect

from faker import Faker
from hashlib import blake2b
from selenium import webdriver
from python_arptable import ARPTABLE
from user_agent import generate_user_agent
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import ( TimeoutException,
	NoSuchElementException, StaleElementReferenceException )

_random = secrets.SystemRandom()
randrange = _random.randrange

timeout_multiplier = 1
driver_timeout = 15 # <-- Adjust in seconds
driver_long_timeout = 25

server_gettime_req = (
	f'''var date = new Date($.ajax({{async: false, type: 'GET', '''
	f'''contentType: 'application/json;charset=utf-8' '''
	f'''}}).getResponseHeader( 'Date' )); return [ '''
	f'''date.getFullYear(), date.getMonth() + 1, date.getDate(), '''
	f'''date.getHours(), date.getMinutes(), date.getSeconds(), 0] '''
)

def check_exists_by_xpath( xpath ):
	try:
		driver.find_element_by_xpath( xpath )
	except NoSuchElementException:
		return False
	return True
	
def check_input( parameters ):
	profile_dir = bin_dir = None
	global driver_timeout
	global driver_long_timeout
	global timeout_multiplier
	
	if len(parameters) == 3:
		profile_dir = str(sys.argv[1])
		bin_dir = str(sys.argv[2])
	
	elif len(sys.argv) == 4:
		try:
			profile_dir = str(sys.argv[1])
			bin_dir = str(sys.argv[2])
			timeout_multiplier = int(sys.argv[3])
		except ValueError:
			print("Integer Value as Third Parameter only!")
			timeout_multiplier = 3
			
	driver_timeout = timeout_multiplier * driver_timeout
	driver_long_timeout = timeout_multiplier * driver_long_timeout
	
	return profile_dir, bin_dir
	
def initialize_profile( f_profile_dir ):				
	firefox_profile = webdriver.FirefoxProfile( f_profile_dir )
	return firefox_profile
		
def initialize_driver( f_profile_dir, f_binary, f_profile, ua ):
	sel_slice1, sel_slice2 = f_profile_dir.split("/.mozilla", 1)
	f_cache_dir = sel_slice1 + "/.cache/mozilla" + sel_slice2

	f_options = webdriver.FirefoxOptions()
	f_options.headless = True
	f_options.accept_insecure_certs = True
	f_options.set_capability("pageLoadStrategy","none")
	f_options.set_preference("browser.cache.disk.parent_directory",
										f_cache_dir)
	f_options.set_preference("general.useragent.override", 
										ua )
	driver = webdriver.Firefox( firefox_binary=f_binary, options=f_options, 
								firefox_profile=f_profile, service_log_path=os.devnull)
	return driver

def portal_authenticate( obj ):

	pages = [ method for method in dir( obj ) if ( method.endswith('page') ) ]
	for page in pages:
		try:
			getattr( obj, page )()
		except:
			driver.quit()
			print(f'{datetime.datetime.now()} - {page} Error {{\n{sys.exc_info()} }}\n')
			sys.exit(254)

class wait_for_text_to_match( object ):
    def __init__(self, locator, pattern):
        self.locator = locator
        self.pattern = re.compile(pattern)

    def __call__(self, driver):
        try:
            element_text = EC._find_element(driver, self.locator).text
            return self.pattern.search(element_text)
        except StaleElementReferenceException:
            return False

class User:
	__slots__ = ['first_name','last_name']
        
	def __init__( self, first_name, last_name ):
		self.first_name = first_name
		self.last_name = last_name
		
	salt = bytes( '%.4f' % time.process_time_ns(), 'utf8' )

	def salted_hash( self, digest_size, message ):
		haesh = blake2b( digest_size=digest_size, salt=self.salt )
		haesh.update(b'message')

		return haesh.hexdigest()

	@property
	def email( self ):    
		message = f'''{self.first_name}.{self.last_name}'''
		username = self.salted_hash( 6 , message )
		email_string = ( f'''{username}@comcast.com''' )

		return email_string
	
	@property
	def password( self ):
		message = f'''{self.last_name}.{self.first_name}'''
		password = self.salted_hash( 4 , message )
		return password
		
	@property
	def unq_hostname( self ):
		hostname = secrets.token_urlsafe(randrange(5,8))
		return hostname
        
	@property
	def url_wifiondemand( self ):
		with open ("global_vars.csv", mode = 'r') as global_vars:
			spoofed_mac = global_vars.read().replace(":","%3A").strip()
		ap_mac = ARPTABLE[0]["HW address"].replace(":","%3A").strip()
		user_os = platform.system()
		hostname = self.unq_hostname
		
		url = ( f'''https://wifiondemand.xfinity.com/wod/landing?c=n&macId='''
			f'''{spoofed_mac}&a=as&bn=st22&location=default&apMacId={ap_mac}'''
			f'''&issuer=r&deviceModel={user_os}+Chrome+-+&deviceName={hostname}''' )
		return url

class XfinityForms( User ):
	def __init__( self, driver ):
		generator = Faker()
		User.__init__( self, generator.first_name(), generator.last_name() )
		self.driver = driver
		self.wait = WebDriverWait( driver, driver_timeout )						 
		self.long_wait = WebDriverWait( driver, driver_long_timeout )						 
	
	def first_page( self ):
		driver = self.driver
		wait = self.wait
		
		driver.get( self.url_wifiondemand )
		
		try:
			free_opt = wait.until(EC.presence_of_element_located((By.XPATH,"//*[contains(text(), 'Complimentary')]")))
		except TimeoutException:
			driver.quit()
			print("No Free Option To Select")
			sys.exit(255)
				
		first_submit = wait.until(EC.presence_of_element_located((By.ID,"continueButton")))
		driver.execute_script("window.stop();")

		free_opt.click()
		
		time_tuple = driver.execute_script(server_gettime_req)
		set_time._linux_set_time(time_tuple)
		
		first_submit.click()

		if check_exists_by_xpath("/html/body/div[1]/div/div[3]/div[2]"):
			decline = wait.until(EC.presence_of_element_located((By.XPATH,"//button[@id='upgradeOfferCancelButton']")))
			decline.click()

	def second_page( self ):
		driver = self.driver
		wait = self.wait
		unq_hostname = self.unq_hostname
			
		first_name_box = wait.until(EC.presence_of_element_located((By.XPATH,"//*[@id='firstName']")))		
		last_name_box = driver.find_element_by_xpath("//*[@id='lastName']")
		
		driver.execute_script("window.stop();")

		first_name_box.send_keys(self.first_name)
		last_name_box.send_keys(self.last_name)
						
		password = driver.find_element_by_xpath("//input[@id='password']")
		password_retype = driver.find_element_by_xpath("//input[@id='passwordRetype']")
		password.send_keys(unq_hostname + "$")
		password_retype.send_keys(unq_hostname + "$")
	
		username = wait.until(EC.element_to_be_clickable((By.XPATH,"//button[@id='usePersonalEmail']"))).click()
		email_box = driver.find_element_by_xpath("//*[@id='primaryEmail']")
		email_box.send_keys(self.email)
	
		drop_menu = wait.until(EC.element_to_be_clickable((By.XPATH,"/html/body/main/div/form/div[4]/fieldset/select/option[2]")))
		secret_answer = driver.find_element_by_xpath("//input[@id='secretAnswer']")	
		drop_menu.click()
		secret_answer.send_keys(unq_hostname)
	
		wait.until(EC.element_to_be_clickable((By.XPATH,"//*[@id='submitButton']"))).click()

	def third_page( self ):
		driver = self.driver
		wait = self.wait
		long_wait = self.long_wait
		
		time_message = long_wait.until(EC.presence_of_element_located((By.XPATH,"//span[@id='orderConfirmationSponsoredExpirationDate']"))).text
				
		driver.execute_script("window.stop();")
	
		time_m_list = time_message.strip().split(' ')	
		final_submit = long_wait.until(EC.element_to_be_clickable((By.XPATH,"//button[@id='_orderConfirmationActivatePass']")))

		military_time = time_m_list[6].split(':')

		#Check Time then Convert to Military Time 
		if (time_m_list[7] == 'PM' and str(military_time[0]) != '12'):
			hour_time = str((int(military_time[0]) + 12))
		elif (time_m_list[7] == 'AM' and str(military_time[0]) == '12'):
			hour_time = "0"
		else:
			hour_time = military_time[0]
			
		min_time = military_time[1].lstrip("0")
		
		try:
			with open ("global_vars.csv", mode='a') as global_vars:
				csv_writer = csv.writer(global_vars)
				csv_writer.writerow([hour_time, min_time])
		finally:
			global_vars.close()
		
		if final_submit.is_enabled():
			final_submit.click()
			
	def tear_down( self, f_profile, f_profile_dir ):
		# src_files = os.listdir(f_profile.path)
		# root_src_dir = f_profile.path
		# root_dst_dir = f_profile_dir

		# for src_dir, dirs, files in os.walk(root_src_dir):
			# dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
			# if not os.path.exists(dst_dir):
				# os.makedirs(dst_dir)
			# for file_ in files:
				# src_file = os.path.join(src_dir, file_)
				# dst_file = os.path.join(dst_dir, file_)
				# if os.path.exists(dst_file):
					# # in case of the src and dst are the same file
					# if os.path.samefile(src_file, dst_file):
						# continue
					# os.remove(dst_file)
				# shutil.move(src_file, dst_dir)
		driver.quit()
		
f_profile_dir, f_binary_dir = check_input( sys.argv )
f_profile = initialize_profile( f_profile_dir )
user_agent = generate_user_agent()

driver = initialize_driver( f_profile_dir, f_binary_dir, f_profile, user_agent )

xfinity = XfinityForms( driver )
portal_authenticate( xfinity )
xfinity.tear_down( f_profile, f_profile_dir )
